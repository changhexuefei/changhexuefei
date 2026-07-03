from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path


USER = "changhexuefei"
ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
ASSETS = ROOT / "assets"
CHART = ASSETS / "commit-activity.svg"


def request_json(url: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USER}-profile-updater",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def safe_request(url: str, fallback):
    try:
        return request_json(url)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return fallback


def fetch_repos():
    repos = safe_request(
        f"https://api.github.com/users/{USER}/repos?sort=updated&per_page=12",
        [],
    )
    return [repo for repo in repos if not repo.get("archived")]


def fetch_commits(repos):
    since = datetime.now(timezone.utc) - timedelta(days=13)
    since = since.replace(hour=0, minute=0, second=0, microsecond=0)
    commits = []
    for repo in repos[:6]:
        name = repo["name"]
        url = (
            f"https://api.github.com/repos/{USER}/{name}/commits"
            f"?since={since.isoformat().replace('+00:00', 'Z')}&per_page=100"
        )
        commits.extend(safe_request(url, []))
    return commits


def day_series(commits):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    days = OrderedDict()
    for offset in range(13, -1, -1):
        day = today - timedelta(days=offset)
        days[day.date().isoformat()] = {"label": f"{day.month}/{day.day}", "count": 0}

    for commit in commits:
        data = commit.get("commit", {})
        date_text = (
            data.get("author", {}).get("date")
            or data.get("committer", {}).get("date")
        )
        if not date_text:
            continue
        key = datetime.fromisoformat(date_text.replace("Z", "+00:00")).date().isoformat()
        if key in days:
            days[key]["count"] += 1

    return list(days.values())


def escape_xml(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_chart(days):
    width, height = 920, 300
    pad = {"top": 30, "right": 32, "bottom": 46, "left": 46}
    inner_w = width - pad["left"] - pad["right"]
    inner_h = height - pad["top"] - pad["bottom"]
    max_count = max(1, *(day["count"] for day in days))

    points = []
    for index, day in enumerate(days):
        x = pad["left"] + inner_w * index / max(1, len(days) - 1)
        y = pad["top"] + inner_h - (day["count"] / max_count) * inner_h
        points.append((x, y, day))

    line = " ".join(
        f"{'M' if index == 0 else 'L'}{x:.1f},{y:.1f}"
        for index, (x, y, _) in enumerate(points)
    )
    base_y = pad["top"] + inner_h
    area = f"{line} L{points[-1][0]:.1f},{base_y:.1f} L{points[0][0]:.1f},{base_y:.1f} Z"
    grid = "\n".join(
        f'<line x1="{pad["left"]}" y1="{pad["top"] + inner_h * ratio:.1f}" '
        f'x2="{width - pad["right"]}" y2="{pad["top"] + inner_h * ratio:.1f}" '
        'stroke="rgba(24,32,38,.10)" stroke-width="1"/>'
        for ratio in (0, 0.25, 0.5, 0.75, 1)
    )
    dots = "\n".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#fffdfa" stroke="#2f7d7b" stroke-width="3"/>'
        + (f'<text x="{x:.1f}" y="{y - 12:.1f}" text-anchor="middle" fill="#182026" '
           f'font-size="12" font-weight="700">{day["count"]}</text>' if day["count"] else "")
        for x, y, day in points
    )
    labels = "\n".join(
        f'<text x="{x:.1f}" y="{height - 14}" text-anchor="middle" fill="#66727d" '
        f'font-size="12" font-weight="700">{escape_xml(day["label"])}</text>'
        for index, (x, _, day) in enumerate(points)
        if index == 0 or index == len(points) - 1 or index % 3 == 0
    )

    total = sum(day["count"] for day in days)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Recent 14 day commit activity">
  <rect width="100%" height="100%" rx="8" fill="#fffdfa"/>
  <text x="46" y="25" fill="#182026" font-size="16" font-weight="700">Recent 14-day public commit activity · {total} commits</text>
  {grid}
  <line x1="{pad["left"]}" y1="{base_y:.1f}" x2="{width - pad["right"]}" y2="{base_y:.1f}" stroke="rgba(24,32,38,.18)" stroke-width="1"/>
  <path d="{area}" fill="rgba(47,125,123,.12)"/>
  <path d="{line}" fill="none" stroke="#2f7d7b" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
  {dots}
  {labels}
</svg>
"""
    ASSETS.mkdir(exist_ok=True)
    CHART.write_text(svg, encoding="utf-8")


def repo_line(repo):
    name = repo["name"]
    url = repo["html_url"]
    language = repo.get("language") or "Mixed"
    description = repo.get("description") or "Public repository activity from GitHub."
    updated = repo["updated_at"][:10]
    fork = " · fork" if repo.get("fork") else ""
    return f"- [{name}]({url}) · `{language}` · updated `{updated}`{fork}\n  {description}"


def render_readme(repos, days):
    top_repos = repos[:6]
    total_commits = sum(day["count"] for day in days)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    repo_count = len(repos)

    repo_block = "\n".join(repo_line(repo) for repo in top_repos) or "- No public repositories found."

    readme = f"""# Hi, I'm changhexuefei

十年饮冰，热血未凉。

I build and collect engineering notes around Kotlin, Python, instrument control, data visualization, and personal publishing. My GitHub profile is automatically refreshed from public GitHub data, while my personal site works as the cleaner long-form entry.

## Personal Site

[changhexuefei.github.io](https://changhexuefei.github.io/)

## Live GitHub Snapshot

- Public repositories scanned: **{repo_count}**
- Public commits in the last 14 days: **{total_commits}**
- Last generated: **{generated_at}**

![Recent public commit activity](assets/commit-activity.svg)

## Recently Active Repositories

{repo_block}

## Tech Direction

```text
Kotlin / Compose Multiplatform / Lets-Plot
Python / PyVISA / PyMeasure
Java / JVisa
GitHub Pages / HTML / CSS / JavaScript
```

## Links

- Website: <https://changhexuefei.github.io/>
- GitHub: <https://github.com/changhexuefei>
"""
    README.write_text(readme, encoding="utf-8")


def main():
    repos = fetch_repos()
    commits = fetch_commits(repos)
    days = day_series(commits)
    render_chart(days)
    render_readme(repos, days)


if __name__ == "__main__":
    main()
