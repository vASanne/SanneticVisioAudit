"""Shared constructors for check results."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain import CheckResult, CheckStatus, Severity


@dataclass(frozen=True)
class Spec:
    """Stable metadata for one check."""

    check_id: str
    severity: Severity
    title: str
    recommendation: str
    quick_win: bool = False


def result(
    spec: Spec,
    status: CheckStatus,
    description: str,
    affected_urls: tuple[str, ...] = (),
    recommendation: str | None = None,
) -> CheckResult:
    """Build a check result from its spec and a page-specific explanation."""

    return CheckResult(
        check_id=spec.check_id,
        status=status,
        severity=spec.severity,
        title=spec.title,
        description=description,
        recommendation=recommendation or spec.recommendation,
        affected_urls=affected_urls,
        quick_win=spec.quick_win,
    )
