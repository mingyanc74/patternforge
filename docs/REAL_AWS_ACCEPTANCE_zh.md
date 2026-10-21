# 真实 Amazon S3 验收

最终验收使用真实 Amazon AWS S3。现有模拟 S3 / Moto / CI 模型替身仅是开发测试证据，不计为真实 AWS 验收，也不再另设模拟桶公网验收阶段。

## 当前核查（2026-10-21，悉尼）

- 网站：<https://clearflow-patternforge.australiaeast.cloudapp.azure.com/>。
- 部署代码 `049cae7f`，已包含 PostgreSQL 可空关联行锁的兼容性修复。修复前版本存在任务无法启动问题，不隐去这次失败。
- 修复版本 CI：<https://github.com/mingyanc74/patternforge/actions/runs/39580701915>。全部三个自动测试任务通过，其中分布式 CI 仍是开发夹具，不是真实 AWS。
- 26 项外部 HTTPS / 门禁 / CSRF / 会话检查通过。该检查不提交处理任务、不连接 AWS。
- 云端数据库只读核查：真实 S3 连接记录 0，真实 S3 成功导入 0；未读取或输出凭据。
- 当前新连接默认 1 小时，独立数据快照默认保留 24 小时。配置值已核实，真实 AWS 过期场景尚未执行。
- S3 endpoint override 为空，不将真实入口重定向到模拟服务。
- 12 个常驻服务运行。服务启动与模型配置存在，不等于本次真实数据全链路成功。
- 内置浏览器访问本次被客户端拦截；未绕过安全限制。外部 HTTPS 客户端验证已通过，真实浏览器文件选择和提交仍待验证。
- 用户确认已有真实 AWS 账号，将本人登录；尚未核实该账号的额度、Bucket、Region 和授权。

## 准备好的文件（尚未上传）

配对文件保存在任务输出目录 `outputs/aws-real-acceptance/`，不含个人真实数据。Excel 工作表为 `TestData`，第一行是字段名，没有额外标题行或公式。CSV 为 UTF-8、逗号分隔，`\N` 表示 null，支持带引号逗号和换行。两个文件解码后的所有 1,000 条记录已逐项比对一致。

| 文件 | 大小 | SHA-256 |
|---|---:|---|
| test_data.csv | 130,760 bytes | 1982f7bed81768f67e6c222fd07f178202cdf17aafb6b3cf79fe8ade98867fca |
| test_data.xlsx | 37,719 bytes | 8414f6168ddcb232c514f4e224a8133058dc2111ccdeb54dc1eea957eba672e2 |

以上只证明本地文件准备完成，不证明 S3 上传或导入。

| 操作 | 列 / 指令 | 独立预期 |
|---|---|---|
| Replacement | Email；`Find email addresses`；替换为 `[REDACTED]` | 1,000 行，Email changed_cells=800；错误邮箱和 null 不变 |
| Extraction | Notes；`Extract the complete order identifier, including ORD- and the following digits`；新列 OrderID | 900 个非空，100 个 null；ID=000001 对应 ORD-100001 |
| Normalization | Name、Status；`Trim leading and trailing spaces, collapse repeated whitespace, then convert to lowercase` | 两列各 1,000 个单元格改变；Name 示例 `alice chen example` |
| 多列替换 | Email、BackupEmail；邮箱替换 | changed_cells 分别为 800、700 |
| 分页 | 默认每页 100 行 | 10 页，无重复或缺失 ID；结果顺序不要求与输入一致 |

## 账号与费用边界

1. 由用户本人登录 AWS 控制台，检查账号计划、可用额度和失效时间。AWS Educate 课程登录不自动等同于可授权本应用的 AWS 账号。
2. 优先复用用户明确授权的测试 Bucket。确认额度前不创建桶、不上传文件、不升级 Paid plan。
3. 若需新桶：使用 General purpose、S3 Standard、ACL disabled、全部 Block Public Access 开启、默认 SSE-S3。Region 在账号实际可用区域中选择，确认后固定。
4. 不开启网站托管、复制、加速、额外日志、KMS 自建密钥、NAT 或新 EC2。应用读取私有桶不需要公开对象，也不需要给 S3 配浏览器 CORS。
5. 网站凭据只用于指定测试桶读取。上传由用户现有授权身份完成，读写权限与应用只读权限分开。
6. 优先使用合适的临时凭据（Access Key + Secret + Session Token）；如必须创建专用 IAM Key，先确认指定身份、最小权限和保存方式。不使用 Root Key，不在聊天、Git、截图或报告中展示秘密值。
7. S3 存储、请求和向 Azure 传输可能产生用量费用；预算告警不是自动停费机制。免费与否以该账号实际计划和额度为准，不能承诺 S3 永久零费用。

参考：[AWS 免费计划说明](https://aws.amazon.com/free/free-tier-faqs/)、[S3 入门与费用提示](https://docs.aws.amazon.com/AmazonS3/latest/userguide/GetStartedWithS3.html)、[S3 访问控制](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-management.html)。

应用针对指定桶所需的身份策略可参考 `deploy/aws-test-readonly-policy.template.json`。替换占位桶名后经用户确认使用；它不是公开 Bucket policy，不允许上传、删除或访问其他桶。

## 第一阶段执行记录

| 项目 | 当前状态 | 成功时须保存的证据 |
|---|---|---|
| 公网 HTTPS、网站门禁、会话 | 接口检查通过；浏览器手动验收待完成 | 不含密码的时间、响应状态、截图 |
| AWS 账号、额度和只读权限 | 用户称已有账号；未核验 | 计划 / 额度核对结论，授权范围，不记录密钥 |
| 两文件上传到真实桶 | 未执行 | 实际 Region、对象 key、字节数、ETag / VersionId、校验值 |
| 网页输入真实凭据并连接 | 未执行 | source_type=amazon_s3、脱敏连接 ID、实际 AWS 响应 |
| 文件列表 / CSV / Excel 选择 | 未执行 | 两对象可见、工作表选择、失败反馈 |
| Spark 导入并保存快照 | 未执行 | 成功 inspection ID、快照 SHA-256、保留到期时间 |
| 三种转换 | 未执行 | 每个任务的真实模型计划、行数、changed_cells / 提取空值分布 |
| LLM / Celery / Redis / Spark 异步链路 | 服务运行；真实数据链路未执行 | 已持久化任务状态、队列流转、模型调用、Spark application / executor 信息 |
| 状态、进度、分页 | 未执行真实数据验收 | 状态序列、结果总数、分页 ID 完整性、原文件未改写 |
| 连接过期后快照可用 | 未执行 | 过期后新导入 410，旧快照新转换 SUCCESS，保留到期时间不变 |
| 错误凭据 / 无权限 / 错误桶 | 未执行 | 实际请求、安全错误提示、无新数据快照、无秘密泄漏 |

连接过期测试优先等待测试连接真实到期。若为加快验证只调整**本次新建测试连接**的应用 expires_at，须在报告标注“加速过期测试”；它不等同于已等待一小时，也不等同于 AWS STS Token 自然到期。24 小时是配置保留窗口，不宣称已经连续观察 24 小时。

S3 的 HeadBucket 可能对不同原因返回同样的 403/404，不能要求应用准确推断 AWS 未公开的原因；应显示可操作的安全提示并拒绝继续导入。

## 第二阶段（第一阶段成功后）

全部仍待执行。复用已成功导入的真实 AWS 数据，不使用预置成功结果替代。

- CSV / Excel 各完成三种转换，核对中文、前导零、null、多行文本及原对象未修改。
- 执行上述多列转换，逐列比较统计结果。
- 在用户确认费用/额度后上传较大文件，先以 100,000 行为目标，再按资源情况确定更大规模。目标不是实际成绩，记录真实行数、字节数、总时间与各阶段时间。
- 较长任务期间读取健康、历史和分页接口，记录响应时间；不以“有任务 ID”代替非阻塞验证。
- 取消只针对本次创建的测试任务。失败和重试使用限定测试流程，不关闭或破坏生产 Redis / 模型服务。
- 相同有效配置二次运行验证 plan cache_hit；记录缓存键隔离和 Redis 可用性，不把模型生成快误当命中。
- 在另一个用户明确授权的真实 Bucket 上完成连接与导入；没有第二个桶时此项保持未完成，不能以代码通用性代替实际测试。
- 每项记录 PASS / FAIL / NOT RUN、时间、部署版本、任务 ID、规模、耗时、预期和实际；遇到失败保留失败与修复后记录，绝不补写虚构成功值。
