# 五仓协同修复与发布验收（2026-10-01）

## 发布范围与边界

本轮修复平台、统一 Edge/合同和三家固件的可复现软件问题，并更新固定地图消费包。
公网运行入口采用现有 FastAPI、PostgreSQL/PostGIS、独立 worker 与 nginx 架构；
登录保护的纯模拟实例使用独立数据库、生产认证、只读访客和单独的模拟操作账户。
实际主机、域名、DNS、证书与上线授权仍应由部署操作者确认；本记录不代表已公网发布。

物理执行保持关闭。Switch ACK 保持 `acknowledged_unverified`，不声称灯具触点或负载
已被独立测量。地图不新增现场测量、室内米制配准、设备位置或电气绑定。
Sense 的受许可 XM125 Presence Detector 镜像仍由合格操作者提供并核验。

## 修复清单

### 平台控制时钟

- SQLite 事务的 `BEGIN IMMEDIATE` 可能等待写锁；控制时钟现在于事务建立后采样
- 生产处理每条命令前重新取时，避免前一条处理延迟使后续过期命令被下发
- 测试显式传入的时间保持确定性
- 命令历史时间不早于申请或前次转换；系统时钟回拨的原始处理时间保留在证据字段
- 自动回归先证实旧实现失败，再验证修复；原始 6.2 秒真实写锁反例改为正常 dispatched

### Edge 与跨语言合同

- 到达新鲜度和观测新鲜度分开；REAL Plug 使用认证 UTC 区间、测量年龄和有界不确定度
- 同 boot 的单调时钟/UTC 高水位与年龄界限持久保存，重启不刷新旧样本的控制资格
- 旧观测仍保留为历史并进入 durable outbox，但不能触发授权本地规则
- SWITCH 命令 ID 上限 48，PLUG 上限 47，与实际固件 wire decoder 一致
- 新增真实 Switch C decoder gate；Plug 的协同发布入口也保留和要求第四个 C gate
- Switch 没有认证 UTC，首次收到的无时钟状态无法证明绝对年龄；该局限保留在文档中，
  boot/单调时间及固件截止期检查没有被绕过

### 硬件软件入口

- Switch maintained defaults、目标 sdkconfig 与编译保护均要求 mbedTLS 证书日期校验
- 缺失时间功能、目标/库配置不一致、跳过校验等配置在编译阶段拒绝
- Sense vendor preflight 默认在缺少外部合格镜像与操作者记录时拒绝部署准备完成；
  profile-only 模式明确只是开发检查
- Switch 与 Plug 已重新通过 ESP-IDF5.4.3 的 ESP32-C3 目标构建；Sense 已重新通过
  Zephyr4.1.0/SDK0.17.0 的 nRF52832 目标构建，Flash129364B、RAM24776B
- 目标编译、host 密码学/协议回归与板上射频/电气验证是不同证据，不能互相替代

### 地图与平台包

- 固定地图提交：`76d7e487fb4763c5aad821e5f8b906dddab0370f`
- 运行包：`3e8b4bda8aaf2f83aefc2d759f9b390a14ff2f12e4112bb21a7f7bb997ed303b`
- 平台空间包：`57b3402d2ebca64f28f5880e434e8f9e3f6c1a143d80b3914b99a8c96412bceb`
- 有界经纬度尾数/背景网格规范化；分别记录原始与规范化来源 hash、锁文件和实际工具版本
- 修复嵌套 `detail/manifest.json` 遗漏；平台消费者拒绝未 hash-listed 或版本/来源不匹配的 native manifest
- 官方 Blender 5.2.0 重新提取 129 栋原生外观；全部 GLB 与原平台固定包逐字节一致
- 完整运行包独立重建两次，manifest 与全部 404 项产物身份一致；373 个背景 footprint 面积差为 0
- 任意宿主/任意工具链的字节等价没有被宣称；室内仍为 metadata_only

## 公网模拟部署

参见 [PUBLIC_DEMO.md](PUBLIC_DEMO.md)。使用独立 `compose.public-demo.yaml`，不得与开发、
普通生产或 transport overlays 叠加。关键约束：

- 只有 HTTPS gateway 发布端口，默认 loopback，公网绑定是已授权部署时的显式选择
- 数据库名、受限角色、bootstrap 标记和部署 ID 同时匹配才可迁移/初始化
- 完成后的初始化只能经验证后无操作返回；中断或非空库不能自动覆盖重种
- API、Alembic 和独立 worker 在模式不符时拒绝操作；预检在 schema/invariant 写入之前
- 访客只读，操作账户仍需 RBAC、CSRF、逐命令资格和期限检查；禁止外部 ingest/adapter、
  registry/身份修改、commissioning 与物理执行
- 默认不设置隐式到期；可显式指定到期时间。存储预算是带监督周期的软保护，包含峰值、
  WAL、备份的磁盘预算由部署方另行规划；不会自动删除证据或重置数据库
- 正式密码/证书不进入 Git；未生成或安装任何真实部署的长期凭据

## 本轮实际验证

最终测试计数、命令与原始证据由配套发布验收报告列明。以下已执行项目的含义保持区分：

- 原生 PostgreSQL 完整套件 464 项通过，1 个独占规模基准在主套件中按 opt-in 跳过；
  旧版 → head → 重复 head → alembic check 通过（本机 PG17.11/PostGIS3.5.2，与目标容器3.6有版本区别）
- 控制时钟/相关后端 65 项通过；真实 6.2 秒 SQLite 锁等待反例修复通过
- 全新 SQLite 全量种子：603 空间、4221 通道、446626 观测；真实 HTTP 验证只读权限、
  单路模拟 Switch 终态、旁路隔离、SHADOW 零下发、API 进程重启后的持久化
- 前端 200 项、TypeScript/生产构建、格式与双向 OpenAPI 合同检查通过
- Edge 86 项通过、47 subtests、1 个预期的非本机 OS 分支跳过；四个实际 C gate 均执行
- 真实 FastAPI → Edge → mTLS MQTT → Python 虚拟 Switch 三路 ACK；晚到回执不降级、
  无合计重复，24 条断网积压重启排空、不盲重放命令
- 地图 75 项、最终完整平台空间消费者 13 项通过
- 官方 Docker Compose v5.5.1 对开发/普通生产/公网模拟三配置的真实 `config` 校验通过，
  缺少必需配置时拒绝；这不等于 Docker 镜像冷启动通过

## 上线前仍需执行

在已批准的目标 Docker/PostGIS 环境运行全新数据库冷启动、镜像健康、受信任 HTTPS、
真实浏览器各角色交互、进程重启、备份与恢复、长期资源增长和目标域名检查。
本工作空间无 Docker Engine；现成云浏览器访问本机服务被 `ERR_BLOCKED_BY_CLIENT` 拒绝，
另起 Chromium 曾被 OS socket 权限限制。没有关闭 sandbox、改安全策略或建立公网隧道。
因此本机已有 HTTP/数据库/构建证据不能升级成目标容器或浏览器验收。

运行硬件前另需真实烧录、受许可 vendor image、配置身份、现场 RF/占用与计量验证、
电路/房间绑定、独立反馈和电气安全放行；这些不能由软件模拟或静态地图替代。
