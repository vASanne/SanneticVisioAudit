"""Score weights stay explicit and stable."""

from app.domain import CheckResult
from app.scoring.engine import score_checks


def _check(check_id: str, status: str, severity: str) -> CheckResult:
    return CheckResult(check_id, status, severity, check_id, "Beschreibung", "Empfehlung")  # type: ignore[arg-type]


def test_weights_and_warning_factor() -> None:
    scores = {item.category: item.score for item in score_checks([
        _check("T01", "fail", "critical"),
        _check("O01", "pass", "high"),
        _check("O02", "warning", "medium"),
        _check("G04", "pass", "critical"),
    ])}
    # technical: 0/5, on-page: (3 + 1) / 5, seo: (0 + 3 + 1) / 10, geo: 5/5, overall: 9/15
    assert scores["technical"] == 0.0
    assert scores["onpage"] == 80.0
    assert scores["seo"] == 40.0
    assert scores["geo"] == 100.0
    assert scores["overall"] == 60.0


def test_details_record_each_check() -> None:
    scored = score_checks([_check("G01", "warning", "critical")])
    overall = next(item for item in scored if item.category == "overall")
    checks = overall.details["checks"]
    assert isinstance(checks, list)
    assert checks[0]["earned"] == 2.5
    assert overall.score == 50.0
