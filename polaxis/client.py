"""Polaxis SDK — main client."""
from __future__ import annotations

import asyncio
import os
import time
from typing import Optional

import httpx

from .exceptions import (
    APIError,
    ApprovalRejectedError,
    ApprovalTimeoutError,
    AuthenticationError,
    BudgetExceededError,
    FirewallBlockError,
    PolicyBlockError,
)
from .models import ApprovalStatus, EvaluateResult, OutputScanResult

_DEFAULT_BASE_URL = "https://api.polaxis.io"
_DEFAULT_TIMEOUT = 10.0  # seconds
_POLL_INTERVAL = 1.5     # seconds between approval status polls


class Polaxis:
    """Governance client for AI agent tool calls.

    Instantiate once per agent, then call :meth:`evaluate` before every tool
    execution.  The client is fully async; use :class:`PolaxisSync` for
    synchronous / non-async contexts.

    Args:
        api_key: Your agent API key (found in the Polaxis dashboard under
            Agents → API Key).  Can also be set via the ``POLAXIS_API_KEY``
            environment variable.
        base_url: Override the Polaxis API endpoint.  Defaults to
            ``https://api.polaxis.io``.
        timeout: HTTP request timeout in seconds.  Defaults to ``10.0``.
        raise_on_block: When ``True`` (default), raise :exc:`PolicyBlockError`
            or :exc:`FirewallBlockError` instead of returning a result with
            ``decision="block"``.
        raise_on_budget: When ``True`` (default), raise
            :exc:`BudgetExceededError` on budget violations.

    Example::

        import asyncio
        from polaxis import Polaxis

        guard = Polaxis(api_key="ag_prod_...")

        async def main():
            result = await guard.evaluate(
                tool_name="send_invoice",
                tool_input={"amount": 500, "customer_id": "cust_123"},
            )
            if result.allowed:
                send_invoice(...)

        asyncio.run(main())
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        raise_on_block: bool = True,
        raise_on_budget: bool = True,
    ) -> None:
        self._api_key = api_key or os.environ.get("POLAXIS_API_KEY", "")
        if not self._api_key:
            raise AuthenticationError(
                "No API key provided. Pass api_key= or set the POLAXIS_API_KEY "
                "environment variable."
            )
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._raise_on_block = raise_on_block
        self._raise_on_budget = raise_on_budget
        self._headers = {
            "X-Agent-Key": self._api_key,
            "Content-Type": "application/json",
            "User-Agent": "polaxis-python-sdk/0.1.0",
        }

    # ── Core evaluate ──────────────────────────────────────────────────────────

    async def evaluate(
        self,
        tool_name: str,
        tool_input: dict,
        *,
        session_id: str = "",
        estimated_cost_usd: float = 0.0,
    ) -> EvaluateResult:
        """Evaluate a tool call against your configured policies.

        Must be called **before** executing the tool.  If the call is allowed,
        proceed as normal.  If it is escalated, call :meth:`await_approval`.

        Args:
            tool_name: Exact name of the tool being invoked (e.g.
                ``"send_email"``).
            tool_input: The arguments the agent is passing to the tool.
            session_id: Optional identifier grouping related calls in one
                agent session.  Useful for audit logs and per-session budgets.
            estimated_cost_usd: Your own cost estimate for this call (e.g.
                cloud API spend).  Polaxis may compute its own estimate; the
                higher of the two is used for budget tracking.

        Returns:
            :class:`EvaluateResult` describing the governance decision.

        Raises:
            PolicyBlockError: If the call is blocked by a policy rule and
                ``raise_on_block=True``.
            FirewallBlockError: If the Agent Firewall detected a threat and
                ``raise_on_block=True``.
            BudgetExceededError: If the agent has no remaining budget and
                ``raise_on_budget=True``.
            AuthenticationError: If the API key is rejected.
            APIError: On unexpected HTTP errors.
        """
        payload = {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "session_id": session_id,
            "estimated_cost_usd": estimated_cost_usd,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/api/evaluate",
                json=payload,
                headers=self._headers,
            )

        if resp.status_code == 401:
            raise AuthenticationError("Invalid or expired API key.")
        if resp.status_code == 429:
            raise APIError(429, resp.text)
        if not resp.is_success:
            raise APIError(resp.status_code, resp.text)

        data = resp.json()
        result = EvaluateResult._from_dict(data)

        # Optionally raise exceptions instead of returning blocked results
        if result.blocked:
            threats = result.threats
            if threats:
                if self._raise_on_block:
                    raise FirewallBlockError(
                        result.reason or "Firewall blocked this call",
                        threats=threats,
                    )
            else:
                if self._raise_on_block:
                    raise PolicyBlockError(
                        result.reason or "Blocked by policy",
                        policy_triggered=result.policy_triggered or "",
                        rule_name=result.rule_name or "",
                    )
                # Budget-specific block
                if (
                    self._raise_on_budget
                    and result.policy_triggered == "budget_envelope"
                ):
                    raise BudgetExceededError(
                        current_spend_usd=result.current_spend_usd,
                        limit_usd=result.budget_remaining_usd,
                    )

        return result

    # ── Output scanning ────────────────────────────────────────────────────────

    async def scan_output(
        self,
        tool_name: str,
        tool_output: object,
        *,
        session_id: str = "",
    ) -> "OutputScanResult":
        """Scan a tool's return value for threats before the agent ingests it.

        Call this after every tool execution and check the result before using
        the output in subsequent reasoning or tool calls.

        Args:
            tool_name:   Name of the tool that produced this output.
            tool_output: The raw value returned by the tool (dict, list, str…).
            session_id:  Session identifier — groups events in audit logs.

        Returns:
            :class:`OutputScanResult` describing whether the output is safe.

        Example::

            result = await guard.evaluate("web_search", {"query": q})
            if result.allowed:
                raw = await web_search(q)
                scan = await guard.scan_output("web_search", raw)
                if scan.safe:
                    content = raw
                elif scan.action == "redact":
                    content = scan.sanitized_output   # PII stripped
                else:
                    raise RuntimeError(f"Tool output quarantined: {scan.threats}")
        """
        payload = {
            "tool_name": tool_name,
            "tool_output": tool_output,
            "session_id": session_id,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/api/evaluate/output",
                json=payload,
                headers=self._headers,
            )
        if resp.status_code == 401:
            raise AuthenticationError("Invalid or expired API key.")
        if not resp.is_success:
            raise APIError(resp.status_code, resp.text)
        return OutputScanResult._from_dict(tool_output, resp.json())

    # ── Human-in-the-loop helpers ──────────────────────────────────────────────

    async def get_approval_status(self, approval_id: str) -> ApprovalStatus:
        """Fetch the current status of a pending approval.

        Args:
            approval_id: The ``approval_id`` from an escalated
                :class:`EvaluateResult`.

        Returns:
            :class:`ApprovalStatus` with the current state.
        """
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self._base_url}/api/approvals/{approval_id}",
                headers=self._headers,
            )
        if not resp.is_success:
            raise APIError(resp.status_code, resp.text)
        return ApprovalStatus._from_dict(approval_id, resp.json())

    async def await_approval(
        self,
        approval_id: str,
        *,
        timeout_seconds: int = 300,
        poll_interval: float = _POLL_INTERVAL,
        raise_on_rejected: bool = True,
        raise_on_timeout: bool = True,
    ) -> ApprovalStatus:
        """Poll until a human approver acts on the request.

        Call this after receiving ``decision="escalate"`` from
        :meth:`evaluate`.  Blocks (async) until the approval is resolved or the
        timeout is reached.

        Args:
            approval_id: The ``approval_id`` from the escalated result.
            timeout_seconds: Maximum wait time.  Defaults to 300 (5 minutes).
            poll_interval: Seconds between status checks.  Defaults to 1.5.
            raise_on_rejected: Raise :exc:`ApprovalRejectedError` on rejection.
            raise_on_timeout: Raise :exc:`ApprovalTimeoutError` on timeout.

        Returns:
            :class:`ApprovalStatus` with the final state.

        Raises:
            ApprovalRejectedError: If the approver rejected the call.
            ApprovalTimeoutError: If no decision was made within the timeout.
        """
        deadline = time.monotonic() + timeout_seconds

        while time.monotonic() < deadline:
            status = await self.get_approval_status(approval_id)

            if status.status in ("approved", "rejected", "timeout"):
                if status.rejected and raise_on_rejected:
                    raise ApprovalRejectedError(status.rejection_reason or "")
                if status.timed_out and raise_on_timeout:
                    raise ApprovalTimeoutError(
                        f"Approval {approval_id} timed out after {timeout_seconds}s"
                    )
                return status

            remaining = deadline - time.monotonic()
            await asyncio.sleep(min(poll_interval, remaining))

        if raise_on_timeout:
            raise ApprovalTimeoutError(
                f"Approval {approval_id} timed out after {timeout_seconds}s (client-side)"
            )
        return ApprovalStatus(approval_id=approval_id, status="timeout")

    # ── Context manager support ────────────────────────────────────────────────

    async def __aenter__(self) -> "Polaxis":
        return self

    async def __aexit__(self, *_) -> None:
        pass  # httpx clients are created per-request; nothing to close


# ── Synchronous wrapper ────────────────────────────────────────────────────────

class PolaxisSync:
    """Synchronous wrapper around :class:`Polaxis` for non-async code.

    Internally creates an event loop for each call.  For high-throughput agents
    use :class:`Polaxis` directly with ``asyncio.run()`` or inside an async
    framework.

    Example::

        from polaxis import PolaxisSync

        guard = PolaxisSync(api_key="ag_prod_...")
        result = guard.evaluate("delete_records", {"table": "users"})
        if result.blocked:
            raise RuntimeError(result.reason)
    """

    def __init__(self, *args, **kwargs) -> None:
        self._async = Polaxis(*args, **kwargs)

    def evaluate(self, tool_name: str, tool_input: dict, **kwargs) -> EvaluateResult:
        """Synchronous version of :meth:`Polaxis.evaluate`."""
        return asyncio.run(self._async.evaluate(tool_name, tool_input, **kwargs))

    def scan_output(self, tool_name: str, tool_output: object, **kwargs) -> "OutputScanResult":
        """Synchronous version of :meth:`Polaxis.scan_output`."""
        return asyncio.run(self._async.scan_output(tool_name, tool_output, **kwargs))

    def get_approval_status(self, approval_id: str) -> ApprovalStatus:
        """Synchronous version of :meth:`Polaxis.get_approval_status`."""
        return asyncio.run(self._async.get_approval_status(approval_id))

    def await_approval(self, approval_id: str, **kwargs) -> ApprovalStatus:
        """Synchronous version of :meth:`Polaxis.await_approval`."""
        return asyncio.run(self._async.await_approval(approval_id, **kwargs))
