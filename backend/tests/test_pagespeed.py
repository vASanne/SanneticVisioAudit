"""PageSpeed parsing and the T09 bands."""

from app.analyzers.engine import run_checks
from app.domain import PageSpeedFacts
from app.services.pagespeed import parse_pagespeed
from tests.test_checks import by_id, context


def test_field_data_wins_over_lab_and_cls_is_scaled() -> None:
    facts = parse_pagespeed(
        {
            "loadingExperience": {
                "metrics": {
                    "LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 1800},
                    "INTERACTION_TO_NEXT_PAINT": {"percentile": 120},
                    "CUMULATIVE_LAYOUT_SHIFT_SCORE": {"percentile": 5},
                }
            },
            "lighthouseResult": {"audits": {"largest-contentful-paint": {"numericValue": 9000}}},
        }
    )
    assert facts is not None
    assert facts.source == "field"
    assert facts.lcp_ms == 1800
    assert facts.cls == 0.05


def test_lab_fallback_and_poor_lcp_fails() -> None:
    facts = parse_pagespeed(
        {
            "lighthouseResult": {
                "audits": {
                    "largest-contentful-paint": {"numericValue": 5200},
                    "cumulative-layout-shift": {"numericValue": 0.02},
                }
            }
        }
    )
    assert facts is not None
    assert facts.source == "lab"
    result = by_id(context(pagespeed=facts))["T09"]
    assert result.status == "fail"
    assert "LCP" in result.description


def test_good_vitals_pass_and_missing_key_skips_the_check() -> None:
    facts = PageSpeedFacts("lab", lcp_ms=2000, inp_ms=100, cls=0.05)
    assert by_id(context(pagespeed=facts))["T09"].status == "pass"
    assert "T09" not in {item.check_id for item in run_checks(context())}
