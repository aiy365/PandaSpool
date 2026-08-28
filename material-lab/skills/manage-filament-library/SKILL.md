---
name: manage-filament-library
description: 将3D打印耗材供应商网页、PDF/TDS/SDS、截图、JSON或BBSFLMT预设建成带来源和冲突的私有SQLite档案；优先匹配Bambu Studio官方配置，为Bambu Lab A1 0.4 mm生成可追溯的耗材预设，记录校准，并维护按耗材聚合的库存盘点。用户提到耗材建档、耗材数据库、供应商资料、材料预设生成、Bambu耗材JSON/BBSFLMT、耗材库存盘点、增加或减少库存、R3D/SUNLU/Polymaker/Panchroma等材料资料或校准历史时使用。
---

# 耗材建档与预设生成

## 工作流

1. 先确定数据层级：`产品（厂家事实与系列颜色目录）→ 颜色库存（盘点）→ 颜色/批次实测（温度塔、流量、K/PA）`。系列可售颜色使用产品级 `available_colors` 声明维护，不得因此创建库存；只有明确写明颜色差异的资料或实测才绑定颜色。
2. 已有产品补充商家截图时，首选产品详情的“资料收件箱”：批量上传PNG/JPG/WebP原图，服务器私有留存并标记 `pending_manual_review`，不实时识图、不创建声明、不修改预设。用户明确要求处理已上传资料时，直接在原来源上追加核对后的声明并标记 `processed`，不重复上传、不再生成 stage/review/manifest 三件套。新产品建档才使用“从截图智能建档”，识别结果仍必须由用户确认后再写入。
3. 收集品牌、产品线、材料类型、地区、颜色SKU/条码，以及用户提供的原始网页、PDF、图片和厂家预设。SKU/条码未知时先用本地 `PP-AUTO-*` 内部标识建档，不得阻塞资料归档，也不得把内部标识当成供应商身份。
4. 只有新产品、外部批量文件或跨来源冲突需要离线暂存时，才按 [数据与声明格式](references/schema.md) 准备 `identity.json` 和逐字段 `claims.json`；已入收件箱的资料走上面的快速路径。
4. 运行本地暂存，不写正式档案：

```powershell
python scripts/run_material_lab.py stage `
  --identity "C:\绝对路径\identity.json" `
  --claims "C:\绝对路径\claims.json" `
  --source-metadata "C:\绝对路径\source-metadata.json" `
  --source "C:\绝对路径\TDS.pdf" `
  --source "https://manufacturer.example/product"
```

5. 阅读输出的 `review.md` 和 `manifest.json`。保留地区、版本和批次冲突；不要用单一“置信度”覆盖异议。
6. 写入SQLite档案和私有文件目录前，说明文件范围和会写入的数据，并取得用户当次确认。确认后运行：

```powershell
python scripts/run_material_lab.py commit "C:\绝对路径\manifest.json" --approved
```

7. 生成预设前读取 [预设编译规则](references/profile-rules.md)。当前用户的低温增稳板统一使用BIQU Glacier（必趣 冰川），然后运行：

```powershell
python scripts/run_material_lab.py profile-build "C:\绝对路径\manifest.json" --nozzle 0.4 --plate glacier
```

8. 若报告建议使用Bambu Studio内置预设，不生成重复文件。若生成草案，检查字段来源，再使用 `slice-smoke --report <profile-report.json>` 做真实切片并回写验证状态；打印前仍需人工预览。
9. 流量比例、K/PA、最大体积流量或批次结果使用 `calibration-record` 单独记录。校准不能改写厂家声明。

网页详情页也可以直接添加厂家资料：选择资料类型、填写来源和采用决定，上传不超过8MB的截图/PDF/预设，并把客服原话与明确写出的温度、热床等参数分开保存。客服说“按照默认参数打就行”应记录为原话和 `use_default_profile` 决策，不得擅自转换成数值参数。

产品资料收件箱与“添加厂家资料”不同：收件箱只接收单张不超过8MB的PNG/JPG/WebP，每次最多10张；每张原图按SHA-256去重，保存在私有文件目录，且不生成占位声明。后续人工处理必须保留原始来源，提取结果另写为可审核声明。

字段体系保持开放：常见打印、物理和机械性能使用规范键；遇到未覆盖的数据时原样保存新的 `claim_key`、单位、适用范围、来源位置和原文，不得丢弃或统称为“其他”。系列颜色名称按厂家原名维护，另由库存颜色记录映射标准色系。

厂家预设应从产品详情页上传：JSON/BBSFLMT 先展开继承并解析 A1 0.4 mm 白名单字段，再选择“产品通用”或“颜色专用”。先在本机 Bambu Studio 安装目录按品牌与完整型号精准查找；有匹配时以 `bambu_system` 建档并与厂家声明比较，没有精准匹配时不得用相近型号冒充。用户明确说明由厂家提供时使用 `manufacturer_profile`，但必须保留文件内部的 `from` 字段和“厂家提供、用户转存”等来源链；`from=User` 不得标为拓竹系统预设。透明、白色等预设存在流量比例或密度差异时分别绑定颜色。

## 快速交付

- 页面或后端改动只运行受影响的定向测试；前端在交付前构建一次。除非出现失败、数据库迁移、认证或高风险改动，不重复全量测试、截图审查和多轮构建。
- 同一批生产资料整理、预设同步和部署可以合并为一次确认；确认后一次写入、一次部署、一次健康检查。
- 预设仅用于归档和参数比较时不做切片烟雾测试；只有生成了准备实际打印的新预设文件时才切片验证。

## 库存盘点

- 使用 `inventory-list` 查看每种耗材的未开封卷数、当前一卷在用余量、库存当量和库存状态。
- 库存小数不是通用浮点库存：`1.5` 必须解释为 `1 卷未开封 + 1 卷开封余量 50%`。每种颜色最多维护一卷“在用卷”。
- 用户给出盘点后的准确数量时，使用 `inventory-set --filament-id <uuid> --spools <未开封数量> --opened-percent <在用卷余量> --approved`。
- 用户明确要求增加或减少时，使用 `inventory-adjust --filament-id <uuid> --delta <正负整数> --approved`。
- 用户给出“颜色 × 产品系列”的Excel库存盘点表时，先运行 `inventory-import-xlsx <文件>` 预览，确认后再加 `--approved` 导入；供应商颜色名原样保留，另存标准色系。
- 写入前展示修改前数量、调整量和修改后数量；不得让库存小于0。
- 只维护聚合卷数与一卷开封余量，不创建单卷实体、打印消耗流水或自动扣减。
- 需要 AI 阅读时使用 `inventory-ai-export` 或鉴权后的 `/api/ai/inventory`；不要让 AI 抓取完整网页。图片识别结果只能是候选草稿，必须通过确定性校验和用户确认后写入。
- 当前不把库存接入3MF转换器，不根据库存生成材料、喷嘴或切片参数推荐。

## 安全边界

- v0.1只处理Bambu Lab A1 0.4 mm；0.6和0.2必须明确拒绝。
- 不从“最高打印速度”推导最大体积流量，不从销售页推导K/PA。
- 最大体积流量和流量比例只接受Bambu系统预设、厂家机器预设或实测校准。
- 含糊的回抽、力学强度和烘干信息不直接覆盖机器参数。
- 数据库和私有资料必须保存在`PRINTPILOT_DATA_DIR`；不得提交到Git或公开目录。
- 执行数据库迁移、恢复、发布、部署、公开资料或导入原始供应商文件前必须取得用户确认。
- 设置或增减库存属于正式数据写入，必须取得当次确认并传入 `--approved`。
- 输出是制造候选，不是承重、疲劳寿命或安全认证。
