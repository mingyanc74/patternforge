"""Read-only, synthetic bucket adapter. This is NOT an Amazon S3 service.

No credentials, user paths, network endpoint, mutable objects or real personal data.
Both the API and worker use this versioned catalog; Spark receives a staged file.
"""

import csv
import hashlib
import io
import re
import zipfile
from datetime import datetime, timezone
from functools import lru_cache

from core.errors import PipelineError

BUCKET = "clearflow-sample-bucket"
REGION = "sample-local"
MODIFIED = datetime(2026, 1, 1, tzinfo=timezone.utc)
VERSION = "sample-v1"
CATALOG = {
    "examples/customers.csv": "1,000 synthetic customers; replace emails, extract order IDs or normalize names.",
    "examples/workbook.xlsx": "Two worksheets: Customers (120 rows) and Orders (80 rows).",
    "examples/large-customers.csv": "50,000 synthetic rows for pagination and longer-running jobs.",
    "edge-cases/empty.csv": "Intentional error: empty file; inspection should be rejected.",
    "edge-cases/duplicate-headers.csv": "Intentional error: duplicate column names.",
    "edge-cases/unsupported.txt": "Intentional unsupported format; cannot be selected.",
}


def customer_rows(count):
    yield ["ID", "Name", "Email", "Notes", "City"]
    names = ["  ALICE   SMITH  ", "  陈   小雨  ", "Bob, Taylor", "Two\nLines"]
    for number in range(1, count + 1):
        email = (
            "\\N"
            if number % 10 == 0
            else "not-an-email"
            if number % 10 == 1
            else f"person{number}@example.com"
        )
        yield [
            f"{number:06}",
            names[(number - 1) % 4],
            email,
            f"Order ORD-{100000 + number}; synthetic test record",
            "\\N" if number % 7 == 0 else "  MELBOURNE  ",
        ]


@lru_cache(maxsize=8)
def object_bytes(key):
    if key not in CATALOG:
        raise PipelineError("SAMPLE_NOT_FOUND", "This file is not in the read-only sample bucket.")
    if key.endswith("customers.csv"):
        stream = io.StringIO(newline="")
        csv.writer(stream, lineterminator="\n").writerows(customer_rows(50000 if "large-" in key else 1000))
        return stream.getvalue().encode("utf-8")
    if key.endswith("workbook.xlsx"):
        from openpyxl import Workbook

        book = Workbook()
        customers = book.active
        customers.title = "Customers"
        for row in customer_rows(120):
            customers.append([None if value == "\\N" else value for value in row])
        orders = book.create_sheet("Orders")
        orders.append(["ID", "Description", "Status"])
        for number in range(1, 81):
            orders.append([f"{number:06}", f"Order ORD-{200000 + number}", "  PENDING   REVIEW  "])
        raw = io.BytesIO()
        book.save(raw)
        book.close()
        # openpyxl writes current ZIP/core-property times: normalize them so
        # fingerprints match across web workers, Spark jobs and server restarts.
        stable = io.BytesIO()
        with zipfile.ZipFile(raw) as source, zipfile.ZipFile(stable, "w", zipfile.ZIP_DEFLATED) as target:
            for name in sorted(source.namelist()):
                body = source.read(name)
                if name == "docProps/core.xml":
                    body = re.sub(
                        rb"(<dcterms:(?:created|modified)[^>]*>).*?(</dcterms:(?:created|modified)>)",
                        rb"\g<1>2026-01-01T00:00:00Z\g<2>",
                        body,
                    )
                info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                target.writestr(info, body)
        return stable.getvalue()
    if key.endswith("empty.csv"):
        return b""
    if key.endswith("duplicate-headers.csv"):
        return b"ID,Email,Email\n001,a@example.com,b@example.com\n"
    return b"Synthetic sample bucket. Not Amazon S3. Original files are read-only.\n"


class SampleBucket:
    """Only implements the read operations needed by the application."""

    @staticmethod
    def _bucket(bucket):
        if bucket != BUCKET:
            raise PipelineError("SAMPLE_NOT_FOUND", "Unknown sample bucket.")

    def head_object(self, Bucket, Key):
        self._bucket(Bucket)
        body = object_bytes(Key)
        return {
            "ContentLength": len(body),
            "ETag": '"' + hashlib.sha256(body).hexdigest() + '"',
            "LastModified": MODIFIED,
            "VersionId": VERSION,
        }

    def list_objects_v2(self, Bucket, Prefix="", MaxKeys=100, ContinuationToken=None):
        self._bucket(Bucket)
        keys = sorted(key for key in CATALOG if key.startswith(Prefix))
        try:
            start = int(ContinuationToken or "0")
            if start < 0 or start > len(keys):
                raise ValueError
        except (ValueError, TypeError):
            raise PipelineError("INVALID_CURSOR", "Refresh the sample file list.") from None
        page = keys[start : start + MaxKeys]
        result = {
            "Contents": [
                {"Key": key, "Size": len(object_bytes(key)), "LastModified": MODIFIED} for key in page
            ]
        }
        if start + len(page) < len(keys):
            result["NextContinuationToken"] = str(start + len(page))
        return result
