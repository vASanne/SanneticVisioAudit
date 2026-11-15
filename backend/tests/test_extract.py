"""HTML extraction ignores script text and keeps document facts."""

from app.crawler.types import CrawledPage
from app.extractors.html_extract import extract_page


def test_visible_words_exclude_scripts_and_links_stay_absolute() -> None:
    paragraph = " ".join(f"wort{index}" for index in range(40))
    script = " ".join(f"script{index}" for index in range(80))
    html = f"""<!doctype html>
    <html><head>
      <title>Titel der Seite</title>
      <meta name="description" content="Kurzbeschreibung der Leistung">
      <link rel="canonical" href="/leistung">
    </head><body>
      <h1>Leistung</h1>
      <p>{paragraph}</p>
      <a href="/kontakt">Kontakt</a>
      <script>{script}</script>
    </body></html>
    """
    snapshot = extract_page(
        CrawledPage(
            requested_url="https://example.com/leistung",
            final_url="https://example.com/leistung",
            status_code=200,
            redirect_count=0,
            redirect_loop=False,
            content_type="text/html; charset=utf-8",
            header_robots=None,
            body=html.encode(),
        )
    )
    assert snapshot.title == "Titel der Seite"
    assert snapshot.h1 == ("Leistung",)
    assert snapshot.canonical == "https://example.com/leistung"
    assert snapshot.word_count == 42
    assert "script0" not in snapshot.text
    assert "https://example.com/kontakt" in snapshot.links
