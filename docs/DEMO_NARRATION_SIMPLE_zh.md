# Rulecraft 简短功能演示配音稿

配合现有 05:18 视频。只读英文，中文供理解。每段在对应画面开始时读，读完自然停顿；处理等待时不需要一直讲话。正常语速即可，不需要讲后台组件或测试报告。

## 00:00–00:11 · 开场

This is Rulecraft. It helps users clean and transform CSV and Excel data using plain English.

这是 Rulecraft，可以用自然语言清理和转换 CSV、Excel 数据。

## 00:11–00:38 · 连接 S3

First, I connect my Amazon S3 bucket using my AWS credentials. I've hidden the keys for security. The available files appear here.

首先用 AWS 凭证连接我的 Amazon S3 桶。密钥输入部分已隐藏。连接成功后，这里显示桶内文件。

## 00:38–01:18 · 选择文件和配置替换

I'll start with the CSV file. After previewing the data, I select Email and ask the app to find email addresses. I'll replace them with “REDACTED,” then review and run the job.

先选择 CSV。预览数据后，选择 Email 列，用自然语言要求查找邮箱，并替换为 REDACTED。确认配置后运行任务。

## 01:18–02:05 · 任务处理中

The job runs in the background, and I can follow its progress here.

任务在后台处理，这里可以查看进度。

（说完等待即可，不需要继续解释。）

## 02:05–02:16 · 结果和分页

The job is complete: one thousand rows processed and eight hundred email replacements. I can browse the results page by page.

处理完成：共 1,000 行，替换了 800 个邮箱。结果支持分页查看。

## 02:16–03:03 · Excel 和字段提取

The app also supports Excel. I select the workbook and preview its data. This time, I'll extract order IDs from Notes into a new column called OrderID.

也支持 Excel。选择工作簿并预览数据，这次从 Notes 中提取订单号，放入新列 OrderID。

## 03:03–03:49 · 等待提取

（无需配音，保留真实任务进度画面。）

## 03:49–03:55 · 提取结果

The new column contains nine hundred extracted order IDs.

新列成功提取出 900 个订单号。

## 03:55–04:13 · 多列标准化

Finally, I'll clean Name and Status together: remove extra spaces and convert the text to lowercase.

最后同时清理 Name 和 Status 两列，去除多余空格并转为小写。

## 04:13–04:52 · 等待标准化

（无需配音，保留真实任务进度画面。）

## 04:52–04:58 · 标准化结果

Both columns are cleaned, with two thousand cells updated.

两列清理完成，共更新 2,000 个单元格。

## 04:58–05:18 · 历史与收尾

I can reuse imported datasets and return to completed jobs from the history. The original S3 files stay unchanged. Thanks for watching.

可以复用已导入的数据，也可以从历史记录返回已完成任务。S3 原文件不会改变。谢谢观看。

---

录音时不要读出密码或密钥。本稿只描述视频实际展示的操作；架构、性能测试与限制仍由 README 和验收报告说明。原详细配音稿保留不变，网站和视频也未修改。
