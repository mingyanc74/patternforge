# Rulecraft — concise demonstration narration

For the existing 05:18 video. Read each passage when its corresponding scene begins, at a natural pace, then pause. No continuous narration is needed while jobs run. The final video uses the owner's recorded English voice; this is the concise functional script, not an architecture presentation.

## 00:00–00:11 · Introduction

This is Rulecraft. It helps users clean and transform CSV and Excel data using plain English.

## 00:11–00:38 · Connect S3

First, I connect my Amazon S3 bucket using my AWS credentials. I've hidden the keys for security. The available files appear here.

## 00:38–01:18 · Select CSV and configure replacement

I'll start with the CSV file. After previewing the data, I select Email and ask the app to find email addresses. I'll replace them with “REDACTED,” then review and run the job.

## 01:18–02:05 · Processing

The job runs in the background, and I can follow its progress here.

Pause after this line; leave the actual progress visible.

## 02:05–02:16 · Results and pagination

The job is complete: one thousand rows processed and eight hundred email replacements. I can browse the results page by page.

## 02:16–03:03 · Excel and extraction

The app also supports Excel. I select the workbook and preview its data. This time, I'll extract order IDs from Notes into a new column called OrderID.

## 03:03–03:49 · Extraction in progress

No narration required; retain the actual progress sequence.

## 03:49–03:55 · Extracted result

The new column contains nine hundred extracted order IDs.

## 03:55–04:13 · Multi-column normalization

Finally, I'll clean Name and Status together: remove extra spaces and convert the text to lowercase.

## 04:13–04:52 · Normalization in progress

No narration required; retain the actual progress sequence.

## 04:52–04:58 · Normalized result

Both columns are cleaned, with two thousand cells updated.

## 04:58–05:18 · History and closing

I can reuse imported datasets and return to completed jobs from the history. The original S3 files stay unchanged. Thanks for watching.

---

Never read passwords or keys aloud. This script describes only what the video demonstrates. Architecture, performance and limitations remain in the README/reports. The [expanded script](DEMO_NARRATION.md) is retained as an alternative, not the final spoken track. Translating documentation does not modify the website, recording or voice.
