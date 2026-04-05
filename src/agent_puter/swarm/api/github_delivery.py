"""
api/github_delivery.py — Push project deliverables to a GitHub repository.

Uses the GitHub REST API (no git binary required):
  1. Create a new public repository under the authenticated user's account
  2. Upload each file from deliveries/{project_id}/ via the Contents API
  3. Return the repository's HTML URL

The repo is named:  ap-{slugified-project-name}-{short-project-id}
"""
from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Optional

import httpx

from ..models import Project


_GH_API = "https://api.github.com"


def _slugify(text: str) -> str:
    """Convert *text* to a lowercase URL-safe slug, truncated to 50 characters."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50]


async def push_project_to_github(
    access_token: str,
    github_login: str,
    project: Project,
) -> str:
    """Create a GitHub repo and push all files from deliveries/{project.id}/.

    The repository is named ``ap-{slug}-{short_id}`` and initialised as a
    public repo. If the repository already exists the upload step proceeds
    against the existing repo. Each file in the delivery directory is
    created or updated via the GitHub Contents API.

    Args:
        access_token (str): A GitHub OAuth access token with ``repo`` scope.
        github_login (str): The GitHub username that owns the token; used to
            construct repository API paths.
        project (Project): The project whose deliverables are being pushed.
            ``project.id`` determines the delivery directory and the repo name
            suffix; ``project.name`` is slugified for the repo name prefix.

    Returns:
        str: The HTML URL of the created (or pre-existing) GitHub repository.

    Raises:
        httpx.HTTPStatusError: When the repository creation or an API request
            fails with an unrecoverable HTTP error status.
    """
    slug = _slugify(project.name)
    repo_name = f"ap-{slug}-{project.id[:8]}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Create repository (auto_init creates an initial commit / default branch)
        create_resp = await client.post(
            f"{_GH_API}/user/repos",
            headers=headers,
            json={
                "name": repo_name,
                "description": f"Delivered by Agent-Puter — {project.name}",
                "auto_init": True,
                "private": False,
            },
        )
        if create_resp.status_code == 422:
            # Repo already exists — fetch its details
            repo_resp = await client.get(
                f"{_GH_API}/repos/{github_login}/{repo_name}",
                headers=headers,
            )
            repo_resp.raise_for_status()
            repo_html_url: str = repo_resp.json()["html_url"]
        elif create_resp.status_code == 201:
            repo_html_url = create_resp.json()["html_url"]
        else:
            create_resp.raise_for_status()
            repo_html_url = f"https://github.com/{github_login}/{repo_name}"

        # 2. Upload each file from the delivery directory
        delivery_dir = Path("deliveries") / project.id
        if not delivery_dir.exists():
            return repo_html_url

        for file_path in sorted(delivery_dir.rglob("*")):
            if not file_path.is_file():
                continue

            rel = file_path.relative_to(delivery_dir).as_posix()
            encoded = base64.b64encode(file_path.read_bytes()).decode()

            api_path = f"{_GH_API}/repos/{github_login}/{repo_name}/contents/{rel}"

            # Check if file already exists (need its SHA to update)
            existing_sha: Optional[str] = None
            check_resp = await client.get(api_path, headers=headers)
            if check_resp.status_code == 200:
                existing_sha = check_resp.json().get("sha")

            body: dict = {
                "message": f"Update {rel}" if existing_sha else f"Add {rel}",
                "content": encoded,
            }
            if existing_sha:
                body["sha"] = existing_sha

            put_resp = await client.put(api_path, headers=headers, json=body)
            # 200 = updated, 201 = created; anything else is an error
            if put_resp.status_code not in (200, 201):
                print(
                    f"[GitHubDelivery] Warning: failed to push {rel} "
                    f"({put_resp.status_code}): {put_resp.text[:200]}"
                )

    return repo_html_url
