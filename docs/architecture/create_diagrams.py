from pathlib import Path
from html import escape
from PIL import Image, ImageFont
import argparse
import ctypes as ct
import hashlib
import json

VERSION = '3.1'
DATE = '2026-10-01'
STATUS = 'engineering_delivery_with_validation_limits'
parser = argparse.ArgumentParser(description='Render the two current-implementation architecture diagrams and refresh their SHA-256 manifest.')
parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent)
parser.add_argument('--svg-only', action='store_true', help='Write SVG drafts only; leave PNG and release manifest unchanged until full rendering')
parser.add_argument('--date', default=DATE, help='Reviewed checkpoint date, YYYY-MM-DD')
parser.add_argument('--version', default=VERSION, help='Diagram version')
parser.add_argument('--status', default=STATUS, help='Machine-readable manifest status')
parser.add_argument('--status-title', default='工程交付版  ·  实物待验收', help='Visible checkpoint status, not inferred from tests')
parser.add_argument('--logical-title', default='01  平台逻辑架构与数据控制闭环')
parser.add_argument('--deployment-title', default='02  Docker 云边部署与五仓库责任')
parser.add_argument('--deployment-note', default='构建与服务健康检查通过；界面操作和实物验证边界见交付报告')
args = parser.parse_args()
DATE, VERSION, STATUS = args.date, args.version, args.status

OUT=args.output_dir.resolve()
OUT.mkdir(parents=True, exist_ok=True)
GENERATED = []
W,H=3000,2280
FONT='Noto Sans CJK SC'
REG='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
BOLD='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
C={'bg':'#F3F7F9','ink':'#163447','muted':'#587082','line':'#C9D8E0','white':'#FFFFFF','blue':'#1E6594','teal':'#008B80','teallight':'#E8F6F2','bluelight':'#EAF2F9','orange':'#B96621','orangelight':'#FFF3E7','purple':'#68579A','purplelight':'#F1EDF8'}
class Svg:
 def __init__(self, title, num):
  self.a=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">碳迹未来当前软件实现架构。{escape(args.status_title)}。物理执行默认关闭，现场资质与投运另行核验。数据路径、控制路径、运行角色及仓库责任以不同区域表示。</desc><defs>']
  for k in ['teal','orange','blue','muted','purple']:
   self.a.append(f'<marker id="arrow-{k}" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M 0 0 L 12 6 L 0 12 Z" fill="{C[k]}"/></marker>')
  self.a+=['</defs>',f'<rect width="{W}" height="{H}" fill="{C["bg"]}"/>']
  self.txt(80,105,'碳迹未来',66,True)
  self.txt(82,165,'基于 AIoT 云边端协同的高校智慧能碳管理平台',38,False)
  self.txt(84,212,'Powered by CARBENTRA · AIoT Campus Energy Orchestration Platform',25,False,'muted')
  self.rect(2200,57,720,68,'orangelight',None,34)
  self.txt(2560,102,args.status_title,32,True,'orange','middle')
  self.txt(80,285,title,43,True)
  self.txt(2915,284,f'ARCHITECTURE  /  {num}',24,True,'muted','end')
 def rect(self,x,y,w,h,fill='white',stroke='line',r=22,dash=False):
  self.a.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{C.get(fill,fill)}"'+(f' stroke="{C.get(stroke,stroke)}" stroke-width="2"' if stroke else '')+(' stroke-dasharray="10 8"' if dash else '')+'/>')
 def txt(self,x,y,t,size=32,bold=False,color='ink',anchor='start'):
  self.a.append(f'<text x="{x}" y="{y}" fill="{C.get(color,color)}" font-family="{FONT}, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" text-anchor="{anchor}">{escape(t)}</text>')
 def wrap(self,x,y,t,width,size=29,line=44,bold=False,color='muted'):
  font=ImageFont.truetype(BOLD if bold else REG,size)
  yy=y
  for p in t.split('\n'):
   acc=''
   for ch in p:
    if font.getlength(acc+ch)>width and acc:
     self.txt(x,yy,acc,size,bold,color); yy+=line; acc=ch
    else: acc+=ch
   if acc:self.txt(x,yy,acc,size,bold,color);yy+=line
  return yy
 def line(self,x1,y1,x2,y2,color='muted',arrow=False,dash=False):
  self.path(f'M{x1} {y1} L{x2} {y2}',color,arrow,dash)
 def path(self,d,color='muted',arrow=True,dash=False):
  self.a.append(f'<path d="{d}" fill="none" stroke="{C.get(color,color)}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"'+(f' marker-end="url(#arrow-{color})"' if arrow else '')+(' stroke-dasharray="11 9"' if dash else '')+'/>')
 def label(self,x,y,t,color='muted',size=25,anchor='middle',bg='bg'):
  font=ImageFont.truetype(REG,size); width=font.getlength(t)+24
  xx=x-width/2 if anchor=='middle' else x
  self.rect(xx,y-size,width,size+12,bg,None,6)
  self.txt(x,y,t,size,False,color,anchor)
 def card(self,x,y,w,h,title,body,fill='white',color='ink',size=28):
  self.rect(x,y,w,h,fill)
  title_size=34
  while ImageFont.truetype(BOLD,title_size).getlength(title)>w-50 and title_size>27:
   title_size-=1
  self.txt(x+25,y+50,title,title_size,True,color)
  end=self.wrap(x+25,y+98,body,w-50,size,44,False,'muted')
  if end-44>y+h-16: raise ValueError(f'Card text overflows: {title}')
 def foot(self,t):
  self.line(80,2185,2920,2185,'line')
  self.txt(80,2240,t,25,False,'muted')
  self.txt(2920,2240,f'{DATE}  ·  v{VERSION}',24,False,'muted','end')
 def save(self,n):
  (OUT/n).write_text('\n'.join(self.a+['</svg>'])+'\n',encoding='utf-8')
  GENERATED.append(n)

s=Svg(args.logical_title,'01')
# Applications
s.rect(80,325,2200,182,'white')
s.txt(108,370,'统一工作台',34,True)
s.txt(108,413,'校园级使用',26,False,'muted')
s.txt(108,455,'按角色授权',26,False,'muted')
apps=[('运行总览','趋势 · 告警 · 覆盖率'),('校园空间','楼栋 · 楼层 · 房间'),('教室与设备','能力 · 历史 · 联动'),('预测与策略','比较 · 审批 · 调度'),('能碳与报告','电价 · 因子 · 快照')]
for i,(a,b) in enumerate(apps):
 x=370+i*373
 s.rect(x,350,353,132,'bluelight',None,14); s.txt(x+20,397,a,32,True); s.txt(x+20,448,b,25,False,'muted')
s.line(1160,510,1160,562,'blue',True)
s.label(1160,547,'查询 / 操作请求', 'blue',23)
# API
s.rect(80,575,2200,120,'bluelight','line')
s.txt(115,624,'同源 HTTP API  +  SSE 事件通知 / 轮询回退',34,True,'blue')
s.txt(115,668,'生产 HTTPS · Cookie / CSRF · RBAC 与校区范围 · 审计 · 浏览器不直连数据库或 MQTT',29,False,'muted')
s.line(1160,698,1160,742,'blue',True)
# Core
s.rect(80,755,2200,332,'white')
s.txt(110,805,'模块化业务核心',37,True)
s.txt(490,805,'模块边界清晰；共享事务与契约；不按每个模块拆微服务',28,False,'muted')
mods=[('资产与身份','设备 / 负载 / 来源身份\n空间与电气回路分别建模\n时序绑定 · 能力与投运记录'),('教室与运维','时点 / 区间状态重建\n能力通道 / 来源与缺测质量\n手动 / 检修 / 保护优先'),('能源 · 碳 · 成本','有效 Wh 差分 · 总分表排重\n位置法碳 · 分时电量费用\n覆盖率 · 版本与报告快照'),('预测与策略','授权范围内预测任务 / 缓存\n基线与岭回归 · 独立测试\n影子评估 → 批准 → 显式调度')]
for i,(a,b) in enumerate(mods):
 x=110+i*540
 s.card(x,839,510,223,a,b,'teallight',size=27)
# controls
s.line(1160,1090,1160,1127,'orange',True)
s.rect(80,1140,2200,220,'orangelight')
s.txt(110,1189,'受控命令服务',34,True,'orange')
s.txt(540,1188,'权限 · 关键负载 · 手动保持 · 租约 / 时效 · 最短间隔 · 本地故障',28,False,'muted')
states=[('请求已持久化',150),('有序下发',552),('ACK 已接收',953),('关联新观测',1356),('能力与结果判定',1757)]
for i,(a,x) in enumerate(states):
 s.rect(x,1219,350,65,'white',None,12); s.txt(x+175,1263,a,28,True,'orange','middle')
 if i<4:s.line(x+357,1251,x+395,1251,'orange',True)
s.txt(112,1331,'Switch ACK → acknowledged_unverified；无独立触点反馈；另有拒绝 / 失败 / 超时，不等于维修隔离',29,False,'muted')
# state/data foundation
s.rect(80,1420,2200,189,'white')
s.txt(110,1471,'统一持久状态',35,True)
s.txt(485,1470,'PostgreSQL + PostGIS',33,True,'teal')
s.txt(110,1524,'原始遥测是事实源 → 有效区间核算；小时派生修订供预测，可重建、按接收时点复核',31,False,'muted')
s.txt(110,1574,'dirty-hour 队列 → 小时修订 → 范围 / 输入版本绑定的预测缓存；保留原始生成时间，不倒灌未来证据',27,False,'muted')
s.path('M 95 1480 L 45 1480 L 45 928 L 78 928','teal',True)
s.label(55,1394,'读写','teal',24)
# edge path
s.txt(80,1670,'端边接入链路',35,True)
s.card(80,1701,570,340,'端  Plug / Sense B / Switch','Plug：计量 / 输出指示 / 保护\nSense B：有线 5V / I2C / raw 光照\nSwitch：三路通断 / 一份合计电量\n未认证广播不作控制依据\nMCU 固件；RF / 市电待实物验收','white',size=26)
s.card(780,1701,770,340,'边  平台唯一共享 Edge','同源 packages/iot-contract 与具体适配器\nMQTT / 认证 GATT；BLE 默认不启用\nSQLite 收据 / outbox / 新鲜度 / 去重\n有界本地规则：授权租约 + 手动保持\n断网缓存不放大权限；未知不等于无人','teallight',size=27)
s.card(1680,1701,600,340,'平台  接入与后台角色','API：教室状态 / 时序绑定 / 幂等入库\ncontrol：派发 / 回读 / 超时\nsimulation：独立模拟循环\nanalysis：小时修订 / 预测任务\n同一后端镜像，角色独立运行','bluelight',size=27)
s.line(654,1785,775,1785,'teal',True);s.label(713,1762,'MQTT·BLE','teal',22)
s.line(1555,1785,1674,1785,'teal',True);s.label(1615,1762,'HTTPS','teal',23)
s.line(1675,1977,1555,1977,'orange',True);s.label(1615,2010,'命令流','orange',23)
s.line(775,1977,654,1977,'orange',True);s.label(713,2010,'执行端','orange',23)
s.line(1975,1695,1975,1614,'teal',True);s.label(2050,1663,'持久事件','teal',23)
s.path('M 2285 1250 L 2320 1250 L 2320 1950 L 2285 1950','orange',True)
s.txt(90,2110,'遥测与反馈',26,True,'teal');s.line(300,2100,408,2100,'teal',True)
s.txt(475,2110,'受控命令',26,True,'orange');s.line(648,2100,757,2100,'orange',True)
s.txt(840,2110,'物理执行默认 OFF；可选传输不等于已接实机，现场安全、计量与安装另行核验',27,False,'muted')
# right sidebar
s.rect(2380,325,540,785,'purplelight')
s.txt(2410,377,'空间与三维发布',35,True,'purple')
s.txt(2410,419,'作者资产 ≠ 浏览器运行资产',26,False,'muted')
s.card(2410,453,480,160,'唯一作者源','GPKG + Blender\n坐标 / 稳定 ID / 来源','white','purple',25)
s.line(2650,617,2650,645,'purple',True)
s.card(2410,657,480,159,'固定版本发布','GLB + 语义 manifest\n坐标 / 稳定 ID / SHA-256','white','purple',25)
s.line(2650,820,2650,853,'purple',True)
s.card(2410,866,480,210,'运行时资产','先二维 / 全校轻量 LOD1\n129 栋作者外观按需加载\n室内示意图保持独立坐标','white','purple',25)
s.path('M2380 960 L2345 960 L2345 430 L2285 430','purple',True)
s.rect(2380,1140,540,400,'white')
s.txt(2410,1192,'安全与运行边界',34,True)
s.wrap(2410,1250,'本地保护 / 手动保持优先\n物理默认 OFF；模拟可执行\nSIMULATED / REPLAYED / REAL\n未知或陈旧不等于无人\nSense 无 PIR；raw 光照非 lux\n模型与软件测试不代替实物验收',480,27,47)
s.rect(2380,1600,540,510,'white')
s.txt(2410,1652,'贯穿全链路的契约',34,True)
s.wrap(2410,1715,'packages/iot-contract 唯一主源\n身份与关系有效期\n采样 / 接收时间与不确定度\n单位 / 来源 / 新鲜度 / 质量\nSwitch 合计计量只算一次\n软件 ACK 不冒充独立反馈\n空间关系与电气关系分开',480,28,54)
s.foot('当前实现的逻辑视图；架构图不是测试结论，最终验收以对应源码、镜像和实测记录为准')
s.save('01_platform_logical_architecture.svg')

s=Svg(args.deployment_title,'02')
# environments
s.rect(80,335,850,945,'teallight','teal')
s.txt(115,390,'可选边缘传输  /  transport overlay',38,True,'teal')
s.txt(115,432,'默认不启用；运维提供证书、身份与允许列表',28,False,'muted')
s.card(120,468,770,160,'broker / Mosquitto','mTLS 证书身份 → 精确设备主题 ACL\n模板仅绑定 127.0.0.1:18883，非校园网入口','white','teal',27)
s.line(505,632,505,674,'teal',True)
s.card(120,685,770,285,'edge / 平台仓库唯一共享服务','同源 edge/ + packages/iot-contract\nPlug / Switch / Sense 的具体线协议适配\nSQLite 收据 / outbox → HTTPS 提交确认\n默认只转发；虚拟命令需单独 opt-in','white','teal',27)
s.line(505,974,505,1010,'teal',True)
s.card(120,1024,770,160,'持久卷  /  edge_data','SQLite + 原始证据 + outbox + 传输状态\n私钥 / 允许列表外置；卷不可随意删除','white','teal',27)
s.txt(120,1235,'platform-tls：私有 HTTPS 网关；edge 不直连 DB',28,False,'muted')
# cloud
s.rect(1050,335,1870,945,'bluelight','blue')
s.txt(1085,390,'平台服务  /  Docker Compose（Linux containers）',38,True,'blue')
s.txt(1085,432,args.deployment_note,28,False,'muted')
s.card(1090,468,1790,147,'web  /  React + TypeScript + nginx','仅发布 127.0.0.1:8080；生产 HTTPS 反代由运维另设；静态资源 / 同源 API / SSE','white','blue',28)
s.txt(1105,655,'启动顺序：db 健康 → migrate 完成 → api 健康 → worker / analysis / web',26,False,'muted')
s.card(1090,680,650,243,'api / FastAPI 模块化核心','教室状态 / 能力通道 / 时序绑定\n身份 / 核算 / 策略 / 幂等入库\nHTTP 读预测快照 / 去重入队','white','blue',27)
s.card(1780,680,515,243,'worker / 控制与模拟','control：命令 / 核验 / 超时\nsimulation：独立模拟循环\n--role 可分进程；生产停模拟','white','blue',27)
s.card(2335,680,545,243,'analysis / 独立分析角色','小时派生修订 / 有界重建\n预测任务租约 / 授权范围缓存\n同后端镜像，不占控制循环','white','blue',27)
s.path('M 1420 928 L 1420 960 L 2025 960','blue',False)
s.path('M 2025 928 L 2025 993','blue',True)
s.path('M 2600 928 L 2600 960 L 2025 960','blue',False)
s.card(1090,1006,1070,178,'db / PostgreSQL + PostGIS','原始遥测 / 时序绑定 / 命令与审计 / 小时修订 / 预测缓存\n持久卷 database；migrate 一次性迁移成功后启动 API','white','blue',27)
s.card(2200,1006,680,178,'随镜像固定的只读资源','共享合同 / 空间包 / 三类产品模型\n报告快照与权限记录存 PostgreSQL','white','blue',27)
s.txt(1090,1235,'API / worker / analysis 共用后端镜像与私网；没有另设 ingestion 微服务或 Redis',28,False,'muted')
# WAN link
s.line(934,765,1043,765,'teal',True);s.label(988,743,'TLS','teal',24)
s.line(1043,854,934,854,'orange',True);s.label(988,892,'租约','orange',24)
s.txt(957,953,'边缘',24,True,'muted');s.txt(957,990,'发起',24,True,'muted');s.txt(952,1027,'HTTPS',21,True,'muted')
# Device + run requirements
s.card(80,1340,850,211,'三类端设备  /  不容器化','Plug / Switch：ESP32-C3；Sense B：nRF52832\n端侧保护 / 手动保持优先；Sense 只读、无 PIR\nMCU 不运行 Docker；RF / 市电 / 标定待实物验收','white','teal',26)
s.line(505,1335,505,1287,'teal',True)
s.rect(1050,1340,1870,211,'white')
s.txt(1085,1392,'运行底线',35,True)
s.txt(1295,1391,'Secrets 不进镜像或仓库',28,True,'orange')
s.txt(1085,1445,'独立心跳 / 健康检查 · 容器日志 · 持久化 / 备份恢复脚本 · 迁移与回滚说明',29,False,'muted')
s.txt(1085,1500,'生产禁止样例身份 / 自动种子 / 模拟；物理开关 OFF + 放行列表为空；现场资质另行核验',28,False,'muted')
# Repos
s.txt(80,1631,'五仓库维护各自唯一主源',39,True)
s.txt(800,1630,'3 个设备仓库 + 1 个平台仓库 + 1 个空间仓库；合同与资产按版本连接',29,False,'muted')
s.card(80,1670,905,362,'三类设备仓库','carbentra-smart-plug  ·  Plug\ncarbentra-presence-sensor  ·  Sense B\ncarbentra-smart-switch  ·  Switch\n各自硬件 / 固件 / 本地安全与制造资料\n输出具体线协议与产品资产；无独立 Edge','white','teal',29)
s.card(1047,1670,905,362,'平台与共享 Edge 仓库','carbentra-campus-platform\n云端 / 前端 / 教室状态与联动\n唯一 edge/ + packages/iot-contract\n能力 / 事件 / 命令由具体适配器统一\n身份 / 绑定 / 核算 / 授权与调度','white','blue',29)
s.card(2014,1670,906,362,'校园空间与模型仓库','njupt-map\nGPKG / Blender 作者源 / 稳定空间身份\n轻量 LOD1 / 背景 / 129 栋作者外观\n交付：版本化运行包与来源哈希\n平台只消费，不另造几何创作主源','white','purple',29)
s.rect(80,2074,2840,68,'purplelight',None,16)
s.txt(110,2120,'njupt-search：固定空间语义与室内示意参考，借鉴界面风格；未导入当前课表或实际占用',29,False,'purple')
s.foot('当前实现的交付拓扑；可选传输与现场部署分别验收，图中不宣称已接真实设备或已实现节能')
s.save('02_docker_deployment_repo_ownership.svg')


if args.svg_only:
 print(f'Wrote {len(GENERATED)} SVG drafts in {OUT}; PNG/manifest unchanged and require full rendering')
 raise SystemExit(0)

# Render the SVG itself with installed librsvg/cairo; no browser, GPU or network.
def rasterize(svg_path, png_path):
 class Rectangle(ct.Structure):
  _fields_=[('x',ct.c_double),('y',ct.c_double),('width',ct.c_double),('height',ct.c_double)]
 r=ct.CDLL('librsvg-2.so.2'); c=ct.CDLL('libcairo.so.2'); g=ct.CDLL('libgobject-2.0.so.0')
 r.rsvg_handle_new_from_file.argtypes=[ct.c_char_p,ct.POINTER(ct.c_void_p)]; r.rsvg_handle_new_from_file.restype=ct.c_void_p
 r.rsvg_handle_render_document.argtypes=[ct.c_void_p,ct.c_void_p,ct.POINTER(Rectangle),ct.POINTER(ct.c_void_p)]; r.rsvg_handle_render_document.restype=ct.c_int
 c.cairo_image_surface_create.argtypes=[ct.c_int,ct.c_int,ct.c_int]; c.cairo_image_surface_create.restype=ct.c_void_p
 c.cairo_create.argtypes=[ct.c_void_p]; c.cairo_create.restype=ct.c_void_p
 c.cairo_surface_write_to_png.argtypes=[ct.c_void_p,ct.c_char_p]; c.cairo_surface_write_to_png.restype=ct.c_int
 c.cairo_destroy.argtypes=[ct.c_void_p]; c.cairo_surface_destroy.argtypes=[ct.c_void_p]; g.g_object_unref.argtypes=[ct.c_void_p]
 error=ct.c_void_p(); handle=r.rsvg_handle_new_from_file(str(svg_path).encode(),ct.byref(error))
 if not handle: raise RuntimeError(f'Cannot parse SVG: {svg_path}')
 surface=c.cairo_image_surface_create(0,W,H); context=c.cairo_create(surface)
 try:
  viewport=Rectangle(0,0,W,H)
  if not r.rsvg_handle_render_document(handle,context,ct.byref(viewport),ct.byref(error)):
   raise RuntimeError(f'Cannot render SVG: {svg_path}')
  if c.cairo_surface_write_to_png(surface,str(png_path).encode())!=0:
   raise RuntimeError(f'Cannot write PNG: {png_path}')
 finally:
  c.cairo_destroy(context); c.cairo_surface_destroy(surface); g.g_object_unref(handle)

def sha(path):
 return hashlib.sha256(path.read_bytes()).hexdigest()

files=[]
for name in GENERATED:
 svg=OUT/name; png=svg.with_suffix('.png'); rasterize(svg,png)
 with Image.open(png) as picture:
  dimensions=list(picture.size)
 files.append({'name':svg.stem,'png_dimensions':dimensions,'png_bytes':png.stat().st_size,'png_sha256':sha(png),'svg_sha256':sha(svg)})
manifest={
 'version':VERSION,'status':STATUS,'date':DATE,
 'description':'Five-repository software structure with a single platform Edge and IoT contract. Images built; runtime verification is ongoing. Physical actuation is OFF and field qualification is separate.',
 'status_title':args.status_title,'logical_title':args.logical_title,'deployment_title':args.deployment_title,'deployment_note':args.deployment_note,
 'renderer':'librsvg + cairo; SVG and PNG share the same authored source',
 'generator':'create_diagrams.py','generator_sha256':sha(Path(__file__).resolve()),
 'files':files,
}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'Rendered {len(files)} SVG/PNG pairs and manifest in {OUT}')
