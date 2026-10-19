FROM python:3.11-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    SPARK_HOME=/usr/local/lib/python3.11/site-packages/pyspark \
    PYSPARK_PYTHON=/usr/local/bin/python PYSPARK_DRIVER_PYTHON=/usr/local/bin/python
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-17-jdk-headless curl procps \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements*.txt ./
RUN pip install --no-cache-dir -r requirements-spark.txt
# Spark 3.5.x bundles Hadoop 3.3.4. Keep S3A and AWS SDK versions in sync with it.
RUN curl -fsSL --retry 3 https://repo.maven.apache.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar \
      -o "$SPARK_HOME/jars/hadoop-aws-3.3.4.jar" \
    && curl -fsSL --retry 3 https://repo.maven.apache.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar \
      -o "$SPARK_HOME/jars/aws-java-sdk-bundle-1.12.262.jar"
RUN groupadd --gid 10001 patternforge && useradd --uid 10001 --gid 10001 --create-home patternforge \
    && mkdir -p /data && chown patternforge:patternforge /data
COPY --chown=10001:10001 backend/ /app/
ENV PATH="/usr/local/lib/python3.11/site-packages/pyspark/bin:${PATH}"
USER 10001:10001
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--access-logfile", "-"]

FROM runtime AS test
USER root
RUN pip install --no-cache-dir -r requirements-dev.txt
USER 10001:10001
