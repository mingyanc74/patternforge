# 在桌面和 VS Code 中运行

直接测试已部署的 [Clearflow](https://clearflow-patternforge.australiaeast.cloudapp.azure.com/) 无需安装开发软件。它连接真实服务而不是交互原型；处理自己的文件仍需要有权访问的真实 S3 Bucket 和只读凭据。见 [实际验收与剩余工作](AZURE_ACCEPTANCE_zh.md)。

## 推荐：运行完整系统

1. 打开桌面的 `patternforge` 文件夹。
2. 在 VS Code 的终端运行 `python scripts/bootstrap.py`。它只会首次创建私有 `.env`，不会覆盖已有配置。
3. 在 `.env` 填入 `LLM_API_KEY` 和你有权使用的 `LLM_MODEL`。这些值仅保存在本机，不提交 GitHub。
4. 确保 Docker Desktop 已安装并运行，然后执行 `docker compose up --build`。
5. 打开 `http://localhost:8080`。
6. 在应用中输入自己的 AWS 凭证、Bucket 与区域；临时凭证还需 Session Token。

完整流程：连接 S3 → 选文件／工作表 → 检查预览 → 选目标列 → 输入自然语言 → 运行 → 跟踪进度 → 查看分页结果。

## 本机没有 Docker 时

仍可运行真实前端和 Django API，检查界面、输入校验和连接接口；完整后台计算还需要 Redis 和 Spark Worker，不能只启动网页。

首次安装：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
```

终端一：

```powershell
.\.venv\Scripts\python.exe scripts/local_backend.py
```

终端二：

```powershell
cd frontend
npm ci
npm run dev
```

打开 `http://127.0.0.1:5173`。缺少模型配置时页面会明确提示，不会伪造处理成功。

## VS Code 已提供的任务

通过“终端 → 运行任务”选择：

- `PatternForge: full stack (Docker)`：完整后台和前端。
- `PatternForge: backend (local)`：本地 Django API。
- `PatternForge: frontend`：前端开发服务。
- `PatternForge: backend tests`：后端基础测试。
- `PatternForge: frontend check`：TypeScript 与生产构建。

可通过 Run and Debug 里的 `PatternForge: Django` 调试后端。Python 解释器默认指向项目 `.venv`。

## 没有 AWS／LLM 资源时如何验证

GitHub CI 使用明确标注的 S3／模型测试服务，测试真正的 Celery、Redis、PostgreSQL 和双 Worker Spark 管道。它能验证工程集成，不等于真实 AWS、真实模型和公网部署验收。最终评审仍需要自己的服务资源。

## 提交前必须完成

参照 [提交清单](SUBMISSION.md)，补上真实模型、真实 S3 验证、公开 HTTPS 地址、规模测试报告和实际演示视频。

不要在聊天、仓库、日志或录屏中展示真实密钥。桌面 `.env` 和 `.venv` 均已在 Git 忽略清单中。
