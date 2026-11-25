import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from string import punctuation
from urllib.parse import urlencode
from urllib.request import Request, urlopen


USERNAME = "juanangelaalma"
QUERY = f"is:pr is:merged is:public author:{USERNAME} -user:{USERNAME}"
START = "<!-- recent-contributions:start -->"
END = "<!-- recent-contributions:end -->"
README = Path(__file__).resolve().parents[2] / "README.md"


def recent_merges():
    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=90)).isoformat()
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"{USERNAME}-profile"}
    if token := os.environ.get("GH_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"

    results = []
    page = 1
    while True:
        params = urlencode({
            "q": f"{QUERY} merged:>={cutoff}",
            "sort": "created",
            "order": "desc",
            "per_page": 100,
            "page": page,
        })
        request = Request(f"https://api.github.com/search/issues?{params}", headers=headers)
        with urlopen(request, timeout=30) as response:
            data = json.load(response)
            has_next = 'rel="next"' in response.headers.get("Link", "")
        if data["incomplete_results"] or data["total_count"] > 1000:
            raise RuntimeError("Search results are incomplete; keeping the existing README.")
        results.extend(data["items"])
        if not has_next:
            break
        page += 1

    return sorted(
        results, key=lambda pr: (pr["pull_request"]["merged_at"], pr["html_url"]), reverse=True
    )[:5]


def markdown_text(text):
    return "".join(f"&#{ord(char)};" if char in punctuation else char
                   for char in " ".join(text.split()))


def render_section(pull_requests):
    if pull_requests:
        lines = ["| Project | Pull request | Merged (UTC) |", "| --- | --- | --- |"]
        for pr in pull_requests:
            owner, repo = pr["repository_url"].rsplit("/", 2)[-2:]
            date = pr["pull_request"]["merged_at"][:10]
            lines.append(
                f"| {markdown_text(f'{owner}/{repo}')} "
                f"| [{markdown_text(pr['title'])}]({pr['html_url']}) | {date} |"
            )
    else:
        lines = ["No public pull requests to other accounts were merged in the last 90 days."]

    search_url = "https://github.com/pulls?" + urlencode({"q": QUERY})
    return "\n".join(lines + ["", f"[All merged public pull requests]({search_url})"])


def main():
    readme = README.read_text(encoding="utf-8")
    if readme.count(START) != 1 or readme.count(END) != 1 or readme.index(START) > readme.index(END):
        raise ValueError("README must contain exactly one ordered pair of contribution markers.")

    start = readme.index(START) + len(START)
    end = readme.index(END)
    print(readme[:start] + "\n\n" + render_section(recent_merges()) + "\n\n" + readme[end:], end="")


if __name__ == "__main__":
    main()
