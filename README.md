# 碳迹未来 · CARBENTRA Campus

**基于 AIoT 云边端协同的高校智慧能碳管理平台**  
Powered by CARBENTRA · AIoT Campus Energy Orchestration Platform

把校园空间、用电设备、计量边界和可执行策略连接起来。前端用同一组真实 API 浏览全校、定位设备、核算能碳、预测负荷、评估策略并追踪执行结果。

## 本地启动

安装 Docker Desktop（Linux containers）或 Docker Engine + Compose，然后在仓库根目录运行：

```powershell
# Windows PowerShell
.\tools\start-dev.ps1
```

PowerShell 7 (`pwsh`) is the shared host-script runtime on Windows, Linux and macOS.

打开 http://localhost:8080 。开发账户 `admin` / `development-only`；另有 `operator`、`analyst`、`viewer` 同密码测试不同权限。首次构建下载依赖，首次启动导入全校空间及历史模拟数据。端口仅绑定本机。生产部署使用独立配置，见 [运行与交接](docs/OPERATIONS.md)。

## 本机开发工具链

Python 统一为 3.12；后端、Edge、测试和资产工具共用根目录 `uv.lock` 的平台依赖标记。
Node.js 使用 24；Linux 服务由 Docker Desktop 运行。首次安装先创建项目环境：

```powershell
uv venv --python 3.12 .venv
uv sync --locked --all-groups
npm --prefix frontend ci
pwsh -File tools/verify-local.ps1 -OutputDirectory D:/Temp/carbentra-check
```

Edge 的认证 Sense 私钥权限校验在 Linux 运行；Windows 可以运行软件测试和 Plug/Switch MQTT 开发，不能绕过 POSIX 私钥权限门槛。

## 系统范围

- 全校总览、二维与三维空间浏览、楼层与房间定位
- 设备注册、时间化空间/电路绑定、能力与运行状态
- 原始遥测、质量和覆盖率、能耗/碳排/费用独立核算
- 负荷预测、基线比较、策略评估、批准与显式调度
- 命令状态追踪、告警处理、排课与维护约束
- 报告导出、角色与校区权限、会话管理、操作审计
- PostgreSQL 持久化、独立 worker、Docker 交接、备份恢复

空间包包含 3 个来源校区、136 个建筑登记项、603 个空间单元；其中 129 个建筑有地图模型。这些数量代表来源资产覆盖，不代表已安装设备。当前 v3 开发种子在这 603 个空间上生成教室场景与 4,221 个能力通道，设备、观测和能源数据均明确标记为 `SIMULATED`；样例规模随种子与空间包版本变化，不能当作现场数量。生产不自动导入样例，真实继电器调度默认关闭。

## 五仓库各自负责什么

| 仓库 | 唯一主责 | 交给其他仓库的接口 |
|---|---|---|
| `carbentra-campus-platform`（本仓库） | 云端、用户界面、身份与时序绑定、教室状态/联动、核算与调度；共享 Edge 与 IoT 应用合同 | 统一 HTTP API、`packages/iot-contract`、`edge/`、策略与命令、报告 |
| `carbentra-smart-plug` | Plug 硬件、固件、本地保护与物理放行依据 | 具体 Plug 线协议、设备能力、遥测/反馈与工程资产 |
| `carbentra-presence-sensor` | Sense B 有线 5V、XM125 I2C 存在检测、raw 光照的硬件与固件 | 诊断广播/认证 GATT、观测质量与工程资产；无 PIR |
| `carbentra-smart-switch` | 三路普通照明开关硬件、固件、本地按键/保护与合计计量 | 三路命令/软件回执、单份合计计量与工程资产；无独立触点反馈 |
| `njupt-map` | 校园空间与三维资产创作 | 带稳定 ID、坐标和哈希的运行时空间包 |

`packages/iot-contract` 是唯一 IoT 应用语义与合同主源，`edge/` 是唯一现役多设备网关。各硬件保留自己的具体线协议，由 Edge 适配为统一事件/能力/命令；Plug 仓库旧 Edge 已退役，不再作为并行运行实现。Switch 回执最多为 `acknowledged_unverified`，三路照明共享的合计电量只计一次。未知或陈旧的 Sense 观测不能解释为无人。

`njupt-search` 作为空间语义和界面风格参考；原软件仓库不作为本实现的依赖。生成的协议和空间副本附带来源哈希，不在消费端另造一套可编辑主源。

## 从哪里继续开发

- [架构与不变量](docs/ARCHITECTURE.md)：对象、边界、数据流和设计取舍
- [API 契约](docs/API_CONTRACT.md)；HTTP 机器契约位于 `packages/contracts/openapi.json`
- [共享 IoT 合同](packages/iot-contract/README.md)与[统一 Edge](edge/README.md)：三类硬件的具体适配、持久运输与授权边界
- [空间包](packages/spatial/README.md)：ID、坐标、导入和重建
- [中文使用与开发交接指南](docs/USER_GUIDE.md)：首次运行、全校工作流与继续开发
- [运行与交接](docs/OPERATIONS.md)：开发、生产、迁移、备份恢复
- [Docker 验证记录](docs/DOCKER_VERIFICATION.md)：实际运行结果及未验证项
- [参考材料取舍](docs/REFERENCE_DECISIONS.md)：三份演示文稿和来源工程如何影响设计

实际部署前仍需现场计量校准、网络与设备身份配置、负载适配、硬件安全检验和机构审批。软件测试、仿真闭环和三维模型不等于真实 220 V 硬件合格或已经实现节能收益。

## Isolated public simulation

For an authenticated, read-only public visitor demo with a separate simulation operator, see [the isolated HTTPS deployment guide](docs/PUBLIC_DEMO.md). Use the standalone `compose.public-demo.yaml`; deployment requires an approved host, DNS/TLS, budget and target acceptance. Development Compose must not be exposed publicly.
