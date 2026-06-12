"""Scrapers for LeetCode problems, NeetCode transcripts, and local markdown sources."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

LEETCODE_GRAPHQL = "https://leetcode.com/graphql"
NEETCODE_BASE = "https://neetcode.io"


@dataclass
class ScrapedDocument:
    """Normalized document from any data source."""

    doc_id: str
    title: str
    content: str
    source: str  # leetcode | neetcode | discuss | user_strategy
    metadata: dict[str, Any] = field(default_factory=dict)


class LeetCodeScraper:
    """Fetch LeetCode problem statements via GraphQL or local JSON fallback."""

    PROBLEM_QUERY = """
    query getQuestionDetail($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        questionId
        title
        titleSlug
        difficulty
        content
        topicTags { name slug }
        hints
      }
    }
    """

    def __init__(self, session_cookie: str | None = None, timeout: int = 30):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": "leetcode-mentor-bot/1.0",
            }
        )
        if session_cookie:
            self.session.cookies.set("LEETCODE_SESSION", session_cookie)
        self.timeout = timeout

    def fetch_problem(self, slug: str) -> ScrapedDocument | None:
        try:
            resp = self.session.post(
                LEETCODE_GRAPHQL,
                json={
                    "query": self.PROBLEM_QUERY,
                    "variables": {"titleSlug": slug},
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json().get("data", {}).get("question")
            if not data:
                return None
            return self._to_document(data)
        except requests.RequestException:
            return None

    def load_from_json(self, path: Path) -> list[ScrapedDocument]:
        """Load problems from a local JSON file (offline / demo mode)."""
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = raw if isinstance(raw, list) else raw.get("problems", [])
        docs: list[ScrapedDocument] = []
        for item in items:
            docs.append(
                ScrapedDocument(
                    doc_id=f"lc_{item.get('questionId', item.get('slug', 'unknown'))}",
                    title=item["title"],
                    content=self._html_to_text(item.get("content", item.get("description", ""))),
                    source="leetcode",
                    metadata={
                        "slug": item.get("slug", item.get("titleSlug", "")),
                        "difficulty": item.get("difficulty", "Unknown"),
                        "tags": [t.get("name", t) if isinstance(t, dict) else t for t in item.get("topicTags", item.get("tags", []))],
                        "hints": item.get("hints", []),
                    },
                )
            )
        return docs

    def load_from_markdown_dir(self, directory: Path) -> list[ScrapedDocument]:
        docs: list[ScrapedDocument] = []
        for path in sorted(directory.glob("*.md")):
            slug = path.stem
            text = path.read_text(encoding="utf-8")
            title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
            title = title_match.group(1) if title_match else slug.replace("-", " ").title()
            docs.append(
                ScrapedDocument(
                    doc_id=f"lc_{slug}",
                    title=title,
                    content=text,
                    source="leetcode",
                    metadata={"slug": slug, "difficulty": "Unknown", "tags": []},
                )
            )
        return docs

    def _to_document(self, data: dict[str, Any]) -> ScrapedDocument:
        return ScrapedDocument(
            doc_id=f"lc_{data['questionId']}",
            title=data["title"],
            content=self._html_to_text(data.get("content", "")),
            source="leetcode",
            metadata={
                "slug": data.get("titleSlug", ""),
                "difficulty": data.get("difficulty", "Unknown"),
                "tags": [t["name"] for t in data.get("topicTags", [])],
                "hints": data.get("hints", []),
            },
        )

    @staticmethod
    def _html_to_text(html: str) -> str:
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator="\n", strip=True)


class NeetCodeScraper:
    """Load NeetCode video transcripts from local files or scrape problem pages."""

    def __init__(self, timeout: int = 30):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "leetcode-mentor-bot/1.0"
        self.timeout = timeout

    def load_transcripts_dir(self, directory: Path) -> list[ScrapedDocument]:
        docs: list[ScrapedDocument] = []
        for path in sorted(directory.glob("*.txt")):
            slug = path.stem
            content = path.read_text(encoding="utf-8")
            docs.append(
                ScrapedDocument(
                    doc_id=f"neet_{slug}",
                    title=slug.replace("-", " ").title(),
                    content=content,
                    source="neetcode",
                    metadata={"slug": slug, "type": "transcript"},
                )
            )
        return docs

    def fetch_problem_page(self, slug: str) -> ScrapedDocument | None:
        try:
            url = f"{NEETCODE_BASE}/problems/{slug}"
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            article = soup.find("article") or soup.find("main")
            if not article:
                return None
            return ScrapedDocument(
                doc_id=f"neet_{slug}",
                title=slug.replace("-", " ").title(),
                content=article.get_text(separator="\n", strip=True),
                source="neetcode",
                metadata={"slug": slug, "url": url},
            )
        except requests.RequestException:
            return None


class MarkdownSourceLoader:
    """Load user strategies and LC Discuss posts saved as markdown."""

    def load_directory(self, directory: Path, source: str) -> list[ScrapedDocument]:
        docs: list[ScrapedDocument] = []
        for path in sorted(directory.glob("**/*.md")):
            slug = path.stem
            content = path.read_text(encoding="utf-8")
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = title_match.group(1) if title_match else slug
            docs.append(
                ScrapedDocument(
                    doc_id=f"{source}_{slug}",
                    title=title,
                    content=content,
                    source=source,
                    metadata={"slug": slug, "file": str(path)},
                )
            )
        return docs
