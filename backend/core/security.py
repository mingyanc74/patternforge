import json
import logging
import re

from cryptography.fernet import Fernet
from django.conf import settings


def encrypt_credentials(value):
    return Fernet(settings.CREDENTIAL_KEY.encode()).encrypt(json.dumps(value).encode()).decode()


def decrypt_credentials(ciphertext):
    return json.loads(Fernet(settings.CREDENTIAL_KEY.encode()).decrypt(ciphertext.encode()))


class RedactingFilter(logging.Filter):
    def filter(self, record):
        text = record.getMessage()
        text = re.sub(
            r"(?i)(secret[_ .-]?(?:access[_ .-]?)?key|access[_ .-]?key|session[_ .-]?token|"
            r"authorization|password|api[_ .-]?key)(\s*[:=]\s*)[^\s,;}]+",
            r"\1\2[REDACTED]",
            text,
        )
        text = re.sub(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b", "[REDACTED]", text)
        record.msg, record.args = text, ()
        return True
