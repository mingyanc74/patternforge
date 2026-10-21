# Azure 实际验收记录

日期：2026-10-21（悉尼时间）。

正式网址：https://clearflow-patternforge.australiaeast.cloudapp.azure.com/

这是独立 Azure 主机上的真实应用，不依赖本机开机；不是高保真模拟页面。服务器继续消耗有限学生额度，不承诺永久免费。没有设置 7 天后自动关闭，评审结束后应另行确认备份与资源处理。

## 本次通过的检查

| 项目 | 实际证据与边界 |
|---|---|
| 主机 | Australia East，Standard_B4as_v2，4 vCPU / 16 GiB，Ubuntu 24.04 x64，64 GiB Standard SSD；两个 Spark Worker 共用一台主机，不是两台物理服务器 |
| 安全部署 | 主机公钥从 Azure 启动日志独立核验，严格 SSH 校验；SSH 仅一个获准来源 /32，公网仅网站 80/443；模型、数据库和队列未公开 |
| 完整容器 | PostgreSQL、Redis、Django、Celery Worker、dispatcher、Spark Master 与两个 Worker、真实 Qwen 模型、前端、Caddy 均运行；迁移退出码和部署退出码为 0 |
| 外部 HTTPS | 本机外部 HTTP 客户端和浏览器均成功访问可信 HTTPS；`/api/health` 为 ready，所有服务标记为 true |
| HTTP/会话 | `scripts/check_cloud_http.py` 的 25 项检查通过：安全头、静态资源、内部监控阻断、安全 Cookie、独立会话、匿名 CSRF、空凭据拒绝及没有虚假历史 |
| 真实模型 | 官方校验的 Qwen3-4B Q4_K_M，llama.cpp CPU；10/10 固定语义案例通过，每项 5.559–26.473 秒；不是任意输入的准确率保证 |
| 真实 Spark | 合成 10,000 行，10,000 个预期替换，两个执行器、8 分区，10.9 秒，Spark 3.5.8；不涉及 S3，也不是完整应用 Job 的端到端耗时 |
| 网页交互 | 正式页面、空字段校验、STS Token 输入、帮助中的服务状态、无预置任务历史已检查；修复了窄窗口步骤导航零宽 flex 导致的横向溢出 |
| 本机回归 | 76 passed / 1 skipped；跳过项为 Windows 缺少 Hadoop 原生 DLL 的 Parquet 测试，不能把跳过冒充通过；该既有路径在 Linux CI 验证 |

原始非敏感报告保留在被 Git 忽略的 `reports/local/azure-model-evaluation.json`、`azure-spark-acceptance.json`、`cloud-http.json`。不提交私钥、环境密钥、账户标识或包含联系信息的 Azure 截图。

服务健康接口只检查模型配置，不证明推理质量；本表的单独真实模型测试补充了这一点。Django 部署检查中的 HSTS 提醒由 Caddy 公网策略承担，已在外部实际响应验证；未加入浏览器 preload 名单。

## 仍未完成，不能标记全部交付

### 用户确认的模拟桶功能验收（2026-10-21 补充）

用户随后明确同意使用模拟桶进行功能演示。代码 `7baa1c2` 已部署到上述正式网址；原有真实 S3 连接入口保留，不改写真实 S3 endpoint。默认访客可点击 `Try sample bucket`，无需 AWS 密钥。模拟标识贯穿连接、文件、任务、结果和历史记录。

`scripts/check_sample_e2e.py` 从外部可信 HTTPS 对正式应用执行 **44 项检查，全部通过**；全组测试耗时 201.52 秒（包括多个串行任务，不是单笔任务 SLA）。CSV 三种操作均为 1,000 行，替换 800 个邮箱、提取 1,000 个订单编号、标准化 1,000 个名字；Excel 两工作表发现、Customers 120 行 / 96 个邮箱替换成功。各转换实际使用 2 个 Spark 执行器、8 分区。缓存命中、完整结果分页、空值与前导零、异步错误、运行中取消及访客隔离均通过。独立浏览器亦完整提交并查看了一笔 1,000 行 / 800 单元格替换任务。

更新后另行通过 25 项 HTTPS/会话检查。本机最终回归 84 passed / 1 skipped，5 个前端测试通过；[对应代码的 Linux CI 三组任务全部成功](https://github.com/mingyanc74/patternforge/actions/runs/39562338200)。详见 [模拟桶验收证据](../reports/SAMPLE_ACCEPTANCE.md) 和 [用户测试指南](SAMPLE_BUCKET_zh.md)。没有新增云资源或开放内部服务；仅经用户确认替换单个管理来源 /32，并验证严格 SSH 主机密钥连接正常。

**边界不变：模拟桶是应用内只读合成数据适配器，不是真实 Amazon S3 或公网 S3 协议服务。真实模型、Celery/Redis、Spark 和结果管道均实际运行。用户接受模拟演示，不等于老师已豁免 PDF 的真实 S3 要求。**

用户确认目前没有真实 Amazon S3 测试 Bucket 和只读权限。因此以下项目仍缺证据：

1. 从正式网页连接新的真实 AWS Bucket，完成 CSV 和 Excel 的异步处理。
2. 实际 S3 任务的结果分页、缓存、取消、错误恢复和完整端到端时间。
3. 使用真实 S3 的演示视频及评审方私有仓库访问权限。

现有 CI 已验证完整合成 S3 管道，但不等于真实 AWS。不能用 Azure Blob、模拟 S3 或本机文件替换原要求，也不自动开通需要支付方式的 AWS 账户。需由课程、评审或有权使用的 AWS 账号拥有者提供测试 Bucket，密钥只在可信 HTTPS 网页中输入。
