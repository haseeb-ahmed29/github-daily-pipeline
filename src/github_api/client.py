"""Small, testable GitHub REST client."""
from __future__ import annotations

import base64
import json
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class GitHubClient:
    def __init__(self, token: str, username: str | None = None) -> None:
        self.token = token
        self.username = username
        self.base_url = "https://api.github.com"

    def request(self, path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=body,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "github-daily-pipeline",
                "Content-Type": "application/json",
            },
        )
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

    def readme(self, full_name: str, branch: str) -> dict[str, Any] | None:
        try:
            return self.request(f"/repos/{full_name}/contents/README.md?ref={branch}")
        except HTTPError as error:
            if error.code == 404:
                return None
            raise

    def update_readme(self, full_name: str, branch: str, content: str, message: str, sha: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        return self.request(f"/repos/{full_name}/contents/README.md", method="PUT", payload=payload)
