# 真实 Amazon AWS S3 验收结果

2026-10-21（悉尼）已在正式 Azure 网站执行真实 AWS 验收。**88 项实际服务检查通过（第一组 65 + 第二组 23）**，另有 26 项 HTTPS / 门禁 / 会话检查。浏览器也实际输入真实 AWS 凭据，连接、选择 CSV / Excel、导入、提交并查看结果。

网站：[Clearflow / PatternForge](https://clearflow-patternforge.australiaeast.cloudapp.azure.com/)。应用部署版本 `049cae7f`。

2026-10-22 补充：网页已改名 Rulecraft，并完成融合原版浅色风格的 UI 更新；后端仍为同一已验收版本。[界面上线与真实快照回归记录](../reports/UI_REFRESH.md) 新增了一笔自然一小时连接到期约九小时后、保留期内成功处理的任务（1,000 行 / 800 个邮箱替换）。这不是 STS 到期或完整 24 小时连续观察；下文 2026-10-21 的加速过期原始记录保持不变。

完整测量、任务 ID、SHA-256、原始 JSON、失败和边界见 [真实 AWS 验收报告](../reports/REAL_AWS_ACCEPTANCE.md)。[测试前准备基线](REAL_AWS_PREPARATION_zh.md) 仅保留历史，不再代表当前进度。模拟 S3 / Moto / CI 模型替身仍只作开发证据，不计入上述真实服务结果，也未重新开展独立模拟桶公网验收。

## 你现在可以怎样测试

1. 打开上述网址，输入本机私密访问文件中的网站密码。网站密码不是 AWS 密钥，也不是个人账号注册系统。
2. 在 Connections 输入本机私密连接文件中的 Access Key、Secret、Bucket 和 Region；本次 IAM Key 不用 Session Token。
3. 主桶 `patternforge-test-20261021-a7f4c2`，Region `ap-southeast-2`，包含真实存储的 `test_data.csv` 和 `test_data.xlsx`。Excel 工作表为 `TestData`。
4. 选择文件并 Preview selected file，等待后台导入成功，再选择列和处理指令。
5. 连接默认一小时到期；重新连接可继续浏览/导入新文件。已有 Imported datasets 在各自 24 小时保留期内可继续处理，不依赖该连接。

| 操作 | 输入 | 实际已验证预期 |
|---|---|---|
| Find & replace | Email；`Find email addresses`；替换为 `[REDACTED]` | 1,000 行，800 个单元格改变 |
| Extract a field | Notes；`Extract the complete order identifier, including ORD- and the following digits`；新列 OrderID | 900 个订单号、100 个 null |
| Clean & standardize | Name 和 Status；`Trim leading and trailing spaces, collapse repeated whitespace, then convert to lowercase` | 每列 1,000 个单元格改变 |
| 多列替换 | Email 和 BackupEmail；同上邮箱指令 | 分别改变 800、700 个单元格 |

以上预期在 CSV 和 Excel 的三种操作中都已通过逐行比较；不是预置成功页面。第一次实际生成的三类模型计划均 cache_hit=false，后续重复有效计划已验证 Redis 命中。

## 已执行第一阶段

- 公网 HTTPS、网站密码门禁、Session / CSRF 检查通过。
- AWS 控制台核验 Free plan 显示 $100 credit、183 天剩余，到期 2027-04-21；没有升级付费计划。
- 两个真实私有 S3 桶，ACL disabled、全部 Block Public Access、SSE-S3；文件内容为虚构测试记录，但文件和 AWS 存储都是真实的。
- 专用 `patternforge-s3-test` IAM 用户无控制台密码，一组密钥，仅允许两桶 List / GetBucketLocation / GetObject / GetObjectVersion；不允许上传、删除或读取其他 AWS 资源。
- 真实 AWS 返回字节与本地文件及独立快照的 SHA-256 一致。CSV / Excel 均经过真实 Celery / Spark 导入，保留到期时间独立于连接。
- Replacement / Extraction / Normalization、状态进度、分页、跨会话隔离及原对象未改写均通过。
- 错误密钥、错误 Bucket 通过实际 AWS 请求安全拒绝；对已存在但尚未授权的第二个私有桶，真实网页显示权限不足。用户另行批准增加第二桶只读权限后，同一密钥成功连接并导入。
- 仅把本次新建测试连接的 expires_at 提前，验证过期后新列表 / 新导入返回 410；已有 CSV / Excel 快照各完成新任务，原数据保留到期时间不变。

**过期测试是加速应用过期测试**：没有等待自然一小时，没有测试 STS 自然失效，也没有连续观察完整 24 小时。这些时间跨度不能标记为已实测。

## 已执行第二阶段

- 第二真实桶 `patternforge-control-20261021-a7f4c2`，同一区域，同一组密钥，含复制的 CSV 和 `large_test_data.csv`；连接、列举、导入和转换均成功。
- 实际大文件 **50,000 行 / 4,765,075 bytes**，替换 40,000 个邮箱。两执行器 / 八分区，Spark 13.305 秒；转换创建到完成 19.431 秒。前者不含排队、导入和模型时间，大文件计划是缓存命中。
- 完整读取 100 页、每页 500 行，50,000 个唯一 ID，无重复/遗漏。任务期间历史与健康接口连续两次请求最大实测合计 0.125 秒，不代表多人压力测试 SLA。
- 真正 RUNNING 后发起取消，任务 CANCELLED 且不发布部分结果；错误 Excel 工作表异步 FAILED / SHEET_NOT_FOUND，无可用快照。
- 单任务隔离的受控瞬时故障：第一尝试在独立操作进程注入 S3_TEMPORARY_ERROR，真实 outbox / dispatcher / Celery 重试第二次，从真正 AWS 下载并完成 Spark，快照校验一致。未模拟任何成功响应，未关闭服务。这不是自然发生的 AWS 故障。
- 失败、取消与重试后依赖健康仍为 ready。

## 尚不能声称完成的部分

真实 AWS 测量上限本次为 50,000 行；已有 300 万行 CI 基准用的是明确标记的合成服务夹具，不能转称真实 AWS 大数据验收。两个 Spark 执行器共用一台 Azure 主机，不是跨物理机集群。完整演示视频和评审对私有仓库的访问权限仍待完成/确认，不因此宣称整个 PDF 已全部交付。

AWS Key 持续有效直到主动禁用，应用的一小时连接到期不会禁用 Key；评审结束后应及时停用。S3 请求/存储/跨云传输及 Azure 主机仍消耗有限免费额度，不承诺永久免费。密钥和网站密码仅保存在本机受限文件及授权服务端，不在聊天、Git、截图或报告公开。
