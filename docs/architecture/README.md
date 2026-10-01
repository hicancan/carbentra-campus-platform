# 当前实现架构图

两张图描述 2026-10-01 的软件实现，版本为 `3.1`，状态为「工程交付版，实物待验收」。图中物理执行默认关闭；现场安全、计量、安装与设备放行是独立前置条件。架构图不充当测试通过、实机接入或已实现节能的证据。

- [平台逻辑架构与数据控制闭环](01_platform_logical_architecture.png) · [SVG](01_platform_logical_architecture.svg)
- [Docker 云边部署与五仓库责任](02_docker_deployment_repo_ownership.png) · [SVG](02_docker_deployment_repo_ownership.svg)

## 与源码的对应关系

- `compose.yaml` / `compose.prod.yaml`：`web`、`api`、`db`、一次性 `migrate`、`worker` 和独立 `analysis`；后端运行角色共用一个镜像。默认 `worker` 在独立循环运行 control 与 simulation，二者也可用 `--role` 分进程运行；生产不启用 simulation
- `backend/app/worker.py` / `analysis.py`：控制、模拟和分析职责分开，小时重建与预测训练不进入控制循环
- `backend/app/projection.py` / `forecast_jobs.py`：原始遥测保留为事实源；小时修订是可重建的预测派生证据，不替代核算电量。持久预测任务与缓存绑定授权范围、参数、输入修订和模型版本，保留生成/训练时间
- `backend/app/routes.py`：浏览器通过同源 HTTP API 与实际 SSE 事件流读取状态，客户端支持轮询回退；没有 WebSocket 接口
- `packages/spatial/dist/manifest.json` / `frontend/src/components/CampusMap3D.tsx`：二维和全校轻量 LOD1 优先，129 栋已发布作者外观按需加载；室内示意图保留独立坐标
- `packages/iot-contract/` 与 `edge/`：平台仓库是唯一应用合同与多设备 Edge 主源；Plug、Switch、Sense 保留具体固件线格式，通过具体适配器接入。旧 Plug Edge 不再作为并行运行服务
- `backend/app/classrooms.py` / `classroom_simulation.py`：能力通道、时点/区间状态、手动与维护边界；开发种子明确为 SIMULATED，真实来源与未知/陈旧状态不能被模拟替代
- `compose.transport.yaml`：可选 broker、平台 Edge 与私有 HTTPS 网关。默认关闭命令轮询；虚拟命令有单独 opt-in，物理门禁始终默认 OFF；实际 BLE/BlueZ 接入另行审阅，默认不挂载主机无线资源
- 三个硬件仓库各自维护 Plug、Sense B、Switch 的硬件/固件/工程资产；`njupt-map` 维护空间作者主源；平台维护云端、共享合同与 Edge。图中使用三类设备仓库分组卡片，合计是五个独立仓库

Sense B 为有线低压 5V、XM125 I2C、raw 光照方案，没有 PIR 或电池续航能力。Switch 的三个继电器通道共用一份合计计量，软件 ACK 只能到 `acknowledged_unverified`，不能当作独立触点反馈。未知、陈旧与未认证数据不代表无人；本地保护与手动保持优先。镜像实际构建完成与运行/浏览器验收是不同阶段，图中状态不宣称后者已通过。

具体规则见 [架构说明](../ARCHITECTURE.md)。运行与验证边界见 [运行手册](../OPERATIONS.md) 和 [Docker 验证记录](../DOCKER_VERIFICATION.md)。

## 重建

唯一随仓库交付的生成器为本目录的 `create_diagrams.py`，默认原位生成这两对 SVG/PNG 和 `manifest.json`，不创建另一套输出目录。需要 Python 3、Pillow、系统 `librsvg` / `cairo`，以及 `/usr/share/fonts/opentype/noto/` 下的 Noto Sans CJK Regular/Bold 字体。生成不联网，不需要浏览器或 GPU。

从仓库根目录运行：

```sh
python docs/architecture/create_diagrams.py
```

只修改源/SVG、暂不栅格化时可加 `--svg-only`；此模式不更新 PNG 或完整 manifest，旧 PNG 不代表新 SVG，必须随后完成正常重建和视觉检查才可交付。

日期、图版本、机器状态和可见状态标题可通过 `--date`、`--version`、`--status`、`--status-title` 显式指定；两张图的标题用 `--logical-title` / `--deployment-title`，部署区说明用 `--deployment-note`。默认值就是当前已审核检查点。查看 `--help` 获取完整选项；只有对应验收结果确定后才更新状态，不需要手改 SVG。

PNG 由同一份 SVG 通过 librsvg/cairo 渲染为 3000 × 2280，避免另写一套栅格绘图逻辑。生成器检查卡片正文是否溢出，清单记录生成器及 SVG/PNG 的 SHA-256。不同字体或渲染库版本可能产生不同 PNG 字节；修改后仍须查看实际图片，不能只检查哈希。

内容变更时先修改生成器，再重建、查看两张 PNG、核对边界和文字，最后提交生成器、图片和清单。保留 `DATE`、`VERSION`、`STATUS` 与实际实现/验证状态一致，不把「运行验证进行中」自动改成「已验收」。

当前验证边界：构建、服务健康、PostgreSQL 与独立 API/MQTT 链路已验证；浏览器完整分路控制和人工接管因测试定位及受限环境性能未完成，不标为通过。楼层排序在截图后按真实楼层元数据修正，仅重新运行前端测试、类型检查及构建。详见交付验证报告；这些限制不由架构图替代。
