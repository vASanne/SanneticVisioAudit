"""Optional LLM advisory. Never feeds the deterministic score."""

from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.domain import PageSnapshot


def summarize_audit(pages: tuple[PageSnapshot, ...]) -> str | None:
    """Ask an OpenAI-compatible chat model for a short German content note."""

    settings = get_settings()
    key = settings.llm_api_key.strip()
    if not key:
        return None
    samples = []
    for page in pages[:5]:
        if not page.is_html or page.word_count < 20:
            continue
        samples.append(f"URL: {page.final_url}\nTitle: {page.title or '–'}\nText: {page.text[:1200]}")
    if not samples:
        return None
    body = {
        "model": settings.llm_model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Du bist ein SEO- und GEO-Berater. Antworte auf Deutsch in höchstens "
                    "120 Wörtern. Keine Check-IDs. Nenne konkrete inhaltliche Stärken und Lücken."
                ),
            },
            {"role": "user", "content": "\n\n".join(samples)},
        ],
    }
    try:
        response = httpx.post(
            settings.llm_api_url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=body,
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        choices = payload.get("choices") if isinstance(payload, dict) else None
        if not isinstance(choices, list) or not choices:
            return None
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str) and content.strip():
            return content.strip()[:2000]
    except (httpx.HTTPError, ValueError, TypeError, IndexError, KeyError):
        return None
    return None
