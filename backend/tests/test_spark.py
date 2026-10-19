import os
import sys

import pytest

pytestmark = pytest.mark.spark


@pytest.fixture(scope="module")
def spark():
    from pathlib import Path

    import pyspark

    os.environ["SPARK_HOME"] = str(Path(pyspark.__file__).parent)
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
    if os.name == "nt":
        import subprocess

        import pyspark.java_gateway as gateway
        from spark_engine.launcher import windows_submit

        original = gateway.Popen
        gateway.Popen = lambda command, **kwargs: subprocess.Popen(windows_submit(command[1:]), **kwargs)
    from pyspark.sql import SparkSession

    session = (
        SparkSession.builder.master("local[2]")
        .appName("patternforge-tests")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()
    if os.name == "nt":
        gateway.Popen = original


def sample(spark):
    # Built in the JVM: these tests exercise Spark expressions, not Python row-by-row processing.
    return spark.sql("""SELECT * FROM VALUES
        ('001', '  ALICE   SMITH  ', 'a@example.com and b@example.org', 'Order ORD-123 shipped'),
        ('002', 'Bob', 'not-an-email', 'No order'),
        ('003', CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING)),
        ('004', '', '', 'ORD-999 then ORD-888') AS data(ID, Name, Email, Description)""")


def test_replace_all_matches_preserve_null_and_literal_dollars(spark, email_plan):
    from spark_engine.transformations import statistics, transform

    df = sample(spark)
    config = {"target_columns": ["Email"], "replacement": "$1\\safe"}
    rows = {row.ID: row.asDict() for row in transform(df, email_plan, config).collect()}
    assert rows["001"]["Email"] == "$1\\safe and $1\\safe"
    assert rows["001"]["Name"] == "  ALICE   SMITH  "
    assert rows["002"]["Email"] == "not-an-email"
    assert rows["003"]["Email"] is None and rows["004"]["Email"] == ""
    stats = statistics(df, email_plan, config)
    assert stats["row_count"] == 4 and stats["changed_cells"]["Email"] == 1


def test_extract_first_match_and_preserve_original(spark):
    from spark_engine.transformations import transform

    plan = {
        "operation": "regex_extract",
        "pattern": r"ORD-\d+",
        "group": 0,
        "steps": [],
        "explanation": "Order IDs",
    }
    rows = {
        r.ID: r.asDict()
        for r in transform(
            sample(spark), plan, {"target_columns": ["Description"], "new_column": "order_id"}
        ).collect()
    }
    assert rows["001"]["order_id"] == "ORD-123"
    assert rows["002"]["order_id"] is None and rows["003"]["order_id"] is None
    assert rows["004"]["order_id"] == "ORD-999"
    assert rows["001"]["Description"] == "Order ORD-123 shipped"


def test_normalization_and_special_column_names(spark):
    from spark_engine.transformations import transform

    df = sample(spark).withColumnRenamed("Name", "用户.name`text")
    plan = {
        "operation": "normalize",
        "pattern": None,
        "group": 0,
        "steps": ["trim", "collapse_whitespace", "lowercase"],
        "explanation": "Clean names",
    }
    rows = {r.ID: r.asDict() for r in transform(df, plan, {"target_columns": ["用户.name`text"]}).collect()}
    assert rows["001"]["用户.name`text"] == "alice smith"
    assert rows["003"]["用户.name`text"] is None


def test_partitioning_does_not_change_values(spark, email_plan):
    from spark_engine.transformations import transform

    config = {"target_columns": ["Email"], "replacement": "REDACTED"}
    df = sample(spark)
    one = sorted(transform(df.repartition(1), email_plan, config).collect(), key=lambda r: r.ID)
    many = sorted(transform(df.repartition(4), email_plan, config).collect(), key=lambda r: r.ID)
    assert one == many


def test_empty_replacement_removes_matching_portions(spark, email_plan):
    from spark_engine.transformations import transform

    row = transform(
        sample(spark).filter("ID = '001'"), email_plan, {"target_columns": ["Email"], "replacement": ""}
    ).first()
    assert row.Email == " and "
