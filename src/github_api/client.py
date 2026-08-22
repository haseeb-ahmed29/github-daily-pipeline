"""Small, testable GitHub REST API client."""
from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen


class GitHubClient:
    def __init__(self, token: str, username: str | None = None) -> None:
        self.token = token
        self.username = username
        self.base_url = "https://api.github.com"

    def request(self, path: str) -> Any:
        request = Request(self.base_url + path, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-daily-pipeline",
        })
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def repositories(self) -> list[dict[str, Any]]:
        page, repositories = 1, []
        while True:
            batch = self.request(f"/user/repos?per_page=100&page={page}&sort=created")
            repositories.extend(batch)
            if len(batch) < 100:
                return repositories
            page += 1
