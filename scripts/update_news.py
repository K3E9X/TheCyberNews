"""Automates fetching, summarising and publishing cybersecurity news."""
from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

try:
    import feedparser
except ImportError as exc:  # pragma: no cover - dependency guard
    raise SystemExit(
        "feedparser is required. Install dependencies via 'pip install -r requirements.txt'"
    ) from exc

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency at runtime
    OpenAI = None  # type: ignore

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
SITE_DIR = ROOT_DIR / "docs"
TEMPLATE_DIR = ROOT_DIR / "templates"

DEFAULT_FEEDS = [
    "https://www.darkreading.com/rss.xml",
    "https://feeds.feedburner.com/TheHackersNews",
    "https://www.bleepingcomputer.com/feed/",
    "https://www.cisa.gov/news-events/alerts.xml",
    "https://www.scmagazine.com/home/feed/",
]

SUMMARY_MODEL = os.getenv("NEWS_AGENT_MODEL", "gpt-4o-mini")
CACHE_FILE = DATA_DIR / "news_cache.json"
STATE_FILE = DATA_DIR / "agent_state.json"
COMMIT_MESSAGE_FILE = DATA_DIR / "commit_message.txt"


def _ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT_DIR / "templates").mkdir(parents=True, exist_ok=True)


@dataclass
class NewsItem:
    title: str
    link: str
    published: dt.datetime
    source: str
    summary: str = ""
    categories: List[str] = field(default_factory=list)
    image: str = ""

    @property
    def published_iso(self) -> str:
        return self.published.isoformat()

    @property
    def published_human(self) -> str:
        return self.published.strftime("%d %b %Y %H:%M UTC")


class NewsCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.entries: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self.entries = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                self.entries = {}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.entries, indent=2, sort_keys=True))

    def get(self, link: str) -> Optional[dict]:
        return self.entries.get(link)

    def set(self, link: str, item: NewsItem) -> None:
        self.entries[link] = {
            "title": item.title,
            "summary": item.summary,
            "published": item.published_iso,
            "source": item.source,
            "categories": item.categories,
            "image": item.image,
        }


class Summariser:
    def __init__(self, model: str = SUMMARY_MODEL) -> None:
        self.model = model
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and OpenAI is not None:
            self.client: Optional[OpenAI] = OpenAI()
        else:
            self.client = None

    def summarise(self, item: NewsItem) -> str:
        if not self.client:
            # Fallback summary if the OpenAI client is not configured.
            snippet = (item.title + " " + item.summary).strip()
            return snippet[:280] + ("…" if len(snippet) > 280 else "")

        prompt = (
            "You are a cybersecurity analyst. Summarise the following news article "
            "in 3 concise bullet points highlighting the impact, the actors, and "
            "the mitigation or response. Include a short risk rating (Low/Medium/High)."
        )
        content = (
            f"Title: {item.title}\n"
            f"Summary: {item.summary}\n"
            f"Link: {item.link}\n"
        )
        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": prompt,
                },
                {
                    "role": "user",
                    "content": content,
                },
            ],
        )
        return response.output_text.strip()


@dataclass
class DailyBrief:
    headline: str
    narrative: str
    key_themes: List[str]
    action_items: List[str]

    def to_dict(self) -> dict:
        return {
            "headline": self.headline,
            "narrative": self.narrative,
            "key_themes": self.key_themes,
            "action_items": self.action_items,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DailyBrief":
        return cls(
            headline=data.get("headline", ""),
            narrative=data.get("narrative", ""),
            key_themes=list(data.get("key_themes", [])),
            action_items=list(data.get("action_items", [])),
        )


class AgentState:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                self.data = {}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True))

    def previous_brief(self) -> Optional[DailyBrief]:
        latest = self.data.get("latest_brief")
        if not latest:
            return None
        try:
            return DailyBrief.from_dict(latest)
        except Exception:
            return None

    def update_brief(self, brief: DailyBrief) -> None:
        self.data["latest_brief"] = brief.to_dict()
        self.data["last_generated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        self.save()


class BriefingComposer:
    def __init__(self, model: str = SUMMARY_MODEL) -> None:
        self.model = model
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and OpenAI is not None:
            self.client: Optional[OpenAI] = OpenAI()
        else:
            self.client = None

    def compose(self, items: List[NewsItem], previous: Optional[DailyBrief]) -> DailyBrief:
        fallback = DailyBrief(
            headline="Autonomous cybersecurity briefing",
            narrative=(
                "The agent summarised the latest publicly available cybersecurity "
                "stories and refreshed the site automatically. Configure an "
                "OPENAI_API_KEY to enable narrative insights."
            ),
            key_themes=[item.source for item in items[:3]] if items else [],
            action_items=[
                "Review the highlighted incidents and evaluate exposure.",
                "Share the briefing with the blue team.",
            ],
        )

        if not self.client or not items:
            return fallback

        condensed_items = [
            {
                "title": item.title,
                "summary": item.summary,
                "published": item.published_iso,
                "source": item.source,
                "categories": item.categories,
            }
            for item in items
        ]

        system_prompt = (
            "You are CyberNews's fully autonomous cyber threat intelligence agent. "
            "Synthesise the supplied incidents into a concise daily briefing ready for "
            "executive publication on a public GitHub Pages site. Always respond as "
            "valid JSON matching the provided schema."
        )

        previous_context = previous.to_dict() if previous else None

        user_payload = {
            "incidents": condensed_items,
            "previous_brief": previous_context,
        }

        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": json.dumps(user_payload),
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "daily_brief",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "headline": {"type": "string"},
                            "narrative": {"type": "string"},
                            "key_themes": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "action_items": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": [
                            "headline",
                            "narrative",
                            "key_themes",
                            "action_items",
                        ],
                        "additionalProperties": False,
                    },
                },
            },
        )

        try:
            payload = json.loads(response.output_text)
            return DailyBrief.from_dict(payload)
        except (json.JSONDecodeError, TypeError, ValueError):
            return fallback


def _write_commit_message(brief: DailyBrief) -> None:
    message = f"auto: {brief.headline.strip() or 'refresh cybersecurity brief'}"
    COMMIT_MESSAGE_FILE.write_text(message)


def extract_image_from_entry(entry) -> str:
    """Extract image URL from RSS entry using multiple methods."""
    # Try media:content (common in RSS feeds)
    if hasattr(entry, "media_content") and entry.media_content:
        for media in entry.media_content:
            if media.get("medium") == "image" or media.get("type", "").startswith("image/"):
                return media.get("url", "")

    # Try media:thumbnail
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url", "")

    # Try enclosures (podcasts/attachments)
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enclosure in entry.enclosures:
            if enclosure.get("type", "").startswith("image/"):
                return enclosure.get("href", "")

    # Try looking for images in content/summary HTML
    import re
    content = entry.get("content", [{}])[0].get("value", "") if entry.get("content") else entry.get("summary", "")
    if content:
        # Look for img tags
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
        if img_match:
            return img_match.group(1)

    return ""


def parse_entry(entry, source: str) -> Optional[NewsItem]:
    published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not published_parsed:
        return None
    published = dt.datetime(*published_parsed[:6], tzinfo=dt.timezone.utc)
    summary = entry.get("summary", "")
    categories = [tag.get("term", "") for tag in entry.get("tags", []) if tag.get("term")]
    image = extract_image_from_entry(entry)

    return NewsItem(
        title=entry.get("title", "Untitled"),
        link=entry.get("link", ""),
        published=published,
        source=source,
        summary=summary,
        categories=categories,
        image=image,
    )


def fetch_news(feeds: Iterable[str]) -> List[NewsItem]:
    items: List[NewsItem] = []
    for feed_url in feeds:
        parsed = feedparser.parse(feed_url)
        source_title = parsed.feed.get("title", feed_url)
        for entry in parsed.entries:
            item = parse_entry(entry, source_title)
            if item and item.link:
                items.append(item)
    items.sort(key=lambda i: i.published, reverse=True)
    return items


def summarise_news(items: List[NewsItem], cache: NewsCache, summariser: Summariser) -> List[NewsItem]:
    results: List[NewsItem] = []
    for item in items:
        cached = cache.get(item.link)
        if cached:
            item.summary = cached.get("summary", "")
            item.categories = cached.get("categories", [])
            item.image = cached.get("image", item.image)
        else:
            item.summary = summariser.summarise(item)
            cache.set(item.link, item)
        results.append(item)
    cache.save()
    return results


def render_site(
    items: List[NewsItem],
    brief: DailyBrief,
    previous: Optional[DailyBrief],
) -> None:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("index.html.j2")
    content = template.render(
        generated_at=dt.datetime.now(dt.timezone.utc),
        items=items,
        daily_brief=brief,
        previous_brief=previous,
    )
    (SITE_DIR / "index.html").write_text(content, encoding="utf-8")


def main() -> None:
    _ensure_directories()
    feeds_env = os.getenv("NEWS_AGENT_FEEDS")
    feeds = [feed.strip() for feed in feeds_env.split(",") if feed.strip()] if feeds_env else DEFAULT_FEEDS
    cache = NewsCache(CACHE_FILE)
    summariser = Summariser()
    composer = BriefingComposer()
    state = AgentState(STATE_FILE)
    previous_brief = state.previous_brief()
    items = fetch_news(feeds)
    # Keep only the most recent 30 items to avoid unbounded growth.
    items = items[:30]
    items = summarise_news(items, cache, summariser)
    brief = composer.compose(items, previous_brief)
    state.update_brief(brief)
    render_site(items, brief, previous_brief)
    _write_commit_message(brief)


if __name__ == "__main__":
    main()
