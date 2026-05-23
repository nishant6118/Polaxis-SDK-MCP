"""Basic Polaxis usage — evaluate a tool call before executing it.

Set your API key:
    export POLAXIS_API_KEY=ag_prod_...

Then run:
    python examples/basic_usage.py
"""
import asyncio
import os
from polaxis import Polaxis, PolicyBlockError, ApprovalRejectedError

# ── Initialize once per agent ────────────────────────────────────────────────

guard = Polaxis(
    api_key=os.environ["POLAXIS_API_KEY"],
    # Optionally override the endpoint for self-hosted deployments:
    # base_url="https://your-polaxis-instance.com",
)


# ── Example 1: Simple allow/block ────────────────────────────────────────────

async def send_invoice(customer_id: str, amount_usd: float) -> dict:
    """Wrapper that governs the tool call before executing."""
    try:
        result = await guard.evaluate(
            tool_name="send_invoice",
            tool_input={"customer_id": customer_id, "amount_usd": amount_usd},
            session_id="demo-session-001",
            estimated_cost_usd=0.001,
        )
    except PolicyBlockError as e:
        print(f"[BLOCKED] {e.reason} (policy: {e.policy_triggered})")
        return {"ok": False, "blocked": True, "reason": e.reason}

    print(f"[ALLOWED] Proceeding — budget remaining: ${result.budget_remaining_usd:.2f}")
    # ... your actual tool logic here ...
    return {"ok": True, "invoice_id": "inv_demo_123"}


# ── Example 2: Human-in-the-loop ────────────────────────────────────────────

async def delete_records(table: str, where: str) -> dict:
    """Tool that requires human sign-off for destructive operations."""
    result = await guard.evaluate(
        tool_name="delete_records",
        tool_input={"table": table, "where": where},
    )

    if result.allowed:
        # No policy triggered — execute immediately
        print("[ALLOWED] Executing delete_records")
        return {"ok": True, "deleted": 0}

    if result.pending_approval:
        print(f"[ESCALATED] Waiting for approval (id: {result.approval_id})")
        print("  → Check your Slack or the Polaxis dashboard to approve/reject")
        try:
            status = await guard.await_approval(
                result.approval_id,
                timeout_seconds=result.timeout_seconds,
            )
            print(f"[RESOLVED] {status.status} by {status.resolved_by}")
            if status.approved:
                # ... execute the tool now ...
                return {"ok": True, "deleted": 0}
        except ApprovalRejectedError as e:
            print(f"[REJECTED] {e.rejection_reason}")
            return {"ok": False, "rejected": True}

    return {"ok": False, "blocked": True}


# ── Run demo ─────────────────────────────────────────────────────────────────

async def main():
    print("=== Example 1: Invoice (low amount — likely allowed) ===")
    await send_invoice("cust_001", 49.00)

    print("\n=== Example 2: Invoice (high amount — may be blocked) ===")
    await send_invoice("cust_002", 10_000.00)

    print("\n=== Example 3: Delete (likely requires approval) ===")
    await delete_records("customers", "status = 'inactive'")


if __name__ == "__main__":
    asyncio.run(main())
