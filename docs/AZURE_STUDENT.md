# Azure student-credit deployment plan

Historical planning/deployment record from 2026-10-20/21. Pricing below is a dated observation, not a current quote. For subsequent real-AWS/video results and remaining limitations, use the [final audit](../reports/FINAL_REQUIREMENTS.md).

Azure for Students was activated with US$100 credit. Email, tenant, subscription ID and login details are not recorded here. After the user confirmed configuration, terms and credit consumption on 2026-10-21 (Sydney), the full stack ran on an independent host. The [public URL](https://clearflow-patternforge.australiaeast.cloudapp.azure.com/) passed external HTTPS; [Azure evidence](AZURE_ACCEPTANCE.md) separates deployment checks from later AWS acceptance.

The Standard_B4as_v2 / Ubuntu 24.04 / 64 GiB Standard SSD VM consumes credit. Initial private-key download was not confirmed; the owner subsequently recovered/saved the key. The host public key was independently obtained from Azure boot logs before strict SSH connection. Private keys stayed local, out of Git/chat/server. Docker, checksum-verified model weights and production preflight were prepared, followed by the full Compose build.

After the public source IP changed, the user approved replacing only the previous SSH source with the current single `/32`. Strict SSH then worked without global access or another VM. Deployment/migrations succeeded with exit code 0. Genuine-model 10/10, two-executor synthetic Spark and 25 external HTTPS/session checks passed. Real AWS and video were pending at that historical stage and have since been documented separately.

Public-IP DNS, SSH, trusted HTTPS and containers were verified. Draft descriptions below are pre-creation evidence, not a claim that no VM exists now or that deployment alone proves AWS acceptance.

## Cost boundary: no cash payment, not perpetual free hosting

The user required no payment method or paid upgrade; only resources covered by existing student credit were considered. The [student-offer terms](https://azure.microsoft.com/en-us/pricing/offers/ms-azr-0170p/) describe subscription disabling when credit runs out. This project does not upgrade the account. Do not remove its spending protection or purchase Marketplace products outside the credit allowance.

A continuous seven-day review window after submission was proposed, subject to actual assessment timing. Start on demand during development and remain available during review. Seven days is a planning suggestion, not an approved automatic shutdown or permanent-availability promise.

### Candidate configuration and historical public quote

- Ordinary Ubuntu Server 24.04 LTS x64, not Windows, Ubuntu Pro or paid preinstalled software.
- Standard_B4as_v2, 4 vCPU / 16 GiB; [official specification](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/basv2-series). Burstable CPU credits can limit sustained performance; local/CI timings are not guaranteed on this host.
- Microsoft's public retail API at **2026-10-20T13:14:59Z** returned US$0.19/hour for ordinary Linux compute in Australia East, or US$31.92 for 168 hours. This was neither the subscription's actual bill nor a locked price.
- That excludes managed disks, IPv4, traffic, other services and taxes, and establishes no quota/region/capacity entitlement. Recheck the complete console configuration before creating resources.
- Azure credit does not pay Amazon S3 request/transfer costs; use explicitly authorized data and read-only access.

In the read-only draft wizard, Australia East's Ubuntu 24.04 x64 / Standard_B4as_v2 was selectable without an unavailable-size error. The console's US$138.70/month compute estimate matched US$0.19/hour. At that draft stage no resources, keys or ports had been created; full creation was not yet validated.

The draft also checked a 64 GiB Standard SSD LRS (E6), without extra disks. The retail API returned US$6.528/month for the disk and US$0.005/hour for standard public IPv4. A rough 730-hour-month conversion gave approximately US$34.26 for seven days of compute, disk capacity and one IPv4. **This still excludes disk transactions, egress, other services and tax; it is not a total or cap.** Standard SSD I/O costs extra; retained disks/IPs can keep consuming credit after VM deallocation. See [disk billing](https://learn.microsoft.com/en-us/azure/virtual-machines/disks-understand-billing).

Read-only compute-price recheck, without Azure login or resource creation:

```text
python scripts/azure_price_check.py --region australiaeast --sku Standard_B4as_v2 --hours 168
```

The script excludes Windows, Spot, Low Priority, Cloud Services and unsuitable billing units, and refuses missing/conflicting prices. [Official retail API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices).

## Before creation

1. Confirm Azure for Students, no paid upgrade/payment method, and credit covering expected compute/storage/network plus headroom.
2. Check permitted regions, 16 GiB SKU and vCPU quota. Do not upgrade to paid merely for quota.
3. Use ordinary Ubuntu x64 and an appropriately sized Standard SSD. Do not add load balancers, Bastion, NAT Gateway, managed databases, backup plans or paid monitoring by default.
4. Use one VM for the container stack. Spark master/two workers are real parallel processes, not three physical hosts. The result-volume design is single-host.
5. Permit SSH only from the owner's source IP using a public key. Never share/commit/record the private key. Expose only website TCP 80/443; keep model/database/Redis/Flower/Spark private.
6. Obtain the owner's confirmation of consumption, review window and final configuration before actual creation.

Those resources were subsequently created with approval. No paid upgrade, payment-method addition or second VM was performed.

## DNS, HTTPS and application

Azure public IPs can have a DNS name label, avoiding a domain purchase. Use the actual full hostname returned by the console, including any anti-reuse suffix, rather than constructing one. [Public IP DNS documentation](https://learn.microsoft.com/en-us/azure/virtual-network/ip-services/public-ip-addresses/).

Set `DOMAIN` privately on the server to that actual hostname and follow [cloud deployment](CLOUD_DEPLOY.md). Caddy needs valid public DNS and reachable 80/443 for trusted HTTPS; a self-signed bare IP is not the acceptance URL.

Run the complete Django/PostgreSQL/Celery/Redis/Spark/Qwen stack, not only React. Azure Blob does not replace the assessment's user-provided Amazon S3 integration.

## Operation and credit protection

- Budget alerts are notifications, not hard stopping controls. Student-credit protection does not make all Marketplace services free.
- Avoid daily automatic shutdown during review, which makes the URL intermittently unavailable.
- When pausing development, stop/deallocate through Azure; shutting down Linux is not deallocation. Disks/IPs may remain billable. [VM cost guidance](https://learn.microsoft.com/en-us/azure/virtual-machines/cost-optimization-plan-to-manage-costs).
- After review, back up required database/results/encryption keys before any separately approved deletion. Never automatically delete the database/resource group.
- Internal model/Redis containers are not separately purchased managed services; no model-API subscription was added.

Complete genuine S3 workflows, external HTTPS, scale evidence and a real demo before claiming full delivery. Later results and uncompleted items remain in the final audit, not inferred from this plan.
