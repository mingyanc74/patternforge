import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.spark


def run_driver(work, source, kind="inspect", config=None, plan=None):
    work.mkdir()
    spec = {
        "job_id": str(uuid.uuid4()),
        "kind": kind,
        "source_key": source.name,
        "config": config or {"delimiter": ",", "encoding": "UTF-8"},
        "plan": plan,
        "local_source": str(source),
        "partitions": 2,
        "max_excel_bytes": 100 * 1024**2,
        "max_excel_rows": 10000,
        "max_cell_chars": 65536,
    }
    spec_path = work / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    arguments = [
        "--master",
        "local[2]",
        str(Path(__file__).parents[1] / "spark_engine" / "run_job.py"),
        str(spec_path),
    ]
    env = {
        **os.environ,
        "PYSPARK_PYTHON": sys.executable,
        "PYSPARK_DRIVER_PYTHON": sys.executable,
        "SPARK_LOCAL_IP": "127.0.0.1",
    }
    if os.name == "nt":
        from spark_engine.launcher import windows_submit

        command = windows_submit(arguments)
    else:
        import pyspark

        command = [str(Path(pyspark.__file__).parent / "bin" / "spark-submit"), *arguments]
    result = subprocess.run(
        command, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90
    )
    if result.returncode:
        failure = (
            (work / "failure.json").read_text() if (work / "failure.json").exists() else result.stderr[-3000:]
        )
        pytest.fail(failure)
    return json.loads((work / "output.json").read_text(encoding="utf-8"))


def test_csv_driver_preserves_zeroes_quotes_and_multiline(tmp_path):
    source = tmp_path / "input.csv"
    source.write_text(
        'ID,Name,Email\n001,"Alice, Smith",a@example.com\n002,"Two\nLines",\\N\n', encoding="utf-8"
    )
    result = run_driver(tmp_path / "csv-inspect", source)
    assert result["preview"][0]["ID"] == "001"
    assert result["preview"][0]["Name"] == "Alice, Smith"
    assert result["preview"][1]["Name"] == "Two\nLines" and result["preview"][1]["Email"] is None


def test_excel_lists_sheets_and_streams_selected_sheet_into_spark(tmp_path):
    from openpyxl import Workbook

    source = tmp_path / "input.xlsx"
    book = Workbook()
    first = book.active
    first.title = "Customers"
    first.append(["ID", "Name"])
    first.append(["001", "Alice"])
    second = book.create_sheet("Orders")
    second.append(["Order"])
    second.append(["ORD-123"])
    book.save(source)
    result = run_driver(tmp_path / "excel-sheets", source)
    assert result["requires_sheet"] and result["sheets"] == ["Customers", "Orders"]
    selected = run_driver(tmp_path / "excel-inspect", source, config={"sheet": "Customers"})
    assert selected["preview"] == [{"ID": "001", "Name": "Alice"}]


@pytest.mark.skipif(
    os.name == "nt", reason="Native Hadoop Windows DLLs are not bundled; Linux Docker/CI runs this test."
)
def test_full_driver_writes_parquet(tmp_path, email_plan):
    import pyarrow.parquet as pq

    source = tmp_path / "input.csv"
    source.write_text("ID,Email\n001,a@example.com\n002,no-match\n", encoding="utf-8")
    work = tmp_path / "transform"
    result = run_driver(
        work,
        source,
        kind="transform",
        plan=email_plan,
        config={"operation": "regex_replace", "target_columns": ["Email"], "replacement": "REDACTED"},
    )
    assert result["row_count"] == 2 and result["changed_cells"] == {"Email": 1}
    rows = pq.ParquetDataset(work / "parquet").read().to_pylist()
    assert sorted(rows, key=lambda r: r["ID"]) == [
        {"ID": "001", "Email": "REDACTED"},
        {"ID": "002", "Email": "no-match"},
    ]
