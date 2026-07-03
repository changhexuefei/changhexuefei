from __future__ import annotations

import json
import os
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
HERO = ASSETS / "profile-hero.svg"


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


def svg_text(value: str, limit: int | None = None) -> str:
    value = " ".join(str(value).split())
    if limit and len(value) > limit:
        value = value[: limit - 1].rstrip() + "..."
    return escape_xml(value)


def render_hero(repos, days, generated_at):
    total_commits = sum(day["count"] for day in days)
    repo_count = len(repos)
    latest = repos[0]["name"] if repos else "public repositories"
    language_counts = {}
    for repo in repos:
        language = repo.get("language") or "Mixed"
        language_counts[language] = language_counts.get(language, 0) + 1
    top_languages = sorted(language_counts.items(), key=lambda item: item[1], reverse=True)[:4]
    language_line = " / ".join(language for language, _ in top_languages) or "Kotlin / Python / Web"

    metric_cards = [
        ("PUBLIC REPOS", repo_count),
        ("14D COMMITS", total_commits),
        ("LATEST FOCUS", latest),
    ]
    metrics = []
    for index, (label, value) in enumerate(metric_cards):
        x = 76 + index * 344
        metrics.append(
            f"""<g>
    <rect x="{x}" y="342" width="304" height="96" rx="18" fill="#111" stroke="#2a2a2a"/>
    <text x="{x + 24}" y="378" fill="#8f8f8f" font-size="13" font-weight="700" letter-spacing="2">{svg_text(label)}</text>
    <text x="{x + 24}" y="417" fill="#f5f5f5" font-size="26" font-weight="800">{svg_text(value, 18)}</text>
  </g>"""
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="520" viewBox="0 0 1200 520" role="img" aria-label="Changhexuefei GitHub profile hero">
  <defs>
    <linearGradient id="shine" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#151515"/>
      <stop offset="0.55" stop-color="#050505"/>
      <stop offset="1" stop-color="#101010"/>
    </linearGradient>
    <filter id="softGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="18" result="blur"/>
      <feColorMatrix in="blur" type="matrix" values="1 0 0 0 0.91  0 1 0 0 0.13  0 0 1 0 0.16  0 0 0 .55 0"/>
      <feBlend in="SourceGraphic"/>
    </filter>
  </defs>
  <rect width="1200" height="520" rx="30" fill="url(#shine)"/>
  <path d="M78 100H1122" stroke="#f5f5f5" stroke-width="1" opacity=".18"/>
  <path d="M78 456H1122" stroke="#f5f5f5" stroke-width="1" opacity=".14"/>
  <path d="M817 112C929 132 1018 188 1084 280" fill="none" stroke="#ffffff" stroke-width="2" opacity=".2"/>
  <path d="M760 292C884 231 988 232 1102 292" fill="none" stroke="#e82127" stroke-width="5" stroke-linecap="round" filter="url(#softGlow)"/>
  <circle cx="1092" cy="292" r="6" fill="#e82127"/>
  <text x="76" y="78" fill="#a8a8a8" font-size="14" font-weight="700" letter-spacing="4">AUTOMATED GITHUB PROFILE</text>
  <text x="74" y="178" fill="#f7f7f7" font-size="72" font-weight="900" letter-spacing="5">CHANGHEXUEFEI</text>
  <text x="78" y="228" fill="#d8d8d8" font-size="24" font-weight="500">十年饮冰，热血未凉。</text>
  <text x="78" y="272" fill="#8d8d8d" font-size="18" font-weight="600">Kotlin · Python · Instrument Control · Data Visualization · Personal Publishing</text>
  <text x="78" y="306" fill="#6f6f6f" font-size="15">Live data rebuilt on schedule from public GitHub activity · {svg_text(generated_at)}</text>
  {"".join(metrics)}
  <text x="78" y="486" fill="#777" font-size="14" font-weight="700" letter-spacing="2">{svg_text(language_line, 80)}</text>
</svg>
"""
    ASSETS.mkdir(exist_ok=True)
    HERO.write_text(svg, encoding="utf-8")


def render_chart(days):
    width, height = 1200, 360
    pad = {"top": 72, "right": 70, "bottom": 62, "left": 70}
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
        'stroke="#252525" stroke-width="1"/>'
        for ratio in (0, 0.25, 0.5, 0.75, 1)
    )
    dots = "\n".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#050505" stroke="#e82127" stroke-width="3"/>'
        + (
            f'<text x="{x:.1f}" y="{y - 14:.1f}" text-anchor="middle" fill="#f5f5f5" '
            f'font-size="12" font-weight="700">{day["count"]}</text>'
            if day["count"]
            else ""
        )
        for x, y, day in points
    )
    labels = "\n".join(
        f'<text x="{x:.1f}" y="{height - 24}" text-anchor="middle" fill="#777" '
        f'font-size="12" font-weight="700">{escape_xml(day["label"])}</text>'
        for index, (x, _, day) in enumerate(points)
        if index == 0 or index == len(points) - 1 or index % 3 == 0
    )

    total = sum(day["count"] for day in days)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Recent 14 day commit activity">
  <rect width="100%" height="100%" rx="24" fill="#050505"/>
  <text x="70" y="42" fill="#f5f5f5" font-size="20" font-weight="900" letter-spacing="3">PUBLIC COMMIT TRAJECTORY</text>
  <text x="70" y="66" fill="#7b7b7b" font-size="14" font-weight="700">{total} commits over the last 14 days</text>
  {grid}
  <line x1="{pad["left"]}" y1="{base_y:.1f}" x2="{width - pad["right"]}" y2="{base_y:.1f}" stroke="#333" stroke-width="1"/>
  <path d="{area}" fill="#e82127" opacity=".12"/>
  <path d="{line}" fill="none" stroke="#e82127" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
  {dots}
  {labels}
</svg>
"""
    ASSETS.mkdir(exist_ok=True)
    CHART.write_text(svg, encoding="utf-8")


def render_readme(repos, days):
    total_commits = sum(day["count"] for day in days)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    repo_count = len(repos)

    readme = f"""<p align="center">
  <img src="assets/profile-hero.svg" alt="Changhexuefei automated GitHub profile hero" width="100%" />
</p>

<p align="center">
  <a href="https://changhexuefei.github.io/"><strong>PERSONAL SITE</strong></a>
  &nbsp;&nbsp;·&nbsp;&nbsp;
  <a href="https://github.com/{USER}"><strong>GITHUB</strong></a>
</p>

## Live System

This profile is rebuilt automatically from public GitHub activity. The layout keeps a clean, high-contrast, Tesla-inspired feel while the content follows the repositories that changed most recently.

- Public repositories scanned: **{repo_count}**
- Public commits in the last 14 days: **{total_commits}**
- Last generated: **{generated_at}**

<p align="center">
  <img src="assets/commit-activity.svg" alt="Recent public commit activity" width="100%" />
</p>

## Build Direction

```text
Kotlin / Compose Multiplatform / Lets-Plot
Python / PyVISA / PyMeasure
Java / JVisa
GitHub Pages / HTML / CSS / JavaScript
```

## Links

- Website: <https://changhexuefei.github.io/>
- GitHub: <https://github.com/{USER}>
"""
    README.write_text(readme, encoding="utf-8")


def main():
    repos = fetch_repos()
    commits = fetch_commits(repos)
    days = day_series(commits)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    render_hero(repos, days, generated_at)
    render_chart(days)
    render_readme(repos, days)


if __name__ == "__main__":
    main()
