# Polaxis SDK

**Python SDK and MCP server for the [Polaxis](https://polaxis.io) AI Agent Governance Platform.**

Polaxis sits between your AI agent and its tools, evaluating every tool call against your policies in real time — blocking dangerous actions, enforcing spend limits, and routing ambiguous calls to a human approver — all in under 5ms.

[![PyPI version](https://img.shields.io/pypi/v/polaxis)](https://pypi.org/project/polaxis/)
[![Python](https://img.shields.io/pypi/pyversions/polaxis)](https://pypi.org/project/polaxis/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Tests](https://github.com/nishant6118/Polaxis-SDK-MCP/actions/workflows/tests.yml/badge.svg)](https://github.com/nishant6118/Polaxis-SDK-MCP/actions)

---

## What does Polaxis do?

```
Your AI agent
    │
    │  tool_call("delete_records", {"table": "users"})
    ▼
┌─────────────────────────────────────────┐
│          Polaxis Policy Engine          │
│  • Evaluate against your policy rules   │
│  • Check agent spend budget             │
│  • Scan for prompt injection / PII      │
│  • Route to human approver if needed    │
└─────────────────────────────────────────┘
    │
    │  decision: "allow" | "block" | "escalate"
    ▼
Your tools (database, email, API…)
```

**Three possible outcomes for every tool call:**

| Decision | Meaning | What to do |
|---|---|---|
| `allow` | Call is within policy. Proceed. | Execute the tool |
| `block` | Call violates a rule or budget. | Abort — log the reason |
| `escalate` | Human sign-off required. | Wait for approval via Slack or dashboard |

---

## Installation

```bash
pip install polaxis
```

With MCP server support:

```bash
pip install "polaxis[mcp]"
```

**Requirements:** Python 3.10+

---

## Quick start

**1. Get your API key** — create a free account at [polaxis.io](https://polaxis.io), add an agent, and copy its API key.

**2. Set the environment variable:**

```bash
export POLAXIS_API_KEY=ag_prod_...
```

**3. Evaluate every tool call before executing it:**

```python
import asyncio
from polaxis import Polaxis, PolicyBlockError

guard = Polaxis()  # reads POLAXIS_API_KEY from env

async def send_invoice(customer_id: str, amount: float):
    # ← Evaluate BEFORE touching any tool
    result = await guard.evaluate(
        tool_name="send_invoice",
        tool_input={"customer_id": customer_id, "amount_usd": amount},
        session_id="session-001",
    )

    # result.decision is "allow", "block", or "escalate"
    if result.allowed:
        your_invoice_api.send(customer_id, amount)

asyncio.run(send_invoice("cust_123", 499.00))
```

That's it. Every call is now governed, logged, and auditable from your Polaxis dashboard.

---

## API reference

### `Polaxis(api_key, *, base_url, timeout, raise_on_block, raise_on_budget)`

Main async client. Create one instance per agent and reuse it.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `api_key` | `str` | env `POLAXIS_API_KEY` | Your agent API key |
| `base_url` | `str` | `https://api.polaxis.io` | Override for self-hosted |
| `timeout` | `float` | `10.0` | HTTP request timeout (seconds) |
| `raise_on_block` | `bool` | `True` | Raise `PolicyBlockError` / `FirewallBlockError` instead of returning a blocked result |
| `raise_on_budget` | `bool` | `True` | Raise `BudgetExceededError` on budget violations |

---

### `await guard.evaluate(tool_name, tool_input, *, session_id, estimated_cost_usd)`

Evaluate a proposed tool call. **Call this before every tool execution.**

```python
result = await guard.evaluate(
    tool_name="send_email",
    tool_input={"to": "alice@example.com", "subject": "Hello"},
    session_id="sess_abc",         # optional — groups calls in audit logs
    estimated_cost_usd=0.002,      # optional — for budget tracking
)
```

Returns [`EvaluateResult`](#evaluateresult).

**Raises:**
- `PolicyBlockError` — blocked by a policy rule
- `FirewallBlockError` — blocked by the Agent Firewall (prompt injection, PII, secrets)
- `BudgetExceededError` — agent's budget is exhausted
- `AuthenticationError` — bad API key
- `APIError` — unexpected HTTP error

---

### `await guard.await_approval(approval_id, *, timeout_seconds, poll_interval)`

Poll until a human approver acts on an escalated request.

```python
result = await guard.evaluate("wire_transfer", {"amount": 50_000})

if result.pending_approval:
    status = await guard.await_approval(
        result.approval_id,
        timeout_seconds=result.timeout_seconds,
    )
    if status.approved:
        execute_transfer()
```

**Raises:**
- `ApprovalRejectedError` — approver clicked Reject
- `ApprovalTimeoutError` — no decision within `timeout_seconds`

---

### `EvaluateResult`

| Attribute | Type | Description |
|---|---|---|
| `decision` | `str` | `"allow"` \| `"block"` \| `"escalate"` |
| `allowed` | `bool` | Shorthand for `decision == "allow"` |
| `blocked` | `bool` | Shorthand for `decision == "block"` |
| `pending_approval` | `bool` | Shorthand for `decision == "escalate"` |
| `reason` | `str \| None` | Human-readable explanation |
| `policy_triggered` | `str \| None` | Policy name that matched |
| `rule_name` | `str \| None` | Specific rule that matched |
| `approval_id` | `str \| None` | For escalated calls — pass to `await_approval()` |
| `timeout_seconds` | `int` | How long to wait for approval |
| `budget_remaining_usd` | `float` | Remaining daily budget |
| `budget_warning` | `bool` | Budget is below 20% |
| `threats` | `list` | Detected firewall threats (non-blocking) |

---

### `PolaxisSync` — synchronous usage

For scripts and non-async frameworks:

```python
from polaxis import PolaxisSync

guard = PolaxisSync()
result = guard.evaluate("delete_records", {"table": "orders", "where": "status='test'"})

if result.blocked:
    raise RuntimeError(f"Blocked: {result.reason}")
```

---

## Error handling

All exceptions inherit from `PolaxisError`:

```python
from polaxis import (
    PolicyBlockError,      # policy rule matched → block
    FirewallBlockError,    # firewall detected threat
    BudgetExceededError,   # daily/monthly budget hit
    ApprovalRejectedError, # human said no
    ApprovalTimeoutError,  # no decision in time
    AuthenticationError,   # bad API key
    APIError,              # HTTP error
)
```

**Pattern — handle without raising:**

```python
guard = Polaxis(raise_on_block=False, raise_on_budget=False)
result = await guard.evaluate("tool", input)

match result.decision:
    case "allow":
        run_tool()
    case "block":
        log.warning("Blocked: %s", result.reason)
    case "escalate":
        status = await guard.await_approval(result.approval_id)
```

---

## Human-in-the-loop (HITL)

When a policy rule has action `require_approval`, Polaxis pauses the agent and sends an approval request to your configured Slack channel or dashboard.

```python
result = await guard.evaluate("deploy_to_production", {"service": "api", "version": "v2.1.0"})

if result.pending_approval:
    print(f"Waiting for approval (id: {result.approval_id})")
    # This blocks (async) until approved, rejected, or timed out
    status = await guard.await_approval(
        result.approval_id,
        timeout_seconds=600,   # 10 minute window
    )
    if status.approved:
        deploy()
    # ApprovalRejectedError or ApprovalTimeoutError raised otherwise
```

Your team sees this in Slack:

```
🔔 Polaxis — Approval Required
Agent: deploy-bot  |  Policy: prod-deploy-policy
Tool: deploy_to_production
Input: {"service": "api", "version": "v2.1.0"}

[✓ Approve]  [✗ Reject]
```

---

## Framework integrations

### OpenAI function calling

```python
# See examples/openai_tools_example.py for the full pattern
async def execute_tool(tool_name: str, tool_input: dict) -> str:
    result = await guard.evaluate(tool_name, tool_input)
    if result.allowed:
        return your_tool_implementations[tool_name](**tool_input)
    return f"Blocked: {result.reason}"
```

### LangChain

```python
# See examples/langchain_example.py for a GovernedTool base class
class MyTool(GovernedTool):
    name = "my_tool"

    async def _run_governed(self, **kwargs):
        # Only called when Polaxis says "allow"
        return do_the_work(**kwargs)
```

### MCP (Model Context Protocol)

Add the Polaxis governance proxy to your MCP client config:

```json
{
  "mcpServers": {
    "polaxis": {
      "command": "polaxis-mcp",
      "env": {
        "POLAXIS_API_KEY": "ag_prod_..."
      }
    }
  }
}
```

The server exposes a `polaxis_evaluate` tool your agent calls before any action. See [`examples/mcp_config.json`](examples/mcp_config.json) for a full config example.

### CrewAI / PydanticAI / AutoGen

The pattern is the same for any framework — evaluate before calling the tool, handle the three outcomes. See the [examples/](examples/) directory.

---

## Policy examples

Policies are configured in the Polaxis dashboard (JSON format). Here are common patterns:

**Block large financial transactions:**
```json
{
  "name": "finance-guard",
  "rules": [
    {
      "trigger": { "tool": "charge_card", "condition": "amount_usd > 500" },
      "action": "block",
      "message": "Charges over $500 require manual processing."
    }
  ]
}
```

**Require approval for production deployments:**
```json
{
  "name": "prod-deploy",
  "rules": [
    {
      "trigger": { "tool": "deploy", "condition": "environment == 'production'" },
      "action": "require_approval",
      "message": "Production deploys require engineering lead sign-off."
    }
  ]
}
```

**Rate-limit a noisy tool:**
```json
{
  "name": "api-rate-limit",
  "rules": [
    {
      "trigger": { "tool": "call_external_api", "condition": "rate_per_hour > 100" },
      "action": "block",
      "message": "External API rate limit exceeded."
    }
  ]
}
```

---

## Examples

| File | What it shows |
|---|---|
| [`examples/basic_usage.py`](examples/basic_usage.py) | Core evaluate + HITL pattern |
| [`examples/openai_tools_example.py`](examples/openai_tools_example.py) | OpenAI function-calling agent loop |
| [`examples/langchain_example.py`](examples/langchain_example.py) | LangChain `GovernedTool` base class |
| [`examples/mcp_config.json`](examples/mcp_config.json) | MCP client config for the proxy server |

---

## Self-hosted deployment

On Pro and Enterprise plans you can run the full Polaxis stack in your own infrastructure:

```bash
git clone https://github.com/nishant6118/Polaxis-SDK-MCP.git
```

Contact [sales@polaxis.io](mailto:sales@polaxis.io) for a Docker Compose deployment guide and VPC setup instructions.

Point the SDK at your instance:

```python
guard = Polaxis(
    api_key="ag_prod_...",
    base_url="https://polaxis.your-company.com",
)
```

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development setup
- How to add a new framework integration
- Running tests
- PR checklist and design principles

---

## Support

| Channel | Link |
|---|---|
| Documentation | [docs.polaxis.io](https://docs.polaxis.io) |
| Dashboard | [polaxis.io](https://polaxis.io) |
| GitHub Issues | [github.com/nishant6118/Polaxis-SDK-MCP/issues](https://github.com/nishant6118/Polaxis-SDK-MCP/issues) |
| Email | sdk@polaxis.io |

---

## License

MIT — see [LICENSE](LICENSE).
