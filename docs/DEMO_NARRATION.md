# Rulecraft — expanded first-person narration reference

Historical expanded script for the [silent video](demo/Rulecraft-Real-AWS-Demo-Silent.mp4), recorded 2026-10-22 Sydney, 1280×720, approximately 05:18. All operations used the public Azure application and genuine Amazon S3 objects containing fictional test contacts, not personal data.

**The delivered owner's voiceover follows the [concise functional script](DEMO_NARRATION_SIMPLE.md), not this longer alternative.** The original expanded English passages below are retained for reference. Import the video into an editor such as CapCut and add your own voice track, leaving pauses where useful. An approximate 110–125 words/minute was suggested for the expanded version, but no constant speech is necessary. Do not read passwords, keys or private configuration. No voice imitation/generated voice is used.

## Timeline and expanded script

### 00:00–00:11 · Website gate

This is Rulecraft, my natural-language workspace for transforming cloud data. I enter the website password privately, with recording paused.

### 00:11–00:29 · Genuine S3 authorization

Website access and AWS access are separate. Here I enter my bucket name and Sydney region. I also enter a genuine read-only AWS Access Key and Secret Key, with recording paused to protect them.

### 00:29–00:38 · File listing

These CSV and Excel files really exist in my private Amazon S3 bucket. I select the CSV.

### 00:38–01:05 · Asynchronous import

Preview starts an asynchronous import. The backend downloads the authorized object and Spark creates an independent dataset snapshot. Django handles the API, Celery runs the heavy work, and Redis supports the queue. Only a bounded preview is sent to the browser; the source object is not overwritten.

### 01:05–01:18 · Natural-language configuration

I select Email, describe the pattern in ordinary language, and enter a literal replacement. I review the source, target column and instruction before submitting.

### 01:18–02:05 · Genuine model and Spark

Submission creates a persistent job rather than blocking the web request. The genuine language model generates a structured plan. The backend validates the rule before Spark processes the snapshot across partitions. The stage and estimated progress are visible here. These three demonstration tasks were later checked against the database: all used real Amazon S3 imports, uncached model inference, two Spark executors and eight partitions. Progress is stage-based, not a precise row counter.

### 02:05–02:16 · Replacement and pages

One thousand rows are ready, with eight hundred email replacements. I open page two; results are fetched in bounded pages.

### 02:16–02:54 · Excel import

Next I select the real Excel object from the same S3 bucket. The workbook is imported through the asynchronous pipeline too. This workbook uses the TestData worksheet. Both formats produce retained snapshots, so later transformations do not need to download the source again. These are real files containing deliberately synthetic test records, including missing and invalid values.

### 02:54–03:03 · Extraction rule

I choose Notes and describe the order ID format: ORD, a hyphen, then digits. The new column is OrderID.

### 03:03–03:49 · Extraction execution

Extraction uses the same model, Celery and Spark path. The custom ID format is in my instruction because private source rows are not sent to the model. The original Notes column is kept, and a non-matching value produces null in the new column. Identical validated instructions can reuse the Redis plan cache; this recorded instruction was an actual uncached model request.

### 03:49–03:55 · Extraction result

Nine hundred rows have an extracted order ID. The remaining rows have no matching reference.

### 03:55–04:13 · Multi-column normalization

Finally, I reuse the imported Excel snapshot. I select Name and Status, then request trimming, repeated-space cleanup and lowercase conversion. This is the third supported transformation.

### 04:13–04:52 · Normalization execution

The model selects approved normalization operations, not arbitrary executable code. The task again runs asynchronously. Original S3 files remain unchanged. Connections normally expire after one hour; imported snapshots and results have their own twenty-four-hour retention. Previous acceptance checked processing after connection expiry. That is separate evidence, not a claim that this short video observes a full day.

### 04:52–04:58 · Normalized result

The result contains one thousand rows and two thousand updated cells across the two selected columns.

### 04:58–05:04 · Retained imports

Imported datasets show their real source and individual retention deadline, independently of the connection.

### 05:04–05:11 · History

Job history preserves the status, duration and result links, so I can return to completed work.

### 05:11–05:18 · Closing

The service is ready. My README documents the architecture, setup, real-service results and separate development evidence.

## Recording boundaries

- UI Duration starts in execution; database creation-to-finish also includes queue/other overhead. Do not interchange them.
- This is an encoded sequence of actual browser captures, approximately one capture per 0.5 seconds, output at 20 fps with repeated frames. Processing waits were not accelerated; preparation intervals between chapters were removed. It is not native 20-fps desktop capture and the cursor may be absent.
- The video demonstrates 1,000 rows. Actual larger-AWS testing reached 50,000; 3,000,000 rows used development fixtures, not real AWS.
- Two Spark worker/executor containers share one Azure host, not two independent machines.
- The silent version is preserved. The subsequent owner-recorded English audio changes no processing facts or video timing. Keep all active credentials and the website password out of the deliverable.
