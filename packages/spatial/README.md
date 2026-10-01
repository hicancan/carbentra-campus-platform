# 空间运行时导入

此包消费 njupt-map 的固定版本运行时及 njupt-search 的身份元数据快照。
原生 GeoPackage、Blender 和观测只在地图仓维护；这里没有第二份可编辑地图。

## 当前范围

- 3 个来源校区，129 个地图建筑，加 7 个没有明确地图关联的搜索建筑，共 136 个登记建筑。
- 41 个楼层、536 个房间族、603 个空间单元。
- 4 个明确建筑关联，563 个明确区域关联，1 个未解决区域，7 组多区域标签关系。
- 公开室内几何为 metadata_only：0 个平面图、0 个室内描摹多边形。保留编号、名称、楼层、来源散列和交叉关系；列表与历史矩阵仍覆盖全部空间。

缺少授权、几何或传感器观测不等于房间不存在、空闲或安全。占用和设备状态由
应用的有时间戳 API 提供；静态包不写入占用、功率或设备位置。

## 本机重建

先从地图仓的锁定 uv 环境导出（完整原生外观可选）：

```powershell
Set-Location ../njupt-map
uv sync --locked
uv run python -m src.runtime.export --native-detail build/native-exteriors
```

在平台根目录，用已经自包含的公开包离线重建到独立目录：

```powershell
uv run python packages/spatial/scripts/build_package.py --map-runtime packages/spatial/dist/map --search-snapshot packages/spatial/dist/search --output D:/Temp/codex/spatial-check/dist
$env:SPATIAL_TEST_DIST='D:/Temp/codex/spatial-check/dist'
uv run python -m unittest discover -s packages/spatial/tests -p 'test_*.py' -v
```

导入新的地图产品时将 --map-runtime 指向地图仓 build/runtime。
若需要重新获取搜索来源，fetch_search_snapshot.py --output 接收独立下载目录；
它检查固定上游快照 c6a20dc3cca30daa6fdd813ae08d881f782e7e3d3e3eda03f402f556ad17222f
的全部散列。build_package.py 在验证后仅投影身份元数据，删除参考图描摹坐标；
新投影有独立内容散列、上游快照散列和各原始元数据来源散列，不能冒充上游原包。
公开投影本身可离线复建，不需要保存参考几何的兼容实现。

不要手改 dist。导入器先在独立 staging 完成校验，才替换认可的生成包；它拒绝
覆盖作者源或任意已有目录。数据库升级必须显式核对移除或重命名的编号，维护
设备绑定历史；导入脚本不自行修改数据库。

## 运行时合同

后端只读挂载 /assets/spatial，经鉴权 API 取得 manifest 后使用包内相对路径。

| 文件 | 作用 |
| --- | --- |
| manifest.json、seed.json | 版本/散列和校区、建筑、楼层、房间族、空间导入记录 |
| crosswalk.json、room-spatial-index.json | 明确来源关联；动态状态只按精确 space_id 及查询时间连接 |
| buildings.local.geojson | 地图建筑的校园局部东/北米制基底 |
| map/campus-lod1.glb、map/buildings/ | 129 个精确 ID 的轻量全校与分栋回退资产 |
| map/detail/buildings/ | 可选原生外观 GLB 和省略项报告；只按请求分栋加载 |
| map/source-regions.json | 564 个来源区域的身份目录，无参考描摹坐标 |
| search/ | 自包含、散列验证的公开身份元数据投影 |

GLB 节点名与 extras.asset_id 是精确地图编号，经 manifest.buildings[].building_id
映射登记建筑，不按显示名或颜色匹配。glTF XYZ=[E,up,-N]。作者原生外观是
明确的运行时投影：不包含高精室内、参考照片、学校标志、贴图或原生作者文件。
完整细节约 357 MB，必须逐栋延迟加载并保留约 0.475 MB 的全校 LOD1 回退。
没有细节 URL 的包不声称原生提取已运行。

## 验证与署名

验证覆盖数量/编号/外键、保留多区域关系、无虚构占用、GLB 拾取映射、所有产物
散列、确定性离线重建、篡改拒绝、源与输出保护、公开包不含参考图描摹坐标。

参见 dist/ATTRIBUTION.json、dist/map/ATTRIBUTION.json 与根 LICENSES.md。
原作署名 hicancan/njupt-map；OSM 数据保留 ODbL 和 © OpenStreetMap contributors。
代码许可证不自动授予第三方图片、平面图或数据库的权利。当前公开包只保留
室内身份元数据，并明确排除未审查参考几何及原始图片。
