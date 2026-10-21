# 独立云部署与验收

本清单是部署与验收执行路径。2026-10-21（悉尼时间）用户确认后，完整应用已在 Azure 学生额度虚拟机启动，可信 HTTPS 可从外部访问；来源 IP 变化后的单地址 SSH 替换也经用户确认完成。见 [实际云端验收记录](AZURE_ACCEPTANCE_zh.md)。不得把云端健康检查当作全部 PDF 交付；真实 S3 资源、完整 S3 任务和演示视频仍待完成。

## 1. 账号和机器：由你确认免费资格

- 当前选择已开通的 Azure for Students，按 [学生额度方案](AZURE_STUDENT_zh.md) 核对规格、区域、库存和预计费用。账号开通不代表虚拟机已创建。
- 不绑卡、不升级；部署只消耗学生额度。不要把限额赠送额度冒充永久免费的服务器，不额外创建收费附加服务。最终资源创建前要获得用户确认。
- 当前配置目标：单台 Ubuntu x64、4 vCPU/16 GiB 内存，使用合适容量的 Standard SSD。首次构建前至少留 20 GiB 空闲磁盘；未来镜像、结果和数据增长需要另外监控空间。ARM 不是当前选择，整套运行仍未验收。
- 使用你的 SSH 公钥；私钥留在本机。SSH 仅允许你的来源 IP，网页放行 TCP 80/443（HTTP/3 UDP 443 可选），不要开放数据库、Redis、Spark、模型或 Flower。
- 同时检查云网络规则和主机防火墙。Docker 发布端口可能不受普通主机防火墙规则约束，因此不能只依赖一个防火墙界面。
- 准备一个归你控制的免费/已有 DNS 主机名，A 记录指向公网 IPv4；有 AAAA 时也必须正确。当前 HTTPS 配置要求 DNS 名，不支持裸 IP 作为可信证书方案。

## 2. 在服务器准备代码与私有配置

使用各工具的官方安装说明安装 Docker Engine 和 Compose v2、Git、Python 3.11 或更新版。模型下载脚本需要 Python 3.11+；不要依赖旧系统的默认 Python 版本。只克隆一次私有仓库；如需认证，使用你自己的安全登录方式，不把 Token 写进命令 URL、聊天、README 或镜像。

在仓库目录运行：

    python3 scripts/bootstrap.py
    python3 scripts/free_model.py --download-only

bootstrap 不覆盖已有 .env，也不输出密钥。使用服务器上的编辑器在私有 .env 加入 DOMAIN=你的真实DNS主机名，并确认以下项：

    DJANGO_DEBUG=0
    SESSION_COOKIE_SECURE=1
    SECURE_SSL_REDIRECT=1
    S3_ENDPOINT_URL=
    S3_ALLOW_HTTP=0

生产叠加文件也强制开启安全 Cookie、关闭调试并设置精确 Host/CSRF 来源。免费模型地址由 compose.local-model.yml 注入内部网络，不需要申请模型 API Key。不要使用 compose.ci.yml；它包含测试服务，不是真实 AWS。

不要把 .env 或数据目录传到 GitHub。保存好数据库备份和 CREDENTIAL_KEY：丢失该密钥会导致已存 AWS 凭证不可解密；不要随意重生成。

## 3. 检查后启动

    python3 scripts/cloud_preflight.py
    docker compose -f docker-compose.yml -f compose.local-model.yml -f compose.production.yml up -d --build --wait --wait-timeout 600
    docker compose -f docker-compose.yml -f compose.local-model.yml -f compose.production.yml ps

预检查只读配置、Docker、内存与磁盘，不打印配置值、不修改或部署任何东西；它不证明云额度、ARM、域名、证书或真实 AWS 已通过。

HTTPS 网关需要公网 DNS 已生效，80/443 可达，并持续保存 Caddy 证书卷。HTTPS 首次签发失败时先排查 DNS/端口，不要关闭证书验证或把 AWS 密钥输入明文 HTTP 页面。

## 4. 真实验收顺序

1. 从手机移动网络或另一台电脑访问 https://你的主机名，检查浏览器证书正常。不是只在服务器内部测试。
2. 检查 /api/health，数据库、队列、Worker 与模型配置正常；健康接口仅是诊断，不代替下面的完成任务。
3. 在 Worker 容器调用真实模型语义测试：

       docker compose -f docker-compose.yml -f compose.local-model.yml -f compose.production.yml exec -T worker python - --report /data/model-evaluation.json < scripts/evaluate_model.py

4. 使用课程/评审提供的真实 AWS Bucket 和最小只读凭证，在网页建立全新连接。密钥不进入聊天、录屏或截图；不要把测试协议服务当成 AWS。
5. CSV 预览→替换→任务完成→至少两页结果；检查字面量替换、空值、无匹配、行数与修改数。
6. Excel 选择不同工作表；再测试提取、标准化、刷新恢复、历史搜索、过期连接、失败提示和正在运行的任务取消。
7. 确认 Spark 确实有两个执行器及多分区；记录实际 Azure 型号、可用内存、耗时。已有 CI 性能不冒充所选云主机性能。
8. 按 SUBMISSION.md 录制真实流程，README 填实际网址和视频，向评审授予私有仓库访问权。

## 5. 运维与恢复

首次启动不应导入敏感业务数据。演示前确认结果/凭证的 24 小时保留策略与评审时间一致；原始 S3 对象始终只读。这个评估版本按浏览器 Session 隔离，没有跨设备账号同步；公开地址的访客仍可消耗计算资源，应限制演示窗口并监控队列。

备份 PostgreSQL、结果卷和独立保护的加密密钥。正常停止保留数据：

    docker compose -f docker-compose.yml -f compose.local-model.yml -f compose.production.yml down

不要加 -v；那会删除持久化数据。停止容器不等于解除分配虚拟机，也不停止所有磁盘/IP 费用，以 Azure 控制台为准。评审窗口、剩余额度和学生计划停用政策都要监控，不承诺永不掉线。

Flower 只监听服务器回环地址。需要查看时使用你自己的 SSH 转发，绝不把监控端口开放公网。故障日志也可能包含文件名或指令，分享前先脱敏；不要执行会输出完整 .env/Compose 环境配置的截图命令。
