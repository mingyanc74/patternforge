# 独立云部署与验收

本清单不创建账号、不购买资源、不替你接受注册条款。当前没有已部署公网网址；这是服务器到位后的执行路径。

## 1. 账号和机器：由你确认免费资格

- 注册并登录支持 Docker 的独立 Linux 云主机账号。候选与免费限制见 [零预算方案](FREE_ONLY_zh.md)。
- 只创建控制台明确标记 Always Free、并在账号免费配额内的资源。不要使用即将到期的试用金实例冒充永久免费，也不要升级付费或添加收费负载均衡器。
- 当前配置目标：单台 Ubuntu、2 OCPU/12 GB 内存、50 GB 启动盘，至少留 20 GiB 磁盘供首次构建。未来结果、镜像和数据增长需要另外监控空间。ARM 整套运行尚待验证。
- 使用你的 SSH 公钥；私钥留在本机。SSH 仅允许你的来源 IP，网页放行 TCP 80/443（HTTP/3 UDP 443 可选），不要开放数据库、Redis、Spark、模型或 Flower。
- 同时检查云网络规则和主机防火墙。Docker 发布端口可能不受普通主机防火墙规则约束，因此不能只依赖一个防火墙界面。
- 准备一个归你控制的免费/已有 DNS 主机名，A 记录指向公网 IPv4；有 AAAA 时也必须正确。当前 HTTPS 配置要求 DNS 名，不支持裸 IP 作为可信证书方案。

## 2. 在服务器准备代码与私有配置

使用项目官方安装说明安装 Docker Engine 和 Compose v2、Git、Python 3。只克隆一次私有仓库；如需认证，使用你自己的安全登录方式，不把 Token 写进命令 URL、聊天、README 或镜像。

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
7. 确认 Spark 确实有两个执行器及多分区；记录 ARM 型号、可用内存、耗时。已有 x86 CI 性能不冒充免费 ARM 主机性能。
8. 按 SUBMISSION.md 录制真实流程，README 填实际网址和视频，向评审授予私有仓库访问权。

## 5. 运维与恢复

首次启动不应导入敏感业务数据。演示前确认结果/凭证的 24 小时保留策略与评审时间一致；原始 S3 对象始终只读。这个评估版本按浏览器 Session 隔离，没有跨设备账号同步；公开地址的访客仍可消耗计算资源，应限制演示窗口并监控队列。

备份 PostgreSQL、结果卷和独立保护的加密密钥。正常停止保留数据：

    docker compose -f docker-compose.yml -f compose.local-model.yml -f compose.production.yml down

不要加 -v；那会删除持久化数据。停机不一定释放云资源或停止所有可能费用，以云控制台为准。免费实例也可能因容量或闲置政策回收；不承诺永不掉线。

Flower 只监听服务器回环地址。需要查看时使用你自己的 SSH 转发，绝不把监控端口开放公网。故障日志也可能包含文件名或指令，分享前先脱敏；不要执行会输出完整 .env/Compose 环境配置的截图命令。
