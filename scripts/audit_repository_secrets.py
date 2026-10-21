"""Bounded local secret audit; reports locations, never secret values.

Private JSON files supply exact values only in memory. Nothing is sent to a
third-party scanner. Historical Git blobs are inspected once, including remotes.
"""

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def git(*args):
    return subprocess.check_output(["git", *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-json", type=Path, action="append", default=[])
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    known = []
    for source in args.private_json:
        values = json.loads(source.read_text(encoding="utf-8"))
        for name in ("access_key", "secret_key", "session_token", "website_access_password"):
            if values.get(name):
                known.append((name, values[name].encode()))
    patterns = {
        "AWS access-key-shaped token": rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
        "GitHub token-shaped value": rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})",
        "OpenAI token-shaped value": rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}",
        "PEM private key": rb"(?m)^-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----",
    }
    findings = []

    def inspect(data, location):
        for name, value in known:
            if value in data:
                findings.append({"location": location, "kind": "exact private " + name})
        for name, pattern in patterns.items():
            if re.search(pattern, data):
                findings.append({"location": location, "kind": name})

    files = git("ls-files", "-z", "--cached", "--others", "--exclude-standard").split(b"\0")
    count = 0
    for raw in files:
        if not raw:
            continue
        path = Path(raw.decode("utf-8"))
        if path.is_file():
            inspect(path.read_bytes(), "working-tree:" + path.as_posix())
            count += 1
    objects = git("rev-list", "--objects", "--all").decode().splitlines()
    proc = subprocess.Popen(["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    blobs = 0
    for entry in objects:
        oid, _, path = entry.partition(" ")
        proc.stdin.write((oid + "\n").encode())
        proc.stdin.flush()
        header = proc.stdout.readline().decode().split()
        size = int(header[2])
        data = proc.stdout.read(size)
        proc.stdout.read(1)
        if header[1] == "blob":
            inspect(data, "git:" + oid + ":" + path)
            blobs += 1
    proc.stdin.close()
    proc.wait()
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "head": git("rev-parse", "HEAD").decode().strip(),
        "commits_checked": int(git("rev-list", "--count", "--all")),
        "historical_blobs_checked": blobs,
        "working_files_checked": count,
        "exact_private_values_checked": len(known),
        "candidate_findings": findings,
        "passed": not findings,
        "scope": "All reachable local/remote refs after fetch and unignored working files; exact provided secrets plus bounded token patterns. Not a guarantee of absence of every possible secret.",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
