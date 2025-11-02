# Evil Corporate – Autonomous Cybersecurity Briefings

Evil Corporate is an autonomous workflow that collects the latest cybersecurity
headlines, summarises them with an LLM, and publishes a dark, minimalist brief
on GitHub Pages.

## Features

- Fetches from a curated list of well-known cybersecurity RSS feeds.
- Summaries generated via OpenAI (or a deterministic fallback when the API key
  is not configured).
- Caches processed articles to avoid duplicate summaries.
- Renders a fully static site (`docs/index.html`) suitable for GitHub Pages.
- Ships with a scheduled GitHub Actions workflow for daily updates.

## Project structure

```
├── data/
│   └── news_cache.json       # persistent cache of processed articles
├── docs/
│   └── index.html            # generated static site (committed by automation)
├── scripts/
│   └── update_news.py        # main automation entrypoint
├── templates/
│   └── index.html.j2         # Jinja template for the site
├── requirements.txt          # runtime dependencies
└── .github/workflows/
    └── update-news.yml       # scheduled automation
```

## Running locally

1. Create and activate a Python 3.11+ virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Export your OpenAI API key (optional but recommended for high-quality
   summaries):
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```
4. (Optional) Override the RSS feeds:
   ```bash
   export NEWS_AGENT_FEEDS="https://example.com/feed.xml,https://another.com/rss"
   ```
5. Run the updater:
   ```bash
   python scripts/update_news.py
   ```

The script will refresh `docs/index.html`, which you can open locally or serve
with any static site host.

## Automation with GitHub Actions

A workflow is included under `.github/workflows/update-news.yml`. To enable it:

1. Push this repository to GitHub.
2. In the repository settings, configure the following secrets:
   - `OPENAI_API_KEY`: your OpenAI API key (optional but recommended).
   - `PAT_PUSH_TOKEN`: a Personal Access Token with `contents: write` scope if
     you need to push from GitHub Actions. The default `GITHUB_TOKEN` is
     sufficient for most setups.
3. Enable GitHub Pages to serve the `docs/` folder.

The workflow runs every day at 07:00 UTC. It installs dependencies, executes the
update script, commits the refreshed `docs/index.html`, and pushes the changes
back to the repository.

## Customising the site

- Modify `templates/index.html.j2` for different layouts or branding.
- Adjust `scripts/update_news.py` to tweak summarisation prompts, caching, or
  retention.
- Extend the workflow schedule to update more frequently.

## Disclaimer

Always review generated content before redistribution and ensure compliance with
source licensing terms when republishing summaries.
