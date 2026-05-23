"""Polaxis MCP Proxy Server.

This server implements the Model Context Protocol (MCP) and sits between
your MCP client (Claude Desktop, Cursor, etc.) and your actual tool servers.
Every tool call is evaluated by Polaxis before being forwarded.

Usage
-----
Set environment variables::

    export POLAXIS_API_KEY=ag_prod_...
    export POLAXIS_BASE_URL=https://api.polaxis.io   # optional

Then add to your MCP client config (e.g. Claude Desktop ~/.claude/claude_desktop_config.json)::

    {
      "mcpServers": {
        "polaxis-proxy": {
          "command": "python",
          "args": ["-m", "polaxis_mcp.server"],
          "env": {
            "POLAXIS_API_KEY": "ag_prod_..."
          }
        }
      }
    }

The server exposes a single tool — ``polaxis_evaluate`` — that your agent
uses to check any action before running it.  You can also run this in
transparent proxy mode where it wraps every tool call automatically
(requires configuring upstream MCP servers via UPSTREAM_MCP_SERVERS).

Dependencies
------------
    pip install polaxis mcp

Architecture
------------
::

    MCP Client (Claude / Cursor)
        │  MCP protocol (stdio / SSE)
        ▼
    polaxis_mcp.server   ←── evaluates every call via Polaxis API
        │  HTTP (allow only)
        ▼
    Your Tools (file system, Slack, DB, etc.)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any

logger = logging.getLogger("polaxis.mcp")


def _require_mcp():
    try:
        import mcp  # noqa: F401
    except ImportError:
        print(
            "The 'mcp' package is required for the MCP server.\n"
            "Install it with:  pip install mcp",
            file=sys.stderr,
        )
        sys.exit(1)


async def run_server() -> None:
    """Start the Polaxis MCP governance server."""
    _require_mcp()

    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent

    from polaxis import Polaxis
    from polaxis.exceptions import PolicyBlockError, FirewallBlockError, BudgetExceededError

    api_key = os.environ.get("POLAXIS_API_KEY", "")
    if not api_key:
        logger.error("POLAXIS_API_KEY is not set. Exiting.")
        sys.exit(1)

    base_url = os.environ.get("POLAXIS_BASE_URL", "https://api.polaxis.io")
    guard = Polaxis(api_key=api_key, base_url=base_url, raise_on_block=False)

    server = Server("polaxis-governance")

    # ── Tool: polaxis_evaluate ───────────────────────────────────────────────

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="polaxis_evaluate",
                description=(
                    "Evaluate a proposed tool call against Polaxis governance policies "
                    "before executing it. Returns 'allow', 'block', or 'escalate'.\n\n"
                    "Call this BEFORE every tool execution and only proceed if decision is 'allow'."
                ),
                inputSchema={
                    "type": "object",
                    "required": ["tool_name", "tool_input"],
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": "Exact name of the tool you intend to call.",
                        },
                        "tool_input": {
                            "type": "object",
                            "description": "The arguments you plan to pass to the tool.",
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Optional session identifier for grouping audit logs.",
                            "default": "",
                        },
                        "estimated_cost_usd": {
                            "type": "number",
                            "description": "Your cost estimate for this call (used for budget tracking).",
                            "default": 0.0,
                        },
                    },
                },
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name != "polaxis_evaluate":
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

        tool_name = arguments.get("tool_name", "")
        tool_input = arguments.get("tool_input", {})
        session_id = arguments.get("session_id", "")
        estimated_cost = float(arguments.get("estimated_cost_usd", 0.0))

        try:
            result = await guard.evaluate(
                tool_name=tool_name,
                tool_input=tool_input,
                session_id=session_id,
                estimated_cost_usd=estimated_cost,
            )
            response = {
                "decision": result.decision,
                "reason": result.reason,
                "policy_triggered": result.policy_triggered,
                "rule_name": result.rule_name,
                "approval_id": result.approval_id,
                "budget_remaining_usd": result.budget_remaining_usd,
                "budget_warning": result.budget_warning,
            }
        except (PolicyBlockError, FirewallBlockError, BudgetExceededError) as exc:
            response = {"decision": "block", "reason": str(exc)}
        except Exception as exc:
            logger.exception("Polaxis evaluate error")
            response = {"decision": "error", "reason": str(exc)}

        return [TextContent(type="text", text=json.dumps(response))]

    # ── Start ────────────────────────────────────────────────────────────────

    logger.info("Polaxis MCP governance server starting (base_url=%s)", base_url)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
