"""Polaxis SDK — request and response models."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EvaluateResult:
    """Response from a successful (non-blocked) ``evaluate()`` call.

    Attributes:
        decision: One of ``"allow"``, ``"block"``, or ``"escalate"``.
        reason: Human-readable reason (set on block/escalate).
        policy_triggered: Name of the policy that fired (block/escalate only).
        policy_version: Version number of the matched policy.
        rule_name: The specific rule that matched.
        approval_id: ID of the created approval request (escalate only).
        timeout_seconds: How long the agent should wait for approval.
        budget_remaining_usd: Remaining budget after this call (allow only).
        current_spend_usd: Total spend so far today (allow only).
        external_api_cost_usd: Estimated cost Polaxis computed for this call.
        budget_warning: True if spend is approaching the daily limit.
        threats: Detected but non-blocking threats from the firewall.
    """

    decision: str  # "allow" | "block" | "escalate"
    reason: Optional[str] = None
    policy_triggered: Optional[str] = None
    policy_version: Optional[int] = None
    rule_name: Optional[str] = None

    # Human-in-the-loop fields
    approval_id: Optional[str] = None
    timeout_seconds: int = 300

    # Budget fields
    budget_remaining_usd: float = 0.0
    current_spend_usd: float = 0.0
    external_api_cost_usd: float = 0.0
    budget_warning: bool = False

    # Firewall
    threats: list = field(default_factory=list)

    @property
    def allowed(self) -> bool:
        """True when the call is permitted to proceed."""
        return self.decision == "allow"

    @property
    def blocked(self) -> bool:
        """True when the call was blocked by a policy or the firewall."""
        return self.decision == "block"

    @property
    def pending_approval(self) -> bool:
        """True when a human approver must act before the call can proceed."""
        return self.decision == "escalate"

    @classmethod
    def _from_dict(cls, data: dict) -> "EvaluateResult":
        return cls(
            decision=data.get("decision", "allow"),
            reason=data.get("reason"),
            policy_triggered=data.get("policy_triggered"),
            policy_version=data.get("policy_version"),
            rule_name=data.get("rule_name"),
            approval_id=data.get("approval_id"),
            timeout_seconds=int(data.get("timeout_seconds", 300)),
            budget_remaining_usd=float(data.get("budget_remaining_usd", 0)),
            current_spend_usd=float(data.get("current_spend_usd", 0)),
            external_api_cost_usd=float(data.get("external_api_cost_usd", 0)),
            budget_warning=bool(data.get("budget_warning", False)),
            threats=data.get("threats", []),
        )


@dataclass
class OutputScanResult:
    """Result of scanning a tool's output for threats.

    Attributes:
        safe:             True when output is clean and safe to use.
        action:           ``"allow"`` | ``"quarantine"`` | ``"redact"`` | ``"flag"``
        threats:          List of detected threats (dicts with type/subtype/severity).
        sanitized_output: Cleaned output with PII/secrets replaced (redact only).
        original_output:  The original unmodified output for reference.
    """

    safe: bool
    action: str             # allow | quarantine | redact | flag
    threats: list = field(default_factory=list)
    sanitized_output: object = None
    original_output: object = None

    @property
    def quarantined(self) -> bool:
        """True when the output must not be used."""
        return self.action == "quarantine"

    @property
    def redacted(self) -> bool:
        """True when the output was cleaned — use sanitized_output instead."""
        return self.action == "redact"

    @classmethod
    def _from_dict(cls, original: object, data: dict) -> "OutputScanResult":
        return cls(
            safe=bool(data.get("safe", True)),
            action=data.get("action", "allow"),
            threats=data.get("threats", []),
            sanitized_output=data.get("sanitized_output"),
            original_output=original,
        )


@dataclass
class ApprovalStatus:
    """Current state of a human-in-the-loop approval request.

    Attributes:
        approval_id: The approval request identifier.
        status: One of ``"pending"``, ``"approved"``, ``"rejected"``, ``"timeout"``.
        resolved_by: Email or identifier of whoever resolved it.
        rejection_reason: Provided reason when status is ``"rejected"``.
    """

    approval_id: str
    status: str  # "pending" | "approved" | "rejected" | "timeout"
    resolved_by: Optional[str] = None
    rejection_reason: Optional[str] = None

    @property
    def approved(self) -> bool:
        return self.status == "approved"

    @property
    def rejected(self) -> bool:
        return self.status == "rejected"

    @property
    def timed_out(self) -> bool:
        return self.status == "timeout"

    @classmethod
    def _from_dict(cls, approval_id: str, data: dict) -> "ApprovalStatus":
        return cls(
            approval_id=approval_id,
            status=data.get("status", "pending"),
            resolved_by=data.get("resolved_by"),
            rejection_reason=data.get("rejection_reason"),
        )
