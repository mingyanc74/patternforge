# Azure 学生额度部署方案

当前账号的 Azure for Students 已激活，截图显示 US$100 学生额度；不在仓库记录邮箱、租户、订阅 ID 或登录信息。2026-10-21（悉尼时间）用户确认配置、条款及额度消耗后，完整应用已在独立服务器运行。[正式网址](https://clearflow-patternforge.australiaeast.cloudapp.azure.com/)已通过外部 HTTPS 检查；[验收记录](AZURE_ACCEPTANCE_zh.md)明确区分已验证项目和真实 S3/视频缺口。

本次创建的 Standard_B4as_v2 / Ubuntu 24.04 / 64 GiB Standard SSD 已开始消耗学生额度。创建时的私钥下载未确认成功，之后用户本人已完成密钥恢复并保存私钥。已从 Azure 启动日志独立取得主机公钥并使用严格校验成功连接 SSH；私钥不进入仓库、聊天输出或服务器。Docker 和官方校验模型已安装，生产预检查通过，完整 Compose 构建已启动。

后续公网来源 IP 变化造成 SSH 白名单不匹配，用户已确认仅将旧来源替换为当前单一 /32。保存后严格主机校验的 SSH 已恢复，不开放全网、不新增服务器。部署退出码为 0，数据库迁移成功，实际模型 10/10、双执行器 Spark 合成检查和 25 项外部 HTTPS/会话检查均通过。用户确认目前没有真实 AWS S3 测试资源，真实 S3 全流程和演示视频仍待完成。

免费公共 IP DNS、SSH、可信 HTTPS 和完整容器应用已验证。下文中的草稿描述保留为创建前的核对记录，不代表当前仍未创建资源，也不代表真实 AWS 验收已完成。

## 费用边界：零现金支出，不是无限期免费

用户要求不绑卡、不输入支付方式、不升级付费。只考虑现有学生额度可以覆盖的资源。[学生计划官方规则](https://azure.microsoft.com/en-us/pricing/offers/ms-azr-0170p/)说明额度耗尽会停用订阅，不会因为本项目自动升级。不要移除支出限制，也不要购买额度不能覆盖的第三方 Marketplace 产品。

建议以正式提交后连续开放 7 天作为初步评审窗口；尚需按实际评审安排确认。开发时按需启动，正式评审期间保持可用。7 天是规划建议，不是已批准的资源创建或永久开放承诺。

### 候选配置和公开报价

- Ubuntu Server 24.04 LTS x64，不选 Windows、Ubuntu Pro 或预装收费软件。
- 候选 Standard_B4as_v2，4 vCPU、16 GiB 内存；[规格来源](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/basv2-series)。B 系列受 CPU 积分影响，持续重负载可能降至基线性能，不保证本机或 CI 的耗时。
- 本次读取微软公开价格接口，Australia East 普通 Linux 虚拟机计算价格为 US$0.19/小时，168 小时计算费为 US$31.92。报价查询记录的 UTC 时间为 2026-10-20T13:14:59Z，属于时点公开零售价，不是用户订阅实际账单或锁定价格。
- 该金额不含托管磁盘、公共 IPv4、流量、其它服务及税费，也不证明这个学生订阅有可用区域、规格、配额或库存。创建前必须再核对控制台总配置。
- Amazon S3 的请求和流量不由 Azure 学生额度支付，需要课程/数据拥有者明确允许的测试数据和只读权限。

本次只读进入该学生订阅的创建向导后，Australia East 的 Ubuntu 24.04 x64 / Standard_B4as_v2 可在大小列表选择，回到基本信息后未显示该规格不可用错误；控制台计算估价 US$138.70/月，与上述 US$0.19/小时一致。这只是配置草稿，不是已通过完整创建验证，也没有创建资源、SSH 密钥或开放网络端口。

草稿中另核对了 64 GiB Standard SSD LRS（E6），未添加数据磁盘。公开价格接口返回该磁盘 US$6.528/月、标准公网 IPv4 US$0.005/小时。仅作 730 小时/月的粗略折算，7 天计算 + 磁盘容量 + 一个公网 IPv4 约 US$34.26；**仍不含磁盘操作、网络出站、其它服务及税费，不是总价或封顶承诺**。Standard SSD 的 I/O 操作另计费，暂停/解除分配 VM 后保留的磁盘和 IP 仍计费。[磁盘计费规则](https://learn.microsoft.com/en-us/azure/virtual-machines/disks-understand-billing)

只读复查计算费，不需要 Azure 登录，不创建任何东西：

    python scripts/azure_price_check.py --region australiaeast --sku Standard_B4as_v2 --hours 168

脚本会排除 Windows、Spot、Low Priority、Cloud Services 和非正常小时计价；如果记录缺失或冲突会拒绝猜价。[官方价格接口](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices)

## 创建前需要确认

1. 订阅确实是 Azure for Students，保持未升级、不绑卡；学生额度余额足够覆盖预计运行、存储、网络和余量。
2. 控制台允许的区域、候选 16 GiB 型号和可用 vCPU 配额。若不支持，不为了提高配额升级付费。
3. 操作系统为普通 Ubuntu x64，磁盘使用合适容量的 Standard SSD；不要默认添加负载均衡器、Bastion、NAT Gateway、托管数据库、备份套餐或付费监控。
4. 只用一台虚拟机承载现有多容器应用；Spark Master 和两个 Worker 是真实并行进程，但不是三台物理服务器。当前结果卷设计只支持单宿主机。
5. SSH 只允许本人来源 IP，使用自己的 SSH 公钥，不把私钥发聊天、提交 Git 或录屏。网页只公开 TCP 80/443；模型、数据库、Redis、Flower 和 Spark 端口不公开。
6. 将预计消耗、评审窗口和最终控制台配置给用户确认后，才能执行最终创建。

上述配置已在用户确认后提交，虚拟机创建成功；后续步骤见本文开头的实际进展。没有升级付费、绑定支付方式或创建第二台虚拟机。

## 域名、HTTPS 和应用部署

可以给 Azure 公共 IP 设置 DNS name label，使用控制台实际返回的完整 DNS 名称，不必先购买域名。返回名称可能包含额外防重用标识，不能自行拼接主机名。[公共 IP DNS 官方说明](https://learn.microsoft.com/en-us/azure/virtual-network/ip-services/public-ip-addresses/)

在服务器私有 .env 中将 DOMAIN 设置为这个实际 DNS 名，按 CLOUD_DEPLOY_zh.md 执行预检查和完整 Docker Compose 启动。Caddy 需要有效公网 DNS 与可达的 80/443 来签发可信 HTTPS；不能把自签名裸 IP 当作验收地址。

服务器上运行全部 Django、PostgreSQL、Celery、Redis、Spark 和 Qwen 模型，不能只发布 React 页面。Azure Blob Storage 不能替代 PDF 要求的用户 Amazon S3 接入。

## 运行与额度保护

- 成本预算告警只是提醒，不是硬性停止开关；不能声称设置一个预算就绝不会超支。学生计划本身的额度保护也不代表所有 Marketplace 服务都可免费使用。
- 正式评审窗口内不要安排每天自动关机，否则网址会间歇不可用。
- 暂停开发时，使用 Azure 的停止并解除分配；仅在 Linux 内关机不等于释放计算资源。解除分配后磁盘和公共 IP 仍可能持续消耗额度。[虚拟机成本说明](https://learn.microsoft.com/en-us/azure/virtual-machines/cost-optimization-plan-to-manage-costs)
- 结束评审后先备份需要保留的数据库、结果和加密密钥；删除云资源须再次确认，不能自动删库或删除整组资源。
- 模型与 Redis 等内部服务不以独立托管产品购买，因此不新增模型 API 订阅。

最后仍要完成真实 S3、真实模型完整任务、外网 HTTPS 验收和演示视频，才能提交。
