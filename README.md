<div align="center">

<img src="https://raw.githubusercontent.com/nishant6118/Polaxis/main/docs/logo/dark.svg" alt="Polaxis" width="180"/>

<br/><br/>

<h2>Polaxis Python SDK & MCP Server</h2>

<p><i>AI agent security at the execution layer — evaluate every tool call, enforce policy, block threats. Sub-millisecond regex + LLM semantic eval. All before the tool runs.</i></p>

<br/>

[![PyPI](https://img.shields.io/pypi/v/polaxis?style=for-the-badge&color=6366f1&label=pip+install+polaxis)](https://pypi.org/project/polaxis)
[![Python](https://img.shields.io/badge/python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://pypi.org/project/polaxis)
[![License](https://img.shields.io/badge/License-MIT-gray?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-22c55e?style=for-the-badge&logo=pytest&logoColor=white)](#)

<br/>

[![Docs](https://img.shields.io/badge/📚_docs.polaxis.io-blue?style=flat-square)](https://docs.polaxis.io)
[![Dashboard](https://img.shields.io/badge/🌐_polaxis.io-live-6366f1?style=flat-square)](https://polaxis.io)
[![Free Tier](https://img.shields.io/badge/✅_free_tier-1_agent_·_10k_calls%2Fmo-22c55e?style=flat-square)](https://polaxis.io/register)
[![Benchmark](https://img.shields.io/badge/📊_benchmark-99%25_injection_·_100%25_secrets-22c55e?style=flat-square)](https://polaxis.io/benchmark)

</div>

---

## What does Polaxis do?

Polaxis is the **AI agent security** and **LLM security** SDK for Python — it sits between your AI agent and its tools, evaluating every tool call against your policies in real time before it executes.

```
  Your AI agent
        │
        │  tool_call("delete_records", {"table": "users"})
        ▼
┌──────────────────────────────────────────────────────────────┐
│                   Polaxis Runtime Firewall                    │
│                                                              │
│  L1  Prompt injection scan     — 35+ regex patterns         │
│  L2  PII detection             — SSN, CC, phone, email…     │
│  L3  Secret / credential scan  — 25+ vendor key formats     │
│  L4  Memory poisoning defense  — RAG / vector store attacks │
│  L5  Authority claim blocking  — admin impersonation, sudo  │
│  L6  Semantic LLM eval         — catches encoding & evasion │
│  L7  Policy engine             — your rules + budget caps   │
│                                                              │
│  Decision returned in < 5ms (regex) or ~400ms (+ LLM)       │
└──────────────────┬─────────────────────┬────────────────────┘
                   │                     │
                ALLOW              BLOCK / ESCALATE
                   │                     │
           Your tools run         Human approves via
         (database, API…)         Slack or dashboard
```

### Three outcomes for every call

| Decision | Meaning | What to do |
|----------|---------|------------|
| `allow` | Within policy. Proceed. | Execute the tool |
| `block` | Violates a rule or budget cap. | Abort — log the reason |
| `escalate` | Human sign-off required. | Wait for approval via Slack or dashboard |

---

## Detection Accuracy

> Measured on **459 real-world adversarial payloads** across 3 difficulty tiers:
> **Easy** (direct English) · **Medium** (multi-language, obfuscated) · **Hard** (Base64, ROT13, Unicode homoglyphs, zero-width chars, social engineering)

| Threat Category | Regex only (L1–L5) | + LLM eval (L6) | Combined |
|---|:---:|:---:|:---:|
| Prompt Injection | 28.3% | 99.0% | **99.0%** |
| Credential / Secret | 56.7% | 100.0% | **100.0%** 🎯 |
| PII Detection | 61.1% | 78.9% | **93.3%** |
| Memory Poisoning | 50.0% | 93.3% | **97.8%** |
| Authority Claims | 40.0% | 84.4% | **87.8%** |
| **False positive rate** | **0.0%** | 8.0% | — |

**Why regex alone isn't enough:** Hard-tier attacks — Base64-encoded injections, ROT13, zero-width characters, Unicode lookalikes, and multilingual injections — reduce regex detection to 10–26%. The LLM semantic eval layer (L6) catches these, pushing combined detection to **87–100%** across all categories.

### Latency breakdown

| Layer | p50 | p99 | Cost |
|-------|-----|-----|------|
| Regex (L1–L5) | **0.065 ms** | 0.177 ms | Free |
| + LLM eval (L6, `gpt-4o-mini`) | ~400 ms | ~900 ms | ~$0.0001/call |

Regex runs on every call. LLM is triggered only for configured high-risk tools or regex-flagged calls — keeping your average cost near zero.

> [View full benchmark methodology →](https://polaxis.io/benchmark)

---

## OWASP Agentic AI Coverage

Polaxis addresses the [OWASP Agentic AI Top Threats (ASI 2026)](https://owasp.org/www-project-top-10-for-large-language-model-applications/):

| Threat | Polaxis Layer | Coverage |
|--------|--------------|----------|
| T1 — Memory Poisoning | L4 + L6 | ✅ RAG/vector injection, latent triggers |
| T2 — Tool / Resource Abuse | L7 Policy Engine | ✅ Per-tool rules, rate limits |
| T3 — Privilege Escalation | L5 + L7 | ✅ Authority claims, sudo detection |
| T4 — Data Exfiltration | L2 (PII) + L3 (secrets) | ✅ Credential & PII blocking |
| T5 — Prompt Injection | L1 + L6 | ✅ 35+ patterns + semantic eval |
| T6 — Cascading Failures | L7 Budget + HITL | ✅ Spend caps, approval gates |
| T7 — Deceptive Alignment | L6 Semantic | ✅ LLM-based intent analysis |
| T15 — Human Manipulation | L5 + L6 | ✅ Authority impersonation, urgency attacks |

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

**1.** Create a free account at [polaxis.io/register →](https://polaxis.io/register), add an agent, and copy its API key.

**2.** Set your key:

```bash
export POLAXIS_API_KEY=ag_prod_...
```

**3.** Evaluate every tool call before executing it:

```python
import asyncio
from polaxis import Polaxis, PolicyBlockError

guard = Polaxis()   # reads POLAXIS_API_KEY from env

async def send_invoice(customer_id: str, amount: float):

    # ← Evaluate BEFORE touching any tool
    result = await guard.evaluate(
        tool_name  = "send_invoice",
        tool_input = {"customer_id": customer_id, "amount_usd": amount},
        session_id = "session-001",
    )

    if result.allowed:
        your_invoice_api.send(customer_id, amount)

asyncio.run(send_invoice("cust_123", 499.00))
```

Every call is now governed, logged, and auditable from your Polaxis dashboard.

> **Why this matters for LLM security:** prompts are only half the problem. The real risk is what your agent *does* — the tools it calls, the data it touches, the money it moves. **Agent runtime security** lives at execution time, not the prompt layer. Regex catches obvious attacks in microseconds. The LLM layer catches the sophisticated ones — multi-language injections, encoded payloads, social engineering — that no regex can see.

---

## API Reference

### `Polaxis(api_key, *, base_url, timeout, raise_on_block, raise_on_budget)`

Main async client. Create **one instance per agent** and reuse it.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `env POLAXIS_API_KEY` | Your agent API key (`ag_...`) |
| `base_url` | `str` | `https://api.polaxis.io` | Override for self-hosted deployments |
| `timeout` | `float` | `10.0` | HTTP request timeout in seconds |
| `raise_on_block` | `bool` | `True` | Raise `PolicyBlockError` / `FirewallBlockError` instead of returning a blocked result |
| `raise_on_budget` | `bool` | `True` | Raise `BudgetExceededError` on budget violations |

---

### `await guard.evaluate(tool_name, tool_input, *, session_id, estimated_cost_usd)`

Evaluate a proposed tool call. **Call this before every tool execution.**

```python
result = await guard.evaluate(
    tool_name          = "send_email",
    tool_input         = {"to_user_id": "usr_alice", "subject": "Hello"},
    session_id         = "sess_abc",       # optional — groups calls in audit logs
    estimated_cost_usd = 0.002,            # optional — for budget tracking
)
```

Returns [`EvaluateResult`](#evaluateresult).

**Raises:**
- `PolicyBlockError` — blocked by a policy rule
- `FirewallBlockError` — blocked by the Agent Firewall (prompt injection, PII, secrets, memory poisoning, authority claim)
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
        timeout_seconds = result.timeout_seconds,
    )
    if status.approved:
        execute_transfer()
    # raises ApprovalRejectedError or ApprovalTimeoutError otherwise
```

---

### `EvaluateResult`

| Attribute | Type | Description |
|-----------|------|-------------|
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
| `threats` | `list` | Detected firewall threats (non-blocking when action is `flag`) |

---

### `PolaxisSync` — synchronous usage

For scripts and non-async frameworks:

```python
from polaxis import PolaxisSync

guard  = PolaxisSync()
result = guard.evaluate("delete_records", {"table": "orders", "where": "status='test'"})

if result.blocked:
    raise RuntimeError(f"Blocked: {result.reason}")
```

---

## Error Handling

All exceptions inherit from `PolaxisError`:

```python
from polaxis import (
    PolicyBlockError,       # policy rule matched → block
    FirewallBlockError,     # firewall detected threat (injection / PII / secret)
    BudgetExceededError,    # daily or monthly budget hit
    ApprovalRejectedError,  # human clicked Reject
    ApprovalTimeoutError,   # no decision within timeout window
    AuthenticationError,    # bad API key
    APIError,               # unexpected HTTP error
)
```

**Pattern — handle without raising:**

```python
guard  = Polaxis(raise_on_block=False, raise_on_budget=False)
result = await guard.evaluate("tool", input_dict)

match result.decision:
    case "allow":
        run_tool()
    case "block":
        log.warning("Blocked: %s", result.reason)
    case "escalate":
        status = await guard.await_approval(result.approval_id)
```

---

## Human-in-the-Loop (HITL)

When a policy rule has `action: require_approval`, Polaxis pauses the agent and sends a request to your configured Slack channel or dashboard.

```python
result = await guard.evaluate(
    "deploy_to_production",
    {"service": "api", "version": "v2.1.0"},
)

if result.pending_approval:
    print(f"⏳ Waiting for approval (id: {result.approval_id})")
    # Blocks (async) until approved, rejected, or timed out
    status = await guard.await_approval(
        result.approval_id,
        timeout_seconds = 600,   # 10-minute window
    )
    if status.approved:
        deploy()
    # ApprovalRejectedError or ApprovalTimeoutError raised otherwise
```

Your team sees this in Slack:

```
🔔  Polaxis — Approval Required
─────────────────────────────────────
Agent:   deploy-bot
Policy:  prod-deploy-policy
Tool:    deploy_to_production
Input:   {"service": "api", "version": "v2.1.0"}
─────────────────────────────────────
[  ✓ Approve  ]   [  ✗ Reject  ]
```

---

## Framework Integrations

### OpenAI function calling

```python
# See examples/openai_tools_example.py for the full pattern
async def execute_tool(tool_name: str, tool_input: dict) -> str:
    result = await guard.evaluate(tool_name, tool_input)
    if result.allowed:
        return your_tool_implementations[tool_name](**tool_input)
    return f"Blocked: {result.reason}"
```

### LangGraph

```python
from polaxis.adapters.langgraph import PolaxisCallback

guard = Polaxis()
graph = builder.compile(callbacks=[PolaxisCallback(guard)])
result = await graph.ainvoke({"messages": [HumanMessage(content="Process refunds")]})
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

The server exposes a `polaxis_evaluate` tool your agent calls before any action. See `examples/mcp_config.json` for a full config example.

### CrewAI / PydanticAI / AutoGen

The pattern is the same for any framework — evaluate before calling the tool, handle the three outcomes. See the `examples/` directory.

---

## Policy Examples

Policies are configured in the [Polaxis dashboard](https://polaxis.io/dashboard). Common patterns:

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

**Rate-limit an external API tool:**

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
|------|---------------|
| `examples/basic_usage.py` | Core `evaluate` + HITL pattern |
| `examples/openai_tools_example.py` | OpenAI function-calling agent loop |
| `examples/langchain_example.py` | LangChain `GovernedTool` base class |
| `examples/mcp_config.json` | MCP client config for the proxy server |

---

## Self-Hosted Deployment

On Pro and Enterprise plans you can run the full Polaxis stack in your own infrastructure:

```bash
git clone https://github.com/nishant6118/comply.git
```

Point the SDK at your instance:

```python
guard = Polaxis(
    api_key  = "ag_prod_...",
    base_url = "https://polaxis.your-company.com",
)
```

Contact [sales@polaxis.io](mailto:sales@polaxis.io) for a Docker Compose deployment guide and VPC setup instructions.

---

## Contributing

Contributions are welcome! See `CONTRIBUTING.md` for:
- Development setup
- How to add a new framework integration
- Running tests
- PR checklist and design principles

---

## Support

| Channel | Link |
|---------|------|
| Documentation | [docs.polaxis.io](https://docs.polaxis.io) |
| Dashboard | [polaxis.io](https://polaxis.io) |
| Benchmark | [polaxis.io/benchmark](https://polaxis.io/benchmark) |
| GitHub Issues | [github.com/nishant6118/Polaxis-SDK-MCP/issues](https://github.com/nishant6118/Polaxis-SDK-MCP/issues) |
| Email | [sdk@polaxis.io](mailto:sdk@polaxis.io) |

---

## License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

**[🚀 Get started free](https://polaxis.io/register)** · **[📊 Benchmark](https://polaxis.io/benchmark)** · **[📚 Full docs](https://docs.polaxis.io)** · **[💬 sales@polaxis.io](mailto:sales@polaxis.io)**

<br/>

[![ai-agent-security](https://img.shields.io/badge/-ai--agent--security-dc2626?style=flat-square)](https://github.com/topics/ai-agent-security)
[![llm-security](https://img.shields.io/badge/-llm--security-dc2626?style=flat-square)](https://github.com/topics/llm-security)
[![prompt-injection](https://img.shields.io/badge/-prompt--injection-b45309?style=flat-square)](https://github.com/topics/prompt-injection)
[![agent-firewall](https://img.shields.io/badge/-agent--firewall-7c3aed?style=flat-square)](https://github.com/topics/agent-firewall)
[![mcp](https://img.shields.io/badge/-mcp-7c3aed?style=flat-square)](https://github.com/topics/mcp)
[![owasp](https://img.shields.io/badge/-owasp--agentic--ai-dc2626?style=flat-square)](https://github.com/topics/owasp)
[![python](https://img.shields.io/badge/-python-3776ab?style=flat-square&logo=python&logoColor=white)](https://github.com/topics/python)

</div>
