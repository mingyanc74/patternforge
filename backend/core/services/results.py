import json
from pathlib import Path

import pyarrow.parquet as pq
from django.conf import settings
from django.core import signing

from core.errors import AppError

CURSOR_SALT = "patternforge-result-page-v1"


def contained_path(path, root=None):
    root = Path(root or settings.DATA_DIR).resolve()
    path = Path(path).resolve()
    if not path.is_relative_to(root):
        raise AppError("INVALID_RESULT", "The result path is invalid.", 400)
    return path


def build_manifest(work, metadata, version):
    entries, offset = [], 0
    for file in sorted((work / "parquet").glob("part-*.parquet")):
        info = pq.ParquetFile(file).metadata
        for group in range(info.num_row_groups):
            count = info.row_group(group).num_rows
            if count:
                entries.append({"file": file.name, "group": group, "start": offset, "rows": count})
                offset += count
    if offset != metadata["row_count"]:
        raise AppError("RESULT_INCOMPLETE", "The result row count did not match.", 500)
    manifest = {
        "version": str(version),
        "columns": metadata["columns"],
        "row_count": offset,
        "groups": entries,
    }
    path = work / "manifest.json"
    temporary = work / "manifest.tmp"
    temporary.write_text(json.dumps(manifest), encoding="utf-8")
    temporary.replace(path)
    return path


def read_page(job, cursor, limit):
    path = contained_path(job.manifest)
    if not path.is_file():
        raise AppError("RESULT_UNAVAILABLE", "The saved result is no longer available.", 410)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    offset = 0
    if cursor:
        try:
            token = signing.loads(cursor, salt=CURSOR_SALT, max_age=86400)
            if (
                token["job"] != str(job.id)
                or token["owner"] != job.owner
                or token["version"] != manifest["version"]
            ):
                raise ValueError
            offset = token["offset"]
            if (
                isinstance(offset, bool)
                or not isinstance(offset, int)
                or not 0 <= offset <= manifest["row_count"]
            ):
                raise ValueError
        except (signing.BadSignature, ValueError, KeyError, TypeError):
            raise AppError(
                "INVALID_CURSOR", "The page link is invalid or expired. Return to the first page."
            ) from None
    rows, byte_count, full = [], 0, False
    for entry in manifest["groups"]:
        if offset >= entry["start"] + entry["rows"]:
            continue
        file = contained_path(path.parent / "parquet" / entry["file"], path.parent)
        local_skip = max(0, offset - entry["start"])
        for batch in pq.ParquetFile(file).iter_batches(
            batch_size=min(limit, 32), row_groups=[entry["group"]]
        ):
            for row in batch.to_pylist():
                if local_skip:
                    local_skip -= 1
                    continue
                size = len(json.dumps(row, ensure_ascii=False, default=str).encode())
                if rows and byte_count + size > 2 * 1024**2:
                    full = True
                    break
                rows.append(row)
                byte_count += size
                if len(rows) >= limit:
                    break
            if len(rows) >= limit or full:
                break
        if len(rows) >= limit or full:
            break
    end = offset + len(rows)
    next_cursor = None
    if end < manifest["row_count"]:
        next_cursor = signing.dumps(
            {"job": str(job.id), "owner": job.owner, "version": manifest["version"], "offset": end},
            salt=CURSOR_SALT,
            compress=True,
        )
    return {
        "rows": rows,
        "columns": manifest["columns"],
        "total_rows": manifest["row_count"],
        "offset": offset,
        "returned_rows": len(rows),
        "next_cursor": next_cursor,
        "version": manifest["version"],
    }
