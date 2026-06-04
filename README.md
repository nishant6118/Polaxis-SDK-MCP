<div align="center">

<img src="https://raw.githubusercontent.com/nishant6118/Polaxis/main/docs/logo/dark.svg" alt="Polaxis" width="180"/>

<br/><br/>

<h2>Polaxis Python SDK & MCP Server</h2>

<p><i>The runtime control layer between your AI agents and the real world — intercept every tool call, enforce policies, require human approval, audit everything. Before anything executes.</i></p>

<br/>

[![PyPI](https://img.shields.io/pypi/v/polaxis?style=for-the-badge&color=6366f1&label=pip+install+polaxis)](https://pypi.org/project/polaxis)
[![Python](https://img.shields.io/badge/python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://pypi.org/project/polaxis)
[![License](https://img.shields.io/badge/License-MIT-gray?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-22c55e?style=for-the-badge&logo=pytest&logoColor=white)](#)

<br/>

[![Docs](https://img.shields.io/badge/docs.polaxis.io-blue?style=flat-square)](https://docs.polaxis.io)
[![Dashboard](https://img.shields.io/badge/polaxis.io-live-6366f1?style=flat-square)](https://polaxis.io)
[![Free Tier](https://img.shields.io/badge/free_tier-1_agent_·_10k_calls%2Fmo-22c55e?style=flat-square)](https://polaxis.io/register)
[![Benchmark](https://img.shields.io/badge/benchmark-99.4%25_detection-22c55e?style=flat-square)](https://polaxis.io/benchmark)

</div>

---

## What is Polaxis?

Polaxis is the **runtime control layer** between your AI agents and the tools they call.

You put an API gateway in front of your backend. Polaxis is that gateway for your agents — every tool call intercepted before it executes, evaluated against your policies, and either allowed, blocked, or routed for human approval.

```
  Your AI agent
        │
        │  tool_call("delete_records", {"table": "users_prod"})
        ▼
┌──────────────────────────────────────────────────────────────┐
│                   Polaxis Control Layer                       │
│                                                              │
│  L1  Regex scan            — 80+ patterns: injection, PII   │
│  L2  Risk scorer           — 15 signals, sub-millisecond    │
│  L3  LLM semantic gate     — fires on ~11% of calls only    │
│  L4  Behavioral baseline   — detects slow drift attacks     │
│  L5  Session graph         — recon → exfil kill-chain       │
│  L6  Threat intel          — per-agent threat level 0–4     │
│  L7  Policy engine         — your rules, budgets, logic     │
│                                                              │
│  0.15ms p50 (regex layers) · $0.00026 per call              │
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
| `approved` | Within policy. Proceed. | Execute the tool |
| `blocked` | Violates a rule or budget cap. | Abort — reason logged |
| `escalated` | Human sign-off required. | Wait for approval via Slack or dashboard |

---

## Quickstart — 3 lines

```bash
pip install polaxis
```

```python
from polaxis import Polaxis

guard = Polaxis(api_key="ag_prod_...", agent_id="my-agent")

# Wrap any tool call — works with any framework
result = await guard.evaluate(
    tool_name="delete_records",
    tool_input={"table": "users_prod"}
)
# result.decision → "approved" | "blocked" | "escalated"
# result.reason   → "rule: no-prod-delete · 0.15ms"
```

That's it. Works with LangChain, LangGraph, CrewAI, OpenAI Agents SDK, PydanticAI, AutoGen, or any custom agent — anything that calls a tool.

---

## MCP Proxy — zero code

For Claude Desktop, Cursor, or any MCP client: set three env vars and point your client at the proxy. No code changes.

```bash
export POLAXIS_API_KEY=ag_prod_...
export POLAXIS_AGENT_ID=claude-desktop
export TARGET_MCP_SERVER_URL=http://localhost:8080

# Start the proxy
python -m polaxis.mcp_proxy
```

Every MCP tool call now goes through Polaxis before it reaches your server.

---

## What it protects against

| Threat | What it catches |
|--------|-----------------|
| **Prompt injection** | Direct, indirect (RAG/email), encoded (Base64, Unicode, NATO phonetic), multilingual |
| **Credential leakage** | 25+ vendor key formats + high-entropy detection |
| **PII exfiltration** | SSN, passport, credit card, phone, email — 10+ languages |
| **Memory poisoning** | MINJA-style latent trigger attacks on vector stores |
| **Authority claims** | Admin impersonation, sudo escalation, fake system overrides |
| **Policy Puppetry** | XML/INI/JSON structured prompts claiming to disable security |
| **Economic DoS** | Token amplification attacks — hard session cap enforced |

---

## Detection accuracy

> Measured on **459 real-world adversarial payloads** — hard tier includes Base64, ROT13, Unicode homoglyphs, zero-width chars, 10+ languages, MINJA memory poisoning, EchoLeak indirect injection.

| Threat Category | Detection Rate |
|---|:---:|
| Prompt Injection | **99.0%** |
| Credential / Secret | **100.0%** |
| PII Detection | **97.8%** |
| Memory Poisoning | **96.7%** |
| Authority Claims | **100.0%** |
| LLM false positive rate | **4.0%** |
| Regex false positive rate | **0.0%** |

**99.4% average detection across all threat categories.**

→ [Full benchmark methodology](https://polaxis.io/benchmark)

---

## Performance

| Layer | p50 latency | Notes |
|-------|-------------|-------|
| Regex + risk scorer | **0.15ms** | Pure Python, no I/O |
| Full 7-layer (no LLM) | **~0.5ms** | 89% of calls |
| With LLM semantic gate | **80–200ms** | ~11% of calls |
| Cost per call | **$0.00026** | LLM layer only when needed |

---

## Framework examples

<details>
<summary><b>LangChain</b></summary>

```python
from langchain.tools import tool
from polaxis import Polaxis

guard = Polaxis(api_key="ag_prod_...", agent_id="langchain-agent")

@tool
async def delete_records(table: str) -> str:
    """Delete records from a table."""
    result = await guard.evaluate(
        tool_name="delete_records",
        tool_input={"table": table}
    )
    if result.decision == "blocked":
        return f"Blocked: {result.reason}"
    # proceed with deletion
    return f"Deleted records from {table}"
```
</details>

<details>
<summary><b>OpenAI Agents SDK</b></summary>

```python
from agents import Agent, function_tool
from polaxis import Polaxis

guard = Polaxis(api_key="ag_prod_...", agent_id="openai-agent")

@function_tool
async def send_email(to: str, body: str) -> str:
    result = await guard.evaluate(
        tool_name="send_email",
        tool_input={"to": to, "body": body}
    )
    if result.decision != "approved":
        return f"Action {result.decision}: {result.reason}"
    # send email
```
</details>

<details>
<summary><b>CrewAI</b></summary>

```python
from crewai_tools import BaseTool
from polaxis import Polaxis

guard = Polaxis(api_key="ag_prod_...", agent_id="crewai-agent")

class SafeDatabaseTool(BaseTool):
    async def _run(self, query: str) -> str:
        result = await guard.evaluate(
            tool_name="run_query",
            tool_input={"query": query}
        )
        if result.decision == "blocked":
            return f"Blocked by Polaxis: {result.reason}"
        # execute query
```
</details>

---

## Policy rules

Define policies in the dashboard or via JSON:

```json
[
  {
    "rule": "no-prod-delete",
    "tool": "delete_records",
    "condition": "table LIKE '%prod%'",
    "action": "block"
  },
  {
    "rule": "large-charge-approval",
    "tool": "charge_card",
    "condition": "amount > 500",
    "action": "escalate",
    "notify": "#finance-alerts"
  },
  {
    "rule": "daily-budget",
    "agent": "*",
    "budget_usd": 50,
    "period": "day",
    "action": "block"
  }
]
```

---

## Links

| | |
|---|---|
| **Dashboard** | [polaxis.io](https://polaxis.io) |
| **Docs** | [docs.polaxis.io](https://docs.polaxis.io) |
| **Interactive demo** | [polaxis.io/demo](https://polaxis.io/demo) |
| **Benchmark** | [polaxis.io/benchmark](https://polaxis.io/benchmark) |
| **Free tier** | 1 agent · 10,000 calls/month · no card required |
| **PyPI** | `pip install polaxis` |

---

## License

MIT — free to use, modify, and distribute.
