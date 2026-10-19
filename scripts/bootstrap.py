"""Create development secrets without printing them; never overwrite existing configuration."""

import base64
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    print("Existing .env preserved.")
else:
    text = (root / ".env.example").read_text(encoding="utf-8")
    text = text.replace("DJANGO_SECRET_KEY=\n", "DJANGO_SECRET_KEY=" + secrets.token_urlsafe(48) + "\n")
    text = text.replace(
        "CREDENTIAL_KEY=\n",
        "CREDENTIAL_KEY=" + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode() + "\n",
    )
    text = text.replace("POSTGRES_PASSWORD=patternforge", "POSTGRES_PASSWORD=" + secrets.token_urlsafe(24))
    text = text.replace(
        "postgresql://patternforge:patternforge@db",
        "postgresql://patternforge:" + text.split("POSTGRES_PASSWORD=")[1].splitlines()[0] + "@db",
    )
    text = text.replace("admin:change-this-before-deploy", "admin:" + secrets.token_urlsafe(24))
    target.write_text(text, encoding="utf-8")
    print("Created .env with random application, encryption, database and monitor secrets.")
print("Next: configure LLM_API_KEY and LLM_MODEL in .env, then run docker compose up --build.")
