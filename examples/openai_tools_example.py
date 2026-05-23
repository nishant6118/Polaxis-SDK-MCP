"""Polaxis + OpenAI function-calling example.

Wraps every tool call the model makes through Polaxis governance.

Requirements:
    pip install polaxis openai

Set environment variables:
    export POLAXIS_API_KEY=ag_prod_...
    export OPENAI_API_KEY=sk-...
"""
import asyncio
import json
import os

import openai
from polaxis import Polaxis, PolicyBlockError, FirewallBlockError

guard = Polaxis(api_key=os.environ["POLAXIS_API_KEY"])
client = openai.AsyncOpenAI()

# ── Tool definitions (passed to OpenAI) ──────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email to a recipient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_record",
            "description": "Delete a record from the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {"type": "string"},
                    "record_id": {"type": "string"},
                },
                "required": ["table", "record_id"],
            },
        },
    },
]


# ── Governed tool executor ────────────────────────────────────────────────────

async def execute_tool(tool_name: str, tool_input: dict, session_id: str) -> str:
    """Evaluate via Polaxis then execute if allowed."""
    try:
        result = await guard.evaluate(
            tool_name=tool_name,
            tool_input=tool_input,
            session_id=session_id,
        )
    except PolicyBlockError as e:
        return json.dumps({"error": f"Blocked by policy '{e.policy_triggered}': {e.reason}"})
    except FirewallBlockError as e:
        return json.dumps({"error": f"Blocked by firewall: {e.reason}", "threats": e.threats})

    if result.pending_approval:
        # For this demo, we surface the escalation to the model
        return json.dumps({
            "status": "pending_approval",
            "approval_id": result.approval_id,
            "message": "This action requires human approval. Approval request sent to Slack.",
        })

    # Execute the actual tool
    if tool_name == "send_email":
        # Your real email logic here
        return json.dumps({"ok": True, "message_id": "msg_demo_001"})
    elif tool_name == "delete_record":
        # Your real DB logic here
        return json.dumps({"ok": True, "deleted": True})

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ── Agentic loop ──────────────────────────────────────────────────────────────

async def run_governed_agent(user_message: str, session_id: str = "session_001"):
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            # Model is done
            print(f"Agent: {msg.content}")
            break

        # Process each tool call through Polaxis governance
        messages.append(msg)
        tool_results = []
        for tc in msg.tool_calls:
            tool_input = json.loads(tc.function.arguments)
            print(f"  Tool call: {tc.function.name}({tool_input})")

            result_str = await execute_tool(tc.function.name, tool_input, session_id)
            print(f"  Result: {result_str}")

            tool_results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str,
            })

        messages.extend(tool_results)


if __name__ == "__main__":
    asyncio.run(
        run_governed_agent(
            "Send a welcome email to alice@example.com and delete test record #42 from the users table."
        )
    )
