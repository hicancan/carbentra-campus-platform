# 本次 Windows / Docker 验证记录

2026-10-01 在 Windows 11、Docker Desktop Linux containers 上实际执行。
Python 3.12.13、uv 0.11.17、Node 24.16.0、PostgreSQL 17 / PostGIS 3.6。
以下为本次结果；已删除的旧 QEMU 日志和历史 PASS 不计入本次验收。

| 范围 | 本次结果 |
|---|---|
| Python 后端、HTTP/domain、PostgreSQL、classroom、基础设施 | 整理后完整测试 413 passed，1 skipped；唯一跳过项为显式 opt-in 的独占 forecast 规模基准 |
| 公开空间包 | 12 项通过；603 空间身份保留，室内参考几何不再随公共包分发，129 原生外观保留 |
| 迁移 | 旧版本 `ba682468c8c6` → head → 重复 head → `alembic check` 全部通过 |
| Node 24 前端 | 39 个测试文件、200 项通过；类型/格式/API 生成契约和生产构建通过 |
| Windows Edge + MSVC Plug 编译结果 | 72 passed、2 个 POSIX 分支跳过、24 subtests；真实 startup、时间签名、证书日期 C 二进制均执行 |
| Linux Edge | 70 passed、4 skipped、24 subtests；包含 Windows 无法执行的两个 POSIX 私钥权限检查。3 个 C 验证器由 Windows 套件互补，另一个跳过为反向 OS 分支 |
| 真实 Mosquitto mTLS + Edge | 6 个虚拟设备、3 家族、2 房间；断网积压保留、重启排空、无命令重放 |
| 真实 FastAPI → Edge → mTLS MQTT → Switch 软件端 | 3 路均回 `acknowledged_unverified`；人工保持、晚到 delivery receipt 不降级、合计功率不重复 |
| 全新 Docker 开发数据库冷启动 | db/api/worker/analysis/web 全 healthy；API 首次启动约 101.7 秒。未使用恢复数据绕过初始化 |
| 实际 Microsoft Edge 浏览器 | 最终公开包 9 组全通过：鉴权、13 路由、603 教室矩阵、三路状态/单份计量、历史/异常、真实 UI 模拟命令与 900 秒人工保持/旁路隔离、零下发 SHADOW 评估、无室内几何时从房间清单选择 |
| API 重启 | 浏览器创建的命令及 SHADOW 评估重新读取成功，状态与无物理验证语义保留 |
| 备份恢复 | 真实 `pg_dump` → 新临时数据库 `pg_restore` → 应用角色读取；恢复 2489 个设备、迁移版本 `98f4a5aa6b9d` |
| 生产配置演练 | 独立临时生产模式数据库，8 个长期服务 healthy；HTTPS/会话 8 项通过，broker 安全 3 项通过 |
| 产品发布物 | 3 家族认证 HTTP / SHA-256 / gzip / 私有缓存检查通过；实际 GLTFLoader 部件定位通过；资产工具 Node 3 项、Python 7 项通过 |
| npm 依赖审计 | 根浏览器工具及前端的 `npm audit --audit-level=moderate` 为 0 漏洞（检查时结果） |

生产演练核验了错误 CA / 主机名拒绝、开发密码拒绝、Secure / HttpOnly /
SameSite cookie、HSTS、CSRF / Origin、登出撤销、无样例设备和价格、关闭模拟及
物理调度。broker 核验真实 mTLS 连接、拒绝无客户端证书连接、断开超出
8192 字节限制的真实 MQTT 帧。测试证书只存放在临时目录并有四小时有效期。移除管理员 bootstrap secret 后的生产模式重启与 HTTPS 复测也通过。

## 复现入口

先创建项目 `.venv`，再安装锁定依赖：

```powershell
uv venv --python 3.12 .venv
uv sync --locked --all-groups
pwsh -File tools/verify-local.ps1 -OutputDirectory D:/Temp/carbentra-check
```

`verify-local.ps1` 自建、自清理独立 PostGIS 测试实例，并拒绝复用已有 Compose
项目。原生 Edge 的 C 编译证明需要明确设置 `CARBENTRA_STARTUP_TEST_BINARY`、
`CARBENTRA_TIME_TEST_BINARY`、`CARBENTRA_CERT_TEST_BINARY`；Windows ASan 程序需要匹配的 MSVC 运行库（由构建脚本随可执行文件复制，或通过 MSVC 开发环境提供）。不能把缺少这些二进制时的 skip 当作执行成功。

Docker 运行镜像由根 Compose 构建；Linux Edge 集成镜像入口为
`tests/deployment/edge.Dockerfile`，以非 root 身份运行：

```powershell
docker compose build api web
docker build -f infra/edge.Dockerfile -t carbentra-campus-edge:local .
docker build -f tests/deployment/edge.Dockerfile -t carbentra-campus-edge-tests:local .
docker run --rm carbentra-campus-edge-tests:local
docker run --rm carbentra-campus-edge-tests:local python tools/check_mqtt_multidevice.py --mosquitto /usr/sbin/mosquitto --output /tmp/mqtt.json
docker run --rm carbentra-campus-edge-tests:local python tools/check_backend_multidevice.py --mosquitto /usr/sbin/mosquitto --backend-python /app/.venv/bin/python --output /tmp/backend.json
pwsh -File tools/verify-deployment.ps1 -OutputDirectory D:/Temp/carbentra-production-check
```

新版公开空间包接入后再次构建 API/Web/Edge，开发服务健康，浏览器 9 组通过且无 pageerror。重复验收会等待 300 秒最小驻留窗口，使用独特策略名，不跳过安全检查。

生产演练脚本已独立真实运行通过；退出时移除自己创建的项目/卷和临时秘密。
浏览器、产品 HTTP 与重启持久化的参数见 `tests/system_upgrade/README.md`。
数据库备份使用 `tools/backup.ps1` / `tools/restore-check.ps1`。

## 保留边界

本次是软件与虚拟端完整链路，未连接或验证真实射频、继电器、220 V 负载、
现场计量校准与节能收益。Switch 仍无独立触点反馈，回执不能升级为物理成功。
Sense 认证私钥检查在 Linux 执行，Windows 不绕过权限要求。

上述耗时来自本机，未清空操作系统缓存，不是生产容量承诺。独占 forecast
规模基准未运行；远程 GitHub Actions 需在实际推送后单独核验。
