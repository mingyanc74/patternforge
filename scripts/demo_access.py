"""Create a local website entrance secret and a hash-only deployment file. Never prints secrets."""

import argparse
import base64
import hashlib
import json
import secrets
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-file", type=Path, required=True)
    parser.add_argument("--hash-file", type=Path, required=True)
    args = parser.parse_args()
    if args.private_file.exists() or args.hash_file.exists():
        parser.error("Refusing to overwrite an existing access secret.")
    password, salt = secrets.token_urlsafe(18), secrets.token_urlsafe(12)
    rounds = 1000000
    digest = base64.b64encode(
        hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), rounds)
    ).decode()
    encoded = base64.b64encode(f"pbkdf2_sha256${rounds}${salt}${digest}".encode()).decode()
    args.private_file.parent.mkdir(parents=True, exist_ok=True)
    args.private_file.write_text(
        json.dumps(
            {
                "website": "https://clearflow-patternforge.australiaeast.cloudapp.azure.com/",
                "website_access_password": password,
                "note": "Website entrance only; NOT an AWS secret. Do not commit or share publicly.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    args.hash_file.write_text(encoded + "\n", encoding="ascii")
    args.private_file.chmod(0o600)
    args.hash_file.chmod(0o600)
    print("Created local access-password file and hash-only deployment file; secret values withheld.")


if __name__ == "__main__":
    main()
