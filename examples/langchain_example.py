"""Polaxis + LangChain tool governance example.

Wraps LangChain tools so every invocation is evaluated by Polaxis.

Requirements:
    pip install polaxis langchain langchain-openai

Set environment variables:
    export POLAXIS_API_KEY=ag_prod_...
    export OPENAI_API_KEY=sk-...
"""
import asyncio
import os
from typing import Any, Type

from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field

from polaxis import Polaxis, PolicyBlockError, FirewallBlockError

guard = Polaxis(api_key=os.environ["POLAXIS_API_KEY"])


# ── Governance mixin ──────────────────────────────────────────────────────────

class GovernedTool(BaseTool):
    """LangChain BaseTool subclass that auto-governs every invocation via Polaxis.

    Subclass this instead of BaseTool and implement _run_governed() instead of _run().
    """

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Use async _arun")

    async def _arun(self, *args: Any, **kwargs: Any) -> Any:
        tool_input = self._build_input(*args, **kwargs)
        try:
            result = await guard.evaluate(
                tool_name=self.name,
                tool_input=tool_input,
                session_id=kwargs.get("__session_id", "langchain"),
            )
        except (PolicyBlockError, FirewallBlockError) as exc:
            return f"[BLOCKED] {exc}"

        if result.pending_approval:
            return (
                f"[ESCALATED] Approval required (id: {result.approval_id}). "
                "Check Slack or the Polaxis dashboard to approve."
            )

        return await self._run_governed(*args, **kwargs)

    def _build_input(self, *args, **kwargs) -> dict:
        """Override to customize how args/kwargs become tool_input for Polaxis."""
        return {"args": args, **kwargs}

    async def _run_governed(self, *args: Any, **kwargs: Any) -> Any:
        """Implement your actual tool logic here."""
        raise NotImplementedError


# ── Example tools ─────────────────────────────────────────────────────────────

class SendEmailInput(BaseModel):
    to: str = Field(description="Recipient email address")
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Email body text")


class SendEmailTool(GovernedTool):
    name: str = "send_email"
    description: str = "Send an email to a recipient."
    args_schema: Type[BaseModel] = SendEmailInput

    def _build_input(self, to: str, subject: str, body: str, **_) -> dict:
        return {"to": to, "subject": subject, "body": body}

    async def _run_governed(self, to: str, subject: str, body: str, **_) -> str:
        # Your real email sending logic here
        print(f"  → Sending email to {to}: {subject}")
        return f"Email sent to {to} successfully."


class DeleteRecordInput(BaseModel):
    table: str = Field(description="Database table name")
    record_id: str = Field(description="ID of the record to delete")


class DeleteRecordTool(GovernedTool):
    name: str = "delete_record"
    description: str = "Delete a record from the database. Requires approval for production tables."
    args_schema: Type[BaseModel] = DeleteRecordInput

    def _build_input(self, table: str, record_id: str, **_) -> dict:
        return {"table": table, "record_id": record_id}

    async def _run_governed(self, table: str, record_id: str, **_) -> str:
        # Your real deletion logic here
        print(f"  → Deleting record {record_id} from {table}")
        return f"Record {record_id} deleted from {table}."


# ── Build governed agent ──────────────────────────────────────────────────────

def build_agent() -> AgentExecutor:
    tools = [SendEmailTool(), DeleteRecordTool()]
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant with access to email and database tools."),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


async def main():
    executor = build_agent()
    result = await executor.ainvoke({
        "input": "Send a summary email to team@example.com and delete test record #99 from the temp_data table."
    })
    print(f"\nFinal answer: {result['output']}")


if __name__ == "__main__":
    asyncio.run(main())
