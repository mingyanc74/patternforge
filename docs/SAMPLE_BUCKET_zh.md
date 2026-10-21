# 模拟 S3 测试桶

用户在 2026-10-21 确认使用模拟桶完成无 AWS 账号的功能测试。这不是老师或评审已豁免 PDF 中真实 S3 要求的证明。

## 网页测试

打开正式网址，点击 `Try sample bucket`，或 Connections 页的 `Use sample bucket`。不需要用户名、密码或任何 AWS 密钥。模拟连接只属于当前浏览器会话，默认 24 小时过期，可以断开后重新连接。不要使用真实个人数据测试。

桶名 `clearflow-sample-bucket`，标识 `sample://`；这是应用内只读数据适配器，不是 Amazon S3，也不是公网 S3 协议服务器。没有公开存储端口，没有 AWS 写操作，没有假 AWS 密钥。

| 文件 | 内容 / 预期 |
|---|---|
| `examples/customers.csv` | 1,000 行，ID 保留前导零；Email 中 800 个邮箱、100 个不匹配文本、100 个空值；Name 有中文、空格、逗号和换行 |
| `examples/workbook.xlsx` | Customers 120 行，Orders 80 行；先选择工作表，再预览 |
| `examples/large-customers.csv` | 50,000 行，适合结果分页和较长任务测试；不是百万行性能证据 |
| `edge-cases/empty.csv` | 故意为空，预检应显示 EMPTY_FILE |
| `edge-cases/duplicate-headers.csv` | 故意重复列名，异步检查应失败并说明原因 |
| `edge-cases/unsupported.txt` | 不支持的格式，网页禁止选择 |

建议先使用 customers.csv，保持 CSV 默认 UTF-8 和逗号：

1. 替换：选择 Email，指令 `Find email addresses`，替换为 `[REDACTED]`。预期 1,000 行，Email 的 changed_cells=800。
2. 提取：选择 Notes，指令 `Extract order IDs beginning with ORD- followed by digits`，新列 `OrderID`。预期 1,000 行，每行提取 ORD- 后的数字编号。
3. 标准化：选择 Name，指令 `Trim spaces, collapse repeated whitespace, then convert to lowercase`。检查空格、英文大小写、中文、换行的结果。
4. 结果翻页、刷新恢复任务、历史记录查看和复用、取消任务以及错误处理仍使用正式 API。无预置成功任务或伪造进度。

模型仍是服务器上的真实 Qwen 推理；Celery/Redis、数据库、分布式 Spark、Parquet 分页结果仍实际运行。模拟仅限数据来源。样本文件按固定白名单生成后临时存入任务目录，Spark 与原有管道一致读取；租约、超时、取消、清理继续生效。

## 管理和 API

`.env` 中 `SAMPLE_BUCKET_ENABLED=1` 开启入口；默认关闭。变更后重建/重启相关应用容器。无需额外云资源、服务订阅或支付方式，但任务依然消耗现有 Azure 学生额度。

`GET /api/bootstrap` 返回 `sample_bucket_enabled`。保留会话 Cookie 和 CSRF Token，向 `POST /api/s3/sample-connection` 发送空 JSON `{}`，得到 source_type=sample 的连接。重复连接复用该会话未过期的模拟连接。后续使用原有 files/inspect/jobs/results API。连接和任务返回 source_type，网页持续标注模拟来源。

原有 `POST /api/s3/connections` 始终要求用户提供真实凭据；模拟模式不改写 S3_ENDPOINT_URL，不影响真实 S3 连接。API 不接受外部样本 URL、任意本机路径或可变 bucket 参数。

## 交付边界

模拟来源可验证应用功能，但不能证明 AWS 权限、网络连接、STS 过期或 S3A 读取行为。保留真实 S3 验收缺口，后续有真实只读桶时直接使用原有连接入口。演示录像应明确显示“Simulated S3”，不能把它描述成真实 Amazon S3 验收。
