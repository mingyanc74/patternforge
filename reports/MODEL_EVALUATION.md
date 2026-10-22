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
| Chinese-language instruction to identify email addresses (exact input retained in `scripts/evaluate_model.py` as Unicode escapes) | hello@example.com | Pass | 18.734 |
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

## Subsequent format-clarification regression

The initial container workflow passed its original six semantic samples but failed the complete synthetic-S3 pipeline at extraction's exact changed-cell count. Reproducing the instruction "Extract order IDs" with the real model generated a guessed label-based rule which did not match the generated ORD-number data. A column name is not a sufficient definition of a custom identifier, and private cells are deliberately not sent to the model.

The fix uses operation-specific instructions and public few-shot guidance, including a supported text-search example and an unspecified-format refusal. Those examples are inputs to actual inference, not a fallback or a lookup table. Cache version changed; null refused rules are not cached, do not start Spark, and return RULE_NEEDS_CLARIFICATION without pointless retries. The extraction UI explains the required prefix/format.

The expanded native evaluation passed **10/10** with the final operation-specific prompt, including the original six samples, an ambiguous custom-ID refusal, an explicit ORD-number rule, a Chinese INV-number rule and the exact pipeline normalization phrasing. The ORD plan was also checked against different lengths and nonmatching examples. Requests plus validation took about 6–15 seconds in this run; not a performance guarantee.

Intermediate prompt-only revisions failed 1–3 cases, including accidental whole-cell anchoring. They were not accepted as successful. A complete container run is required for the final code; the local 10/10 result does not itself certify that run or real AWS.

The end-to-end test now describes the actual custom identifier format and keeps its original exact row count, changed-cell count and result-value assertions. It additionally checks that an ambiguous request fails before Spark and saves bounded, generated test-only diagnostics before correctness assertions.

## Verified Linux container integration

The [genuine-model run on 2f5efb9a](https://github.com/mingyanc74/patternforge/actions/runs/39429271689) completed successfully. It used the pinned llama.cpp container, Qwen3 weights and actual Django, PostgreSQL, Celery, Redis and Spark services. **Only S3 was a synthetic protocol fixture; this is not real-AWS authorization evidence or a public deployment.**

- Expanded model semantics: **10/10 passed**, with request/validation times of 10.751–48.741 seconds on this 2-logical-CPU Linux runner. The cold first request was the slowest; native timings are not substituted for container timings.
- Complete task harness: **284.61 seconds**, with 1,000 rows and 10 columns per operation. Replacement, extraction and normalization each produced the exact expected 1,000 changed cells and preserved the complete row count.
- Each operation recorded 8 effective partitions and 2 executors, with one core/1 GiB per executor and 1 GiB driver memory. Spark stage times were 24.921, 26.288 and 24.488 seconds respectively, not end-to-end request times.
- Excel inspection/transformation, real Redis plan-cache reuse, ambiguous-ID refusal before Spark, session isolation and actual running Spark cancellation passed. Cancellation took 1.65 seconds in this run.
- Machine-readable semantic and end-to-end reports are attached to that workflow as genuine-model-e2e-report.

These are bounded correctness samples, not general semantic accuracy. For example, one generated email extraction rule used a broader character range than intended; the fixed positive sample passed, but this does not certify comprehensive negative-case or RFC email validation. Users must review generated rules and results against their own data. No deterministic rule replacement was used to make the model test pass.
