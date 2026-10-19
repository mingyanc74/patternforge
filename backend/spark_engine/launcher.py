"""Use Spark's normal launcher on Linux; avoid cmd code-page corruption on Windows."""

import os
import shutil
from pathlib import Path


def windows_submit(arguments, memory="1g"):
    import pyspark

    spark_home = Path(pyspark.__file__).parent
    java = (
        str(Path(os.environ["JAVA_HOME"]) / "bin" / "java.exe")
        if os.getenv("JAVA_HOME")
        else shutil.which("java")
    )
    modules = [
        "java.base/java.lang",
        "java.base/java.lang.invoke",
        "java.base/java.lang.reflect",
        "java.base/java.io",
        "java.base/java.net",
        "java.base/java.nio",
        "java.base/java.util",
        "java.base/java.util.concurrent",
        "java.base/java.util.concurrent.atomic",
        "java.base/sun.nio.ch",
        "java.base/sun.nio.cs",
        "java.base/sun.security.action",
        "java.base/sun.util.calendar",
        "java.security.jgss/sun.security.krb5",
    ]
    return [
        java,
        "-Xmx" + memory,
        "-Dio.netty.tryReflectionSetAccessible=true",
        *["--add-opens=" + module + "=ALL-UNNAMED" for module in modules],
        "-cp",
        str(spark_home / "jars" / "*"),
        "org.apache.spark.deploy.SparkSubmit",
        *arguments,
    ]
