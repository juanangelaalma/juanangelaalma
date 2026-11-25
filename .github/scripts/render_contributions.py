import json
import os
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen


USERNAME = "juanangelaalma"
QUERY = f"is:pr is:merged is:public author:{USERNAME} -user:{USERNAME}"
WEEKS = 13


def weekly_counts(first_week):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"{USERNAME}-profile"}
    if token := os.environ.get("GH_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"

    counts = [0] * WEEKS
    page = 1
    while True:
        params = urlencode({
            "q": f"{QUERY} merged:>={first_week.isoformat()}",
            "per_page": 100,
            "page": page,
        })
        request = Request(f"https://api.github.com/search/issues?{params}", headers=headers)
        with urlopen(request, timeout=30) as response:
            data = json.load(response)
            has_next = 'rel="next"' in response.headers.get("Link", "")
        if data["incomplete_results"] or data["total_count"] > 1000:
            raise RuntimeError("Search results are incomplete; keeping the existing chart.")
        for pr in data["items"]:
            merged = date.fromisoformat(pr["pull_request"]["merged_at"][:10])
            week = (merged - first_week).days // 7
            if 0 <= week < WEEKS:
                counts[week] += 1
        if not has_next:
            break
        page += 1

    return counts


def render_chart(first_week, counts):
    baseline = 190
    peak = max(1, max(counts))
    dates = [first_week + timedelta(weeks=i) for i in range(WEEKS)]
    description = "; ".join(f"{week.isoformat()}: {count}" for week, count in zip(dates, counts))
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="240" viewBox="0 0 720 240" role="img" aria-labelledby="title desc">',
        '  <title id="title">Merged public pull requests per week</title>',
        f'  <desc id="desc">Weeks start Monday (UTC). {description}.</desc>',
        '  <rect x=".5" y=".5" width="719" height="239" rx="14" fill="#0d1918" stroke="#365450"/>',
        '  <g font-family="system-ui, sans-serif">',
        '    <text x="30" y="41" font-size="26" font-weight="650" fill="#f0faf5">Merged PRs per week</text>',
        f'    <text x="690" y="41" text-anchor="end" font-size="21" fill="#b1e6d3">{sum(counts)} total</text>',
        f'    <path d="M30 {baseline}H690" stroke="#58716d"/>',
    ]
    if not sum(counts):
        lines.append('    <text x="360" y="132" text-anchor="middle" font-size="24" fill="#c2d6d1">No merged PRs this period</text>')
    for i, (week, count) in enumerate(zip(dates, counts)):
        x = 60 + 50 * i
        if count:
            height = max(2, round(103 * count / peak))
            lines.extend([
                f'    <rect x="{x - 15}" y="{baseline - height}" width="30" height="{height}" rx="2" fill="#71d6b4"/>',
                f'    <text x="{x}" y="{baseline - height - 7}" text-anchor="middle" font-size="23" fill="#f0faf5">{count}</text>',
            ])
        if i % 3 == 0:
            lines.append(f'    <text x="{x}" y="222" text-anchor="middle" font-size="22" fill="#c2d6d1">{week:%d %b}</text>')
    return "\n".join(lines + ["  </g>", "</svg>"])


def main():
    today = datetime.now(timezone.utc).date()
    first_week = today - timedelta(days=today.weekday(), weeks=WEEKS - 1)
    print(render_chart(first_week, weekly_counts(first_week)))


if __name__ == "__main__":
    main()
