# Independent hosting without a payment method or cash subscription

Historical hosting/model selection, 2026-10-20/21. Provider allowances and prices below are dated findings, not guarantees of current eligibility. Subsequent real-AWS tests and the video are recorded in the [final audit](../reports/FINAL_REQUIREMENTS.md).

The selected approach runs the full application on an independent cloud server, not a laptop, temporary tunnel, static-only frontend or persistent GitHub Actions process. No paid plan is opened automatically and free-host capacity is not guaranteed.

The owner activated Azure for Students with US$100 credit without a payment method. The full application runs there; see [Azure evidence](AZURE_ACCEPTANCE.md) and [credit planning](AZURE_STUDENT.md). No cash payment/upgrade does not mean zero metered consumption or unlimited lifetime.

## Genuine model without a paid API

The official [Qwen3-4B GGUF](https://huggingface.co/Qwen/Qwen3-4B-GGUF) Q4_K_M weights are approximately 2.50 GB, Apache 2.0 licensed, served by the official llama.cpp CPU container. Downloads pin a revision and SHA-256. Thinking is disabled, sampling greedy, context 2048 and extra runtime repacking disabled to reduce memory demands.

The model receives instructions, operation and column names, not source rows, replacements or AWS keys. Its internal port is private. A small model cannot guarantee arbitrary-language accuracy; structured output and regex/real-Java safety checks remain necessary. No preset-answer fallback is used.

Expanded native Windows CPU semantics passed 10/10. A later [genuine Linux model-container run](https://github.com/mingyanc74/patternforge/actions/runs/39429271689) passed 10/10 bounded semantics and the complete 1,000-row replacement/extraction/normalization, Excel, cache, isolation and running-cancellation path. Model/application services were actual, but S3 was a protocol fixture. That run is not Azure-host, ARM or real-AWS acceptance. See [validation](../reports/VALIDATION.md).

## Rejected candidates and limits

At the 2026-10-20 check, [Oracle Always Free documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) described an A1 allowance equivalent to two OCPUs/12 GB RAM and 200 GB total block storage, not the older four-OCPU/24-GB figures. Eligibility must be checked against the actual account, home region and Always Free labels rather than relying on this dated record.

Oracle required card verification, so it was excluded under the owner's no-card constraint. The complete stack includes Django/PostgreSQL/Redis/Celery, Spark master/two workers, model and HTTPS. Two workers are distributed processes, not two physical machines.

Java image paths support amd64/arm64, and the pinned llama.cpp image includes both. No full ARM cloud run was obtained, so ARM acceptance is not claimed.

Never send passwords, card numbers, SSH private keys or tokens in chat. Azure student plans can restrict region/quota/SKU; if capacity is unavailable, stop and check rather than adding a card or switching to paid consumption.

The [Hugging Face Space documentation](https://huggingface.co/docs/hub/spaces-overview), checked during this historical selection, indicated a paid-plan requirement for new Docker/Gradio compute Spaces. A zero CPU-hour rate alone did not establish zero-budget account eligibility.

## Deployment and delivery

Use the [cloud deployment checklist](CLOUD_DEPLOY.md). The [public application](https://clearflow-patternforge.australiaeast.cloudapp.azure.com/) runs the full containers with trusted HTTPS. Source code does not automatically create more cloud resources.

A real DNS hostname must point to the host: an existing domain or obtained free hostname. Caddy cannot turn a bare IP into a trusted hostname certificate.

Amazon S3 separately requires an authorized owner's account/bucket and read-only credentials entered privately in the webpage. Fixtures are not AWS; never create/upload chargeable storage without authorization. Free model/cloud allowances do not guarantee free S3 requests or cross-cloud transfer. The owner later authorized actual AWS resources; those boundaries and results are in the real-AWS report.

Do not claim complete PDF delivery until external access, actual S3, asynchronous processing, paginated results and the real demo are supported by evidence. The final audit, rather than this historical selection plan, records completed and uncompleted items.
