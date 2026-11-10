# Hidden Hire

A personal, local-first AI job search agent for tech roles. It finds underrated jobs from company career pages, remote and country-specific boards, and community channels, then scores them locally against my profile.

The agent never applies or sends emails. Applications are always done manually.

> Work in progress.

## How it works

- **Fetcher** (GitHub Actions, every 3 hours): collects public job data and pushes it to a private data repo. No personal data.
- **Local app** (my PC): pulls job data, scores jobs against my profile, and serves a dashboard on `127.0.0.1`.

## Setup

Requires Python 3.12.

```bash
conda create -n hidden-hire python=3.12 -y
conda activate hidden-hire
pip install -r requirements.txt
cp .env.example .env
```

## Privacy

Personal files (`profile/`, `cv/`, `data/`, `*.db`, `.env`, `settings.yaml`) are git-ignored and never committed.

## License

MIT