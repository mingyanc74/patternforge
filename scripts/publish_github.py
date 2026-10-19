"""Create a private repository using existing Git Credential Manager authorization. Never print tokens."""

import argparse
import json
import os
import subprocess
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", required=True)
    parser.add_argument("--name", default="patternforge")
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}
    result = subprocess.run(
        ["git", "credential", "fill"],
        input=f"protocol=https\nhost=github.com\nusername={args.owner}\n\n",
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode:
        raise SystemExit("GitHub authorization is unavailable. Sign in through Git Credential Manager first.")
    credential = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    token = credential.get("password")
    if not token:
        raise SystemExit("No usable GitHub authorization. No repository was changed.")

    def request(path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            "https://api.github.com" + path,
            data=data,
            headers={
                "Authorization": "Bearer " + token,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "PatternForge-project-setup",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise SystemExit(
                f"GitHub API returned HTTP {exc.code}. Authorization and repository were not exposed."
            ) from None

    user = request("/user")
    if user["login"].lower() != args.owner.lower():
        raise SystemExit("The authorized GitHub identity does not match the requested owner.")
    repo = request(f"/repos/{args.owner}/{args.name}")
    if not args.create:
        print(json.dumps({"authorized_as": user["login"], "repository_exists": repo is not None}))
        return
    if repo:
        raise SystemExit(
            "That repository already exists. Choose a new name; existing repositories are never overwritten."
        )
    repo = request(
        "/user/repos",
        {
            "name": args.name,
            "private": True,
            "auto_init": False,
            "description": "Natural-language S3 data transformations with Django, React, Celery, Redis and PySpark.",
        },
    )
    print(json.dumps({"url": repo["html_url"], "clone_url": repo["clone_url"], "private": repo["private"]}))


if __name__ == "__main__":
    main()
