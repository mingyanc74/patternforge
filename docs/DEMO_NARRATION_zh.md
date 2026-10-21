# Rulecraft Demo 配音稿（英文第一人称／中文对照）

配套影片：`docs/demo/Rulecraft-Real-AWS-Demo-Silent.mp4`。1280×720，约 **05:18**，无声。录制于 2026-10-22（悉尼时间）。所有操作均在 Azure 公网网站进行，使用真实 Amazon S3 文件；文件内容为虚构测试联系人，不是个人资料。

建议用剪映／CapCut 导入视频，另建录音轨，按下列时间段朗读英文。中文仅供理解，不需要两种语言都读。语速约每分钟 110–125 个英文词；留白处可以停顿，不必一直讲话。不要在录音中读出密码、AWS Key 或完整私密配置。视频没有仿造你的声音；最终人声由你本人录制。

## 时间轴与讲稿

### 00:00–00:11 · 网站门禁

**English:** This is Rulecraft, my natural-language workspace for transforming cloud data. I enter the website password privately, with recording paused.

**中文：** 这是我的 Rulecraft 自然语言云端数据处理工作台。我暂停录制，在画面外输入网站访问密码。

### 00:11–00:29 · 真实 S3 连接

**English:** Website access and AWS access are separate. Here I enter my bucket name and Sydney region. I also enter a genuine read-only AWS Access Key and Secret Key, with recording paused to protect them.

**中文：** 网站门禁和 AWS 授权是两回事。这里填写真实桶名和悉尼区域。真实只读 Access Key、Secret Key 也由网页输入，但暂停录制保护密钥。

### 00:29–00:38 · 文件列表

**English:** These CSV and Excel files really exist in my private Amazon S3 bucket. I select the CSV.

**中文：** 后端已经实际连接 Amazon S3。这两个 CSV、Excel 文件真实存放在私有桶中。我先选择 CSV。

### 00:38–01:05 · 异步导入

**English:** Preview starts an asynchronous import. The backend downloads the authorized object and Spark creates an independent dataset snapshot. Django handles the API, Celery runs the heavy work, and Redis supports the queue. Only a bounded preview is sent to the browser; the source object is not overwritten.

**中文：** 预览会启动异步导入：后端下载有权限读取的对象，Spark 创建独立快照。Django 提供 API，Celery 处理重任务，Redis 支持队列。浏览器只收到有限预览，原文件不会被覆盖。

### 01:05–01:18 · 自然语言配置

**English:** I select Email, describe the pattern in ordinary language, and enter a literal replacement. I review the source, target column and instruction before submitting.

**中文：** 选择 Email，用自然语言描述要匹配的内容，再填写字面替换值。提交前确认数据源、目标列和指令。

### 01:18–02:05 · 真模型与 Spark 任务

**English:** Submission creates a persistent job rather than blocking the web request. The genuine language model generates a structured plan. The backend validates the rule before Spark processes the snapshot across partitions. The stage and estimated progress are visible here. These three demonstration tasks were later checked against the database: all used real Amazon S3 imports, uncached model inference, two Spark executors and eight partitions. Progress is stage-based, not a precise row counter.

**中文：** 提交后创建持久化任务，而不是让网页请求一直等待。真实语言模型生成结构化方案，后端先验证安全性，再由 Spark 分区处理。这里显示阶段和估计进度。数据库核对证实，本片三个任务均使用真实 AWS 导入、未命中模型缓存、两个 Spark 执行器及八个分区。进度条不是精确的逐行计数。

### 02:05–02:16 · 替换结果与分页

**English:** One thousand rows are ready, with eight hundred email replacements. I open page two; results are fetched in bounded pages.

**中文：** 任务成功：处理 1,000 行，替换 800 个邮箱。切换第二页，浏览器不会一次取回全部结果。

### 02:16–02:54 · Excel 导入

**English:** Next I select the real Excel object from the same S3 bucket. The workbook is imported through the asynchronous pipeline too. This workbook uses the TestData worksheet. Both formats produce retained snapshots, so later transformations do not need to download the source again. These are real files containing deliberately synthetic test records, including missing and invalid values.

**中文：** 接着选择同一真实桶里的 Excel 文件，也通过异步流程导入。它使用 TestData 工作表。两种格式都会产生保留快照，后续转换无需重新下载原对象。文件真实存在，内容是特意编造的测试记录，包括空值与错误值。

### 02:54–03:03 · 提取规则

**English:** I choose Notes and describe the order ID format: ORD, a hyphen, then digits. The new column is OrderID.

**中文：** 提取时选择 Notes，明确订单号格式为 ORD- 后接数字，新列名为 OrderID。

### 03:03–03:49 · 提取执行

**English:** Extraction uses the same model, Celery and Spark path. The custom ID format is in my instruction because private source rows are not sent to the model. The original Notes column is kept, and a non-matching value produces null in the new column. Identical validated instructions can reuse the Redis plan cache; this recorded instruction was an actual uncached model request.

**中文：** 提取使用相同模型、Celery 和 Spark 流程。需要在指令中明确自定义 ID 格式，因为不会把私有数据行发给模型。Notes 保留，无匹配时新列为空。相同且通过验证的指令可使用 Redis 缓存；本片这次确实发起了未缓存模型请求。

### 03:49–03:55 · 提取结果

**English:** Nine hundred rows have an extracted order ID. The remaining rows have no matching reference.

**中文：** 900 行提取出订单号，其余行没有匹配的订单引用。

### 03:55–04:13 · 多列标准化

**English:** Finally, I reuse the imported Excel snapshot. I select Name and Status, then request trimming, repeated-space cleanup and lowercase conversion. This is the third supported transformation.

**中文：** 最后复用已导入的 Excel 快照，选择 Name、Status 两列，要求去除首尾空白、合并重复空格，再转小写。这是第三种转换。

### 04:13–04:52 · 标准化执行

**English:** The model selects approved normalization operations, not arbitrary executable code. The task again runs asynchronously. Original S3 files remain unchanged. Connections normally expire after one hour; imported snapshots and results have their own twenty-four-hour retention. Previous acceptance checked processing after connection expiry. That is separate evidence, not a claim that this short video observes a full day.

**中文：** 模型选择允许的标准化操作，不执行任意生成代码。任务仍然异步运行，S3 原文件不变。连接通常一小时过期，导入快照及结果另行保留 24 小时。此前已经验证连接过期后仍能处理快照，但本短片不代表连续观察了完整一天。

### 04:52–04:58 · 标准化结果

**English:** The result contains one thousand rows and two thousand updated cells across the two selected columns.

**中文：** 结果共 1,000 行，两列合计更新 2,000 个单元格。

### 04:58–05:04 · 快照

**English:** Imported datasets show their real source and individual retention deadline, independently of the connection.

**中文：** 导入列表显示真实数据源及各自保留截止时间，独立于连接期限。

### 05:04–05:11 · 历史

**English:** Job history preserves the status, duration and result links, so I can return to completed work.

**中文：** 任务历史保留状态、用时和结果入口，方便回到已完成任务。

### 05:11–05:18 · 收尾

**English:** The service is ready. My README documents the architecture, setup, real-service results and separate development evidence.

**中文：** 在线服务已经就绪。README 提供架构、可复现启动方法，并明确区分真实服务验收与开发测试证据。

## 配音注意事项

- 页面显示的任务 Duration 从任务执行阶段计时；数据库创建至结束时间还包括排队等开销，二者不可混称。
- 本视频为真实浏览器截图序列编码，约每 0.5 秒采集一帧，输出为 20 fps；重复帧不是新的状态。任务执行等待未加速；章节之间剪去操作准备间隔。不是原生 20 fps 桌面录屏，鼠标指针不一定被采集。
- 视频只演示 1,000 行数据。真实 AWS 较大测试为 50,000 行；3,000,000 行测试使用开发 fixture，不要在配音中说成真实 AWS 百万行测试。
- 网站使用同一 Azure 主机上的两个 Spark worker／executor 容器，不是两台独立物理服务器。
- 本片为可交付无声版。加入你本人声音后，保留同样的事实范围，再替换 README 中的视频附件即可；勿把密钥或网站密码录入成片。
