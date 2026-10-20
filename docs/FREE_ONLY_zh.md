# 免绑卡、零现金支出的独立云方案

已选定：完整应用在独立云服务器运行，不使用电脑托管、临时隧道、静态前端或 GitHub Actions 长驻进程替代服务器。不会代开付费套餐，也不保证免费主机一定有库存。

当前选择 Azure for Students：用户已激活 US$100 学生额度，不需要输入支付方式。详见 [Azure 部署与额度规划](AZURE_STUDENT_zh.md)。这里的零现金支出指不绑卡、不升级、只用学生额度，不代表虚拟机没有计量费用或可以无限期运行。服务器仍未创建。

## 模型不需要付费 API

采用 [Qwen3-4B 官方 GGUF](https://huggingface.co/Qwen/Qwen3-4B-GGUF) 的 Q4_K_M 权重，约 2.50 GB、Apache 2.0；由官方 llama.cpp CPU 容器进行真实推理。下载脚本校验固定版本的 SHA-256。关闭思考、贪婪采样、2048 上下文和禁止额外内存重打包，以降低内存需求。

模型只接收指令、操作类型及列名，不接收数据行、替换内容或 AWS 密钥。内部模型端口不公开。小模型不保证任意自然语言准确；输出仍经过结构、正则安全和真实 Java 校验，不用预设答案兜底。

扩展后的 Windows 原生 CPU 语义实测 10/10 通过。后续 [Linux 真实模型容器验证](https://github.com/mingyanc74/patternforge/actions/runs/39429271689) 也通过了 10/10 小样本语义检查，以及完整 1,000 行替换、提取、标准化、Excel、缓存、隔离和运行中取消流程。模型和应用服务是真实的，但 S3 仍是协议测试服务；这不是所选 Azure 主机、ARM 性能或真实 AWS 验收。详见 [验证记录](../reports/VALIDATION.md)。

## 已排除的原候选与限制

截至 2026-10-20 核实的 [Oracle Always Free 官方说明](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)，A1 ARM 的月度免费额度合计相当于 2 OCPU、12 GB 内存，另有总计 200 GB 的免费块存储。不要沿用旧的 4 OCPU/24 GB 数字；以自己账号、主区域和创建页面的 Always Free 标识为准。

Oracle 原候选需要银行卡验证，不符合用户明确的免绑卡要求，因此不再引导注册或使用它。完整服务包括 Django、PostgreSQL、Redis、Celery、Spark Master、两个 Worker、模型和 HTTPS 网关；2 个 Spark Worker 是分布式进程，不是两台物理主机。

Java 镜像路径已改为识别 amd64/arm64；所固定 llama.cpp 镜像包含这两种架构。但尚未获得 ARM 云主机进行整套运行，不能宣称 ARM 已验收。

不要在聊天发送密码、卡号、SSH 私钥或 Token。Azure 学生计划仍可能限制区域、配额和规格；如果没有可用资源，先停止并核实，不改为绑卡或按量付费。

[Hugging Face 官方说明](https://huggingface.co/docs/hub/spaces-overview)显示，新建 Docker/Gradio 计算 Space 需要付费计划，不能把其 CPU 小时价为零等同于零预算开户。

## 部署与最终提交

按 [独立云部署清单](CLOUD_DEPLOY_zh.md) 操作。服务器准备好后才下载模型、启动容器、配置域名和 HTTPS。项目不会自动创建云资源，也没有现成公网地址。

需要一个指向云主机的真实 DNS 主机名。可以使用你已持有的域名或自行获得的免费 DNS 主机名；当前 Caddy 配置不能把裸 IP 自动变成可信 HTTPS 地址。

真实 Amazon S3 仍需要你或课程/评审提供测试 Bucket 和只读凭证，私下在网页输入。测试协议服务不是 AWS；不自动创建或上传收费存储。云主机和模型免费不代表数据拥有者的 S3 请求/流量一定免费。

最后完成外网访问、真实 S3、完整异步任务和结果分页，再录制真实演示视频并填入 README。未完成前不标记 PDF 全部交付。
