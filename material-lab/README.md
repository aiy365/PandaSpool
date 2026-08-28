# PandaSpool 耗材实验室

PandaSpool Material Lab 是一个独立、私有的 3D 打印耗材管理后台。它把“产品系列 × 商家颜色名”的库存、供应商网页、PDF、图片和客服原话整理成可追溯档案。库存只记录未开封整卷和当前一卷在用余量，不跟踪每次打印消耗。

当前运行架构只有四部分：

- Caddy：HTTPS 与反向代理。
- Python 标准库单体服务：同源 REST 接口、登录会话和静态资源服务。
- SQLite：唯一运行数据库，事务化保存档案和库存流水。
- React + shadcn/ui：编译后的静态管理后台。

不依赖外部数据库或云存储。私有 PDF、图片、预设和切片产物保存在服务器本地文件系统。

## 产品范围

- 颜色矩阵、卡片/表格耗材库、补货清单和耗材详情页；默认进入颜色矩阵。
- 商家颜色名原样保留，同时归入可人工修正的标准色系。
- 库存明确拆分为“未开封整卷”和“当前一卷在用余量”；Excel 中的 `1.5` 导入为 `1 卷未开封 + 1 卷开封余量 50%`。
- 首页以“从截图智能建档”为首要入口：上传商家参数图后由服务器端 Tesseract 识别，自动填入草稿并保留原图；确认后一次性建立耗材档案、厂家声明和库存记录。
- 网页新增、编辑、搜索和盘点耗材；枚举字段统一为“已有值下拉 + 自定义输入”，不再混用浏览器 datalist 建议框。
- 在耗材详情页上传厂家/销售页/客服截图、PDF、预设或个人记录；可同时保存客服原话、结构化参数和“直接使用默认参数”等采用决定。
- 入库、盘点、修正与最近操作撤销；不按打印任务自动扣减库存。
- 目标库存、低库存阈值、存放位置和备注。
- 一键盘点评测检查颜色归类、资料缺口和冲突字段，并可复制面向 AI 的紧凑 JSON。
- `/api/ai/inventory` 提供鉴权后的低令牌库存读取；`/openapi.json` 与 `/llms.txt` 公开描述接口，但不公开私有库存。
- Bambu Lab A1 0.4 mm 可追溯预设生成；0.6 mm 和 0.2 mm 暂不自动开放。

## 安装与本地启动

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\pandaspool-material.exe database-init
```

双击 `启动耗材看板.cmd`，或运行：

```powershell
$env:PRINTPILOT_DATA_DIR = "$env:LOCALAPPDATA\PandaSpool\MaterialLab"
pandaspool-material dashboard
```

看板只监听 `127.0.0.1`。视图显隐、宽度、排序和筛选保存在当前浏览器；业务数据保存在 SQLite。生产服务器需要安装 `tesseract`，并提供 `chi_sim` 与 `eng` 语言包；没有识别组件时仍可使用手动建档和原图上传。

## 数据目录

生产环境只需设置：

```text
PRINTPILOT_DATA_DIR=/var/lib/pandaspool-material-lab
```

目录内容：

```text
material-lab.sqlite3   唯一运行数据库
files/                 原始证据和生成产物
dashboard-auth.json    生产用户名和密码哈希
backups/               本地完整备份
```

SQLite 自动启用外键、WAL、繁忙等待和版本化迁移。库存变动与当前卷数在同一事务内提交。

## 常用命令

```powershell
pandaspool-material stage --identity identity.json --claims claims.json --source document.pdf
pandaspool-material commit staging/<id>/manifest.json --approved
pandaspool-material profile-build staging/<id>/manifest.json --nozzle 0.4 --plate glacier
pandaspool-material slice-smoke --profile profile.json --input model.3mf --report profile-report.json
pandaspool-material calibration-record staging/<id>/manifest.json --input calibration.json
pandaspool-material inventory-list
pandaspool-material inventory-set --filament-id <uuid> --spools 6 --opened-percent 50 --approved
pandaspool-material inventory-adjust --filament-id <uuid> --delta -1 --approved
pandaspool-material inventory-import-xlsx "C:\库存盘点.xlsx"
pandaspool-material inventory-import-xlsx "C:\库存盘点.xlsx" --approved
pandaspool-material inventory-ai-export --pretty
pandaspool-material database-init
pandaspool-material backup --output-dir backups
pandaspool-material restore backups/<archive>.tar.gz --approved
```

`inventory-import-xlsx` 默认只预览，带 `--approved` 才写库；相同工作簿重复导入是幂等的。`stage` 只生成待审核资料；`commit` 才写入 SQLite 和私有文件目录。预设与校准分别使用 `profile-commit`、`calibration-commit` 建档。

## 备份与恢复

`backup` 使用 SQLite 在线备份接口生成一致性快照，将数据库和 `files/` 打成带 SHA-256 清单的压缩包，不需要停止看板。

`restore` 会先检查压缩包路径安全、逐文件哈希、SQLite 完整性和必要表结构；全部通过后才覆盖当前数据，失败时恢复旧副本。恢复属于破坏性操作，必须显式传入 `--approved`；生产环境恢复前必须先停止看板并取得人工确认。

建议由 systemd timer 每天备份，保留 30 份，并定期下载一份到服务器之外。备份中包含私有资料，不应放入 Git 或公开网盘。

## 生产部署

生产模式：

```bash
pandaspool-material dashboard \
  --port 8765 --no-browser \
  --public-origin https://3d.bstccc.cn \
  --auth-file /var/lib/pandaspool-material-lab/dashboard-auth.json
```

- Python 仅监听 `127.0.0.1:8765`，Caddy 提供 HTTPS。
- systemd 使用独立低权限用户，只有 `/var/lib/pandaspool-material-lab` 可写。
- 密码使用随机盐的 scrypt 哈希；修改账号后注销全部现有会话。
- Caddy、systemd 和备份定时器模板位于 `deploy/`。

## 前端开发

```powershell
cd dashboard
npm install --include=dev
npm run build
```

构建结果写入 Python 包内的 `dashboard_dist`，生产服务器不运行 Node.js。

## 工艺原则

- 原始证据、厂家声明、拓竹基线和个人校准分层保存。
- 图片识别只生成“待确认草稿”，不会直接写库存或覆盖厂家事实；没有SKU/条码时生成 `PP-AUTO-*` 本地内部标识，明确标记为待补充。
- 当前网页不把实际库存接入 3MF 转换器，也不生成材料、喷嘴或切片参数推荐。
- 冲突值并存，不静默覆盖；完全匹配时优先使用 Bambu Studio 内置预设。
- 最大体积流量只接受官方/厂家机器预设或实测，不从“最高打印速度”推导。
- 低温增稳板默认使用 BIQU Glacier（必趣 冰川）：PLA 50 °C、PETG 65 °C。
- 输出是打印候选方案，不是材料认证、承重或疲劳寿命保证。

仓库根部 `plugin.json` 遵循 Agent Plugins 1.0.0；核心工作流位于 `skills/manage-filament-library/`。许可证为 MIT。
