"""robots.txt policy used by the crawler and the T05 / G01 checks.

The longest matching Allow or Disallow wins. An equal-length Allow wins.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit
from urllib.robotparser import RobotFileParser


@dataclass(frozen=True)
class _Rule:
    allow: bool
    path: str


@dataclass(frozen=True)
class _Group:
    agents: tuple[str, ...]
    rules: tuple[_Rule, ...]


class RobotsPolicy:
    """A fetched robots.txt, or the default allow when the file is absent."""

    def __init__(self, body: str | None, status_code: int | None) -> None:
        self.body = body or ""
        self.status_code = status_code
        self._parser = RobotFileParser()
        self._groups: tuple[_Group, ...] = ()
        if self.body.strip():
            self._parser.parse(self.body.splitlines())
            self._groups = _parse_groups(self.body)

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
        parts = urlsplit(url)
        rules = _rules_for(self._groups, user_agent)
        return _permitted(rules, unquote(parts.path or "/"), unquote(parts.query))

    def crawl_delay(self, user_agent: str) -> float:
        if not self.body.strip():
            return 0.0
        value = self._parser.crawl_delay(user_agent)
        if value is None:
            return 0.0
        return float(value)

    def sitemaps(self) -> list[str]:
        return re.findall(r"(?im)^sitemap:\s*(\S+)", self.body)


def _rules_for(groups: tuple[_Group, ...], user_agent: str) -> tuple[_Rule, ...]:
    product = user_agent.split("/", 1)[0].strip().lower()
    best: int | None = None
    chosen: list[_Group] = []
    for group in groups:
        score = _specificity(group.agents, product)
        if score is None:
            continue
        if best is None or score > best:
            best = score
            chosen = [group]
        elif score == best:
            chosen.append(group)
    return tuple(rule for group in chosen for rule in group.rules)


def _specificity(agents: tuple[str, ...], product: str) -> int | None:
    best: int | None = None
    for agent in agents:
        agent_name = agent.split("/", 1)[0].strip().lower()
        if not agent_name:
            continue
        if agent_name == "*":
            score = 0
        elif product.startswith(agent_name):
            score = len(agent_name)
        else:
            continue
        if best is None or score > best:
            best = score
    return best


def _parse_groups(body: str) -> tuple[_Group, ...]:
    agents: list[str] = []
    rules: list[_Rule] = []
    groups: list[_Group] = []
    closed = False

    def flush() -> None:
        nonlocal agents, rules, closed
        if agents:
            groups.append(_Group(tuple(agents), tuple(rules)))
        agents = []
        rules = []
        closed = False

    for raw in body.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            if agents:
                closed = True
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            if rules or closed:
                flush()
            agents.append(value)
            continue
        if key in {"allow", "disallow"} and agents:
            closed = False
            if key == "allow" and value == "":
                continue
            rules.append(_Rule(key == "allow" or value == "", value))
    if agents:
        flush()
    return tuple(groups)


def _permitted(rules: tuple[_Rule, ...], path: str, query: str) -> bool:
    best_length = -1
    allowed = True
    for rule in rules:
        length = _match_length(rule.path, path, query)
        if length is None:
            continue
        if length > best_length:
            best_length = length
            allowed = rule.allow
        elif length == best_length and rule.allow:
            allowed = True
    return allowed


def _match_length(pattern: str, path: str, query: str) -> int | None:
    pattern = unquote(pattern)
    target = f"{path}?{query}" if "?" in pattern else path
    if pattern == "":
        return 0
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    if "*" not in body:
        matched = target == body if anchored else target.startswith(body)
        return len(pattern) if matched else None
    expression = "^" + ".*".join(re.escape(piece) for piece in body.split("*"))
    if anchored:
        expression += "$"
    if re.match(expression, target):
        return len(pattern)
    return None
