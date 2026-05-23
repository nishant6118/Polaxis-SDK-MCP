"""Polaxis SDK — custom exceptions."""
from __future__ import annotations


class PolaxisError(Exception):
    """Base exception for all Polaxis SDK errors."""


class AuthenticationError(PolaxisError):
    """Raised when the API key is invalid or missing."""


class PolicyBlockError(PolaxisError):
    """Raised when a tool call is blocked by a policy.

    Attributes:
        reason: Human-readable explanation from the policy rule.
        policy_triggered: Name of the policy that fired.
        rule_name: Name of the specific rule within the policy.
    """

    def __init__(self, reason: str, policy_triggered: str = "", rule_name: str = ""):
        super().__init__(reason)
        self.reason = reason
        self.policy_triggered = policy_triggered
        self.rule_name = rule_name


class BudgetExceededError(PolaxisError):
    """Raised when the agent's budget limit has been reached.

    Attributes:
        current_spend_usd: How much has been spent today.
        limit_usd: The configured daily limit.
    """

    def __init__(self, current_spend_usd: float = 0.0, limit_usd: float = 0.0):
        super().__init__(
            f"Budget limit exceeded — spent ${current_spend_usd:.4f} of ${limit_usd:.4f} daily limit"
        )
        self.current_spend_usd = current_spend_usd
        self.limit_usd = limit_usd


class ApprovalRejectedError(PolaxisError):
    """Raised when a human reviewer rejects the tool call."""

    def __init__(self, rejection_reason: str = ""):
        super().__init__(rejection_reason or "Tool call rejected by approver")
        self.rejection_reason = rejection_reason


class ApprovalTimeoutError(PolaxisError):
    """Raised when a human-in-the-loop approval times out."""


class FirewallBlockError(PolaxisError):
    """Raised when the Agent Firewall blocks a call (prompt injection, PII, secrets).

    Attributes:
        threats: List of detected threat dicts with keys: type, subtype, severity.
    """

    def __init__(self, reason: str, threats: list | None = None):
        super().__init__(reason)
        self.reason = reason
        self.threats = threats or []


class APIError(PolaxisError):
    """Raised on unexpected HTTP errors from the Polaxis API.

    Attributes:
        status_code: HTTP status code.
        response_body: Raw response text.
    """

    def __init__(self, status_code: int, response_body: str = ""):
        super().__init__(f"Polaxis API returned HTTP {status_code}: {response_body[:200]}")
        self.status_code = status_code
        self.response_body = response_body
