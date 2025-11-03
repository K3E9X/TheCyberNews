# Evil Corporate – Autonomous Cybersecurity Briefings

Evil Corporate is an autonomous workflow that collects the latest cybersecurity
headlines, lets an LLM agent reason over them, and publishes a dark, minimalist
brief on GitHub Pages – end to end with no manual touch.

## Features

- Fetches from a curated list of well-known cybersecurity RSS feeds.
- Summaries generated via OpenAI (or a deterministic fallback when the API key
  is not configured).
- LLM-powered **Briefing Composer** produces an executive headline, narrative,
  key themes, and action items every run, persisting memory between cycles.
- Agent state, cache, rendered site, and even commit messages are written back
  automatically for a fully self-updating public page.
- Ships with a scheduled GitHub Actions workflow for daily updates.

## Project structure

```
├── data/
│   ├── agent_state.json      # persisted agent memory between runs
│   ├── commit_message.txt    # headline-driven commit message produced by the agent
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
   narratives and summaries):
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

The script will refresh `docs/index.html`, update `data/agent_state.json` with
the latest brief, and draft a commit message under `data/commit_message.txt`.
Open the generated site locally or serve it with any static host.

## Automation with GitHub Actions

A workflow is included under `.github/workflows/update-news.yml`. To enable it:

1. Push this repository to GitHub.
2. In the repository settings, configure the following secrets:
   - `OPENAI_API_KEY`: your OpenAI API key (optional but recommended).
   - `PAT_PUSH_TOKEN`: a Personal Access Token with `contents: write` scope if
     you need to push from GitHub Actions. The default `GITHUB_TOKEN` is
     sufficient for most setups.
   - `NEWS_AGENT_FEEDS`: (optional) comma-separated list of RSS/Atom feeds to
     override the defaults.
3. Enable GitHub Pages to serve the `docs/` folder.

The workflow runs every day at 07:00 UTC. It installs dependencies, executes the
update script, stages the regenerated artefacts, and opens a brand-new pull
request with the agent-authored commit message, headline, and briefing notes.
This avoids force-pushing over an existing branch and keeps the history clean
when multiple reviews happen in parallel. Once the new pull request is opened,
the automation closes any previous bot PRs and attempts to merge the fresh
update into the base branch. If GitHub reports a conflict, the workflow leaves a
comment explaining what happened so you can resolve it manually before the next
scheduled run.

## Customising the site

- Modify `templates/index.html.j2` for different layouts or branding.
- Adjust `scripts/update_news.py` to tweak summarisation prompts, caching, or
  retention.
- Extend the workflow schedule to update more frequently.

## Disclaimer

Always review generated content before redistribution and ensure compliance with
source licensing terms when republishing summaries.
