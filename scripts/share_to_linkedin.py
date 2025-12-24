"""Shares a selected cybersecurity article to LinkedIn with AI-generated message."""
from __future__ import annotations

import datetime as dt
import json
import os
import random
from pathlib import Path
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
CACHE_FILE = DATA_DIR / "news_cache.json"
LINKEDIN_STATE_FILE = DATA_DIR / "linkedin_state.json"


class LinkedInPoster:
    def __init__(self):
        self.access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        self.user_id = os.getenv("LINKEDIN_USER_ID")  # LinkedIn URN

        if not self.access_token or not self.user_id:
            raise ValueError(
                "Missing LinkedIn credentials. Set LINKEDIN_ACCESS_TOKEN and LINKEDIN_USER_ID"
            )

    def post(self, message: str, article_url: str) -> dict:
        """Post a message with article link to LinkedIn."""
        url = "https://api.linkedin.com/v2/ugcPosts"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        payload = {
            "author": self.user_id,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": message
                    },
                    "shareMediaCategory": "ARTICLE",
                    "media": [
                        {
                            "status": "READY",
                            "originalUrl": article_url,
                        }
                    ],
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()


class ArticleSelector:
    def __init__(self, cache_path: Path, state_path: Path):
        self.cache_path = cache_path
        self.state_path = state_path
        self.shared_articles = self._load_state()

    def _load_state(self) -> set:
        """Load previously shared article URLs."""
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text())
                return set(data.get("shared_articles", []))
            except json.JSONDecodeError:
                return set()
        return set()

    def _save_state(self) -> None:
        """Save shared article URLs."""
        data = {
            "shared_articles": list(self.shared_articles),
            "last_shared_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        self.state_path.write_text(json.dumps(data, indent=2))

    def select_article(self) -> Optional[dict]:
        """
        Select the best article to share from cache.
        Priority: CRITICAL > HIGH > MEDIUM > LOW
        Excludes already shared articles.
        """
        if not self.cache_path.exists():
            return None

        cache = json.loads(self.cache_path.read_text())

        # Filter out already shared articles
        available = {
            url: data for url, data in cache.items()
            if url not in self.shared_articles
        }

        if not available:
            # Reset if all articles have been shared
            self.shared_articles.clear()
            available = cache

        # Group by severity
        by_severity = {
            "CRITICAL": [],
            "HIGH": [],
            "MEDIUM": [],
            "LOW": [],
        }

        for url, data in available.items():
            severity = data.get("severity", "LOW")
            article = {
                "url": url,
                "title": data.get("title", ""),
                "summary": data.get("summary", ""),
                "source": data.get("source", ""),
                "severity": severity,
                "categories": data.get("categories", []),
            }
            by_severity[severity].append(article)

        # Select from highest severity available
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if by_severity[severity]:
                selected = random.choice(by_severity[severity])
                self.shared_articles.add(selected["url"])
                self._save_state()
                return selected

        return None


class MessageGenerator:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and OpenAI is not None:
            self.client: Optional[OpenAI] = OpenAI()
        else:
            self.client = None

    def generate(self, article: dict) -> str:
        """Generate a personalized LinkedIn message for the article."""
        if not self.client:
            return self._fallback_message(article)

        severity = article.get("severity", "MEDIUM")
        title = article.get("title", "")
        summary = article.get("summary", "")
        source = article.get("source", "")

        prompt = f"""Generate a professional LinkedIn post (max 200 words) for this cybersecurity article.

Article: {title}
Source: {source}
Severity: {severity}
Summary: {summary}

Requirements:
- Write in English
- Professional but engaging tone
- Highlight why this matters to cybersecurity professionals
- Include relevant hashtags (2-4)
- Add a call-to-action
- Don't include the article link (it will be attached automatically)

The message should match the severity level - more urgent for CRITICAL/HIGH threats."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a cybersecurity expert sharing insights on LinkedIn."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return self._fallback_message(article)

    def _fallback_message(self, article: dict) -> str:
        """Generate a simple fallback message without AI."""
        severity = article.get("severity", "MEDIUM")
        title = article.get("title", "")

        severity_emoji = {
            "CRITICAL": "🚨",
            "HIGH": "⚠️",
            "MEDIUM": "📊",
            "LOW": "ℹ️",
        }

        emoji = severity_emoji.get(severity, "📰")

        messages = {
            "CRITICAL": f"{emoji} CRITICAL ALERT: {title}\n\nThis is a high-priority threat that requires immediate attention from security teams. Stay informed and take action.\n\n#CyberSecurity #ThreatIntelligence #InfoSec #SecurityAlert",
            "HIGH": f"{emoji} Important Security Update: {title}\n\nThis high-severity issue deserves your attention. Keeping up with the latest threats is essential for maintaining a strong security posture.\n\n#CyberSecurity #InfoSec #ThreatIntel #Security",
            "MEDIUM": f"{emoji} Security Insight: {title}\n\nAnother important development in the cybersecurity landscape. Stay ahead of emerging threats.\n\n#CyberSecurity #InfoSec #Security",
            "LOW": f"{emoji} From TheCyberNews: {title}\n\nStaying informed on cybersecurity trends and news. Knowledge is the first line of defense.\n\n#CyberSecurity #InfoSec #TechNews",
        }

        return messages.get(severity, messages["MEDIUM"])


def main() -> None:
    """Main execution: select article, generate message, post to LinkedIn."""
    print("🔍 Selecting article to share on LinkedIn...")

    selector = ArticleSelector(CACHE_FILE, LINKEDIN_STATE_FILE)
    article = selector.select_article()

    if not article:
        print("❌ No articles available to share")
        return

    print(f"✅ Selected: {article['title']}")
    print(f"   Severity: {article['severity']}")
    print(f"   Source: {article['source']}")

    print("\n🤖 Generating personalized message...")
    generator = MessageGenerator()
    message = generator.generate(article)

    print(f"\n📝 Message preview:\n{message}\n")

    print("📤 Posting to LinkedIn...")
    poster = LinkedInPoster()
    result = poster.post(message, article["url"])

    print(f"✅ Successfully posted to LinkedIn!")
    print(f"   Post ID: {result.get('id', 'N/A')}")


if __name__ == "__main__":
    main()
