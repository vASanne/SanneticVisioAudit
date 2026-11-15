"""robots.txt policy used by the crawler and the T05 / G01 checks."""

from __future__ import annotations

import re
from urllib.robotparser import RobotFileParser


class RobotsPolicy:
    """A fetched robots.txt, or the default allow when the file is absent."""

    def __init__(self, body: str | None, status_code: int | None) -> None:
        self.body = body or ""
        self.status_code = status_code
        self._parser = RobotFileParser()
        if self.body.strip():
            self._parser.parse(self.body.splitlines())

    @property
    def exists(self) -> bool:
        return self.status_code == 200 and bool(self.body.strip())

    @property
    def unreadable(self) -> bool:
        return self.status_code is None or self.status_code >= 500

    def allowed(self, user_agent: str, url: str) -> bool:
        """Return whether robots.txt permits the fetch. A missing file allows it."""

        if not self.body.strip():
            return True
        return bool(self._parser.can_fetch(user_agent, url))

    def crawl_delay(self, user_agent: str) -> float:
        if not self.body.strip():
            return 0.0
        value = self._parser.crawl_delay(user_agent)
        if value is None:
            return 0.0
        return float(value)

    def sitemaps(self) -> list[str]:
        return re.findall(r"(?im)^sitemap:\s*(\S+)", self.body)
