# Genuine free CPU model evaluation — 2026-10-20

This was an actual inference run, not a canned response server or prompt-to-regex lookup. The same application request_plan, validate_plan and Java validator were called. Only public fixed sample text was used.

## Reproducible configuration

- Official Qwen/Qwen3-4B-GGUF Q4_K_M, revision bc640142c66e1fdd12af0bd68f40445458f3869b.
- Model SHA-256: 7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5.
- Official llama.cpp b11669 Windows CPU x64 runtime; checksum pinned in scripts/free_model.py.
- Windows 11, Python 3.12, Java 17; host has 16 logical CPUs, inference used 4 threads, one parallel slot.
- Context 2048, temperature 0, reasoning off, no-repack. Loopback only; model alias patternforge-local.
- No model API subscription, GPU, cloud credential or dataset uploaded to a model provider.

| Instruction / operation | Expected semantic result | Result | Request + validation seconds |
|---|---|---|---:|
| Find email addresses | plus-tag email with .technology TLD | Pass | 28.641 |
| 识别文本中的电子邮箱地址 | hello@example.com | Pass | 18.734 |
| Match runs of decimal digits | 123 from Order AB123X | Pass | 17.516 |
| Extract the email address from the text | team@example.org | Pass | 16.078 |
| Trim ends, collapse repeated whitespace and convert to lowercase | alice smith | Pass | 14.953 |
| Make all letters uppercase and trim surrounding whitespace | ALICE | Pass | 11.984 |

The initial request encoded Chinese as literal Unicode escapes inside the user-message JSON and passed 5/6. Preserving the actual Unicode instruction fixed the Chinese case; privacy regression tests cover both schema modes. No hard-coded semantic answer was added.

## Limits and resource findings

Six fixed samples are not a benchmark of general language comprehension, RFC-complete email validation, prompt-injection robustness or production semantic accuracy. Some explanations were verbose or truncated by the schema's 300-character bound, despite the pattern being valid. The UI shows the validated rule for review.

On this memory-constrained computer, default runtime repacking initially failed an extra allocation. Disabling repacking and using context 2048 allowed the run. A concurrent backend Java check failed while resources were heavily used; after the model process was stopped, the complete backend suite passed 62 tests with the documented native-Windows Parquet skip. Do not increase concurrency without resource testing.

This native evaluation did not exercise Amazon S3, the public URL, ARM64, the model container or the complete task stack. Those are separate acceptance steps. The manual free-model CI workflow exercises the container model with real application services and explicitly synthetic S3; inspect its actual result before asserting success.

Run on a genuine configured model with scripts/evaluate_model.py; use --local for the loopback native model. JSON output is saved under ignored reports/local, never populated with user datasets.
