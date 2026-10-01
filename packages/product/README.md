# 三类产品工程参考资产

`dist/catalog.json` 将 PLUG、SWITCH、PRESENCE 明确映射到各自的清单、GLB 和 PNG 首图。每种产品使用同一清单结构，包含真实源仓库提交、源文件路径、精确字节哈希、大小、单位和零件身份。源 CAD/ECAD 继续由相应硬件仓库维护。

- Plug：30,337,768 字节源模型的有界量化展示，22,318,016 字节；保留既有零件、材质和独立数值比较记录
- Switch：原始工程 GLB 逐字节发布，三路照明结构参考
- Sense B：原始工程 GLB 逐字节发布，5 V USB-C 有线雷达结构，已移除电池/PIR

图片只表示设计外观，GLB 只在明确点击后载入。图像或模型均不能证明现场型号、安装位置、投运、标定、物理输出或电气安全。未知产品没有默认套用 Plug 模型的路径。

## 唯一发布入口

在平台仓库根目录运行，先提交对应硬件中的模型和首图，避免清单指向不包含这些字节的提交：

```sh
python backend/tools/import_product_asset.py /path/to/carbentra-smart-plug --family PLUG --optimize
python backend/tools/import_product_asset.py /path/to/carbentra-smart-switch --family SWITCH
python backend/tools/import_product_asset.py /path/to/carbentra-presence-sensor --family PRESENCE
```

Plug 的离线量化需要 `tools/` 下锁定依赖，也可用 `--optimized-candidate PATH --reports DIRECTORY` 提升已有且经过三项哈希绑定检查的产物。Sense/Switch 当前无需量化。`tools/validate-khronos.mjs` 对每个展示模型产生独立结构检查记录；结构检查不能替代真实浏览器性能测试。

## 受保护的读取接口

三个接口都必须明确提供 `family=PLUG|SWITCH|PRESENCE`：

- `/api/v1/assets/product/manifest?family=…`
- `/api/v1/assets/product/hero?family=…`
- `/api/v1/assets/product/model?family=…`

服务端校验映射路径、文件大小与哈希，所有接口需要登录；浏览器同时验证所选产品身份与模型 SHA-256。不同产品之间切换会卸载原模型，再由用户决定是否载入。

当前文件只在本项目中交付。原始第三方组件资料、地图和图形素材的权利并未因导入而改变，外部发布前应按相应来源条款复核。
