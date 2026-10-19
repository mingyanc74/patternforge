"""Pure Spark expressions. No driver-side row transformation or per-row model calls."""

from pyspark.sql import functions as F


def column(name):
    return F.col("`" + name.replace("`", "``") + "`")


def literal_replacement(text):
    return text.replace("\\", "\\\\").replace("$", "\\$")


def expressions(df, plan, config):
    changes = {}
    for name in config["target_columns"]:
        value = column(name)
        if plan["operation"] == "regex_replace":
            updated = F.regexp_replace(value, plan["pattern"], literal_replacement(config["replacement"]))
            changes[name] = (value, updated)
        elif plan["operation"] == "regex_extract":
            extracted = F.regexp_extract(value, plan["pattern"], plan["group"])
            updated = F.when(extracted != "", extracted).otherwise(F.lit(None).cast("string"))
            changes[config["new_column"]] = (F.lit(None).cast("string"), updated)
        else:
            updated = value
            for step in plan["steps"]:
                if step == "trim":
                    updated = F.regexp_replace(updated, r"(?U)^\s+|\s+$", "")
                elif step == "collapse_whitespace":
                    updated = F.regexp_replace(updated, r"(?U)\s+", " ")
                elif step == "lowercase":
                    updated = F.lower(updated)
                elif step == "uppercase":
                    updated = F.upper(updated)
                else:
                    raise ValueError("Unsupported normalization step")
            changes[name] = (value, updated)
    return changes


def transform(df, plan, config):
    changes = expressions(df, plan, config)
    return df.select(
        *[changes[name][1].alias(name) if name in changes else column(name) for name in df.columns],
        *[value[1].alias(name) for name, value in changes.items() if name not in df.columns],
    )


def statistics(df, plan, config):
    changes = expressions(df, plan, config)
    summary = df.agg(
        F.count(F.lit(1)).alias("__rows"),
        *[
            F.sum(F.when(~old.eqNullSafe(new), 1).otherwise(0)).alias("__change_" + str(i))
            for i, (_, (old, new)) in enumerate(changes.items())
        ],
    ).first()
    return {
        "row_count": summary["__rows"],
        "changed_cells": {name: int(summary["__change_" + str(i)] or 0) for i, name in enumerate(changes)},
        "count_kind": "changed_cells",
    }
