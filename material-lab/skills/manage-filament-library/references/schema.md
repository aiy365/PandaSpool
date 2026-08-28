# 数据层级与声明格式

## 三层模型

1. `material_products`：厂家产品/配方。品牌、制造商、产品线、材料、配方或表面、线径、地区、厂家资料和产品通用预设只存一次。
2. `filaments`：颜色库存项。保存商家颜色名、标准色系、颜色SKU/条码、未开封卷、当前一卷在用余量、位置和库存备注。
3. `calibration_runs`：颜色/批次/机器实测。温度塔、流量比例、最大体积流量、K/PA、烘干、环境和测试结果在这里，不改写厂家事实。

`sources`、`claims`、`preset_evaluations`都有`scope_level`：

- `product`：厂家对整个产品发布的资料；`filament_id`必须为空。
- `color_variant`：明确针对某颜色的资料、预设或实测；必须绑定`filament_id`。

## identity.json

```json
{
  "brand": "R3D",
  "manufacturer": "R3D",
  "seller": "国内官方渠道",
  "product_line": "PETG透明系列",
  "material_type": "PETG",
  "variant": "Transparent",
  "color": "透明",
  "diameter_mm": 1.75,
  "sku": "R3D-CLEAR-CN",
  "barcode": null,
  "region": "CN"
}
```

`variant`在当前兼容接口中代表产品配方/表面，不是颜色。条码优先识别颜色商品；缺少条码时使用产品+颜色SKU。不要只按展示名称合并。

## claims.json

```json
[
  {
    "key": "nozzle_temperature_range_c",
    "value": [230, 260],
    "unit": "°C",
    "source": "TDS.pdf",
    "location": "page 2",
    "authority": "manufacturer_tds",
    "scope": {"region": "CN"},
    "review_status": "approved"
  }
]
```

常用字段：`available_colors`（系列可售颜色，不代表库存）、`diameter`、`diameter_tolerance`、`spool_weight`、`nozzle_temperature`、`bed_temperature`、`cooling_fan`、`print_speed`、`drying_temperature`、`drying_time`、`density`、`heat_deflection_temperature`、`melt_flow_index`、`vicat_softening_temperature`、`tensile_strength`、`tensile_modulus`、`elongation_at_break`、`flexural_strength`、`flexural_modulus`、`notched_impact_strength`、`shore_hardness`、`water_absorption`、`filament_flow_ratio`和`filament_max_volumetric_speed`。

字段表不是封闭枚举。遇到厂家独有指标、测试方向或标准时，保留清晰的新 `key`，并把单位、测试条件/方向写入 `unit` 和 `scope`，把页码或图片区域写入来源位置；不得压缩成 `other`。厂家颜色名称原样组成 `available_colors` 数组，库存项再单独维护标准色系。

同一字段值不同即保留冲突。销售页的最高速度不等于最大体积流量；力学参数不直接覆盖切片字段。

## 厂家预设

- `bambu_system`：确实来自 Bambu Studio 系统资源。
- `manufacturer_profile`：厂家或厂家客服提供，来源链可追溯。
- `user_profile`：用户或社区预设，来源待核验。

JSON/BBSFLMT 的 `from=User` 是文件内部身份；即便厂家通过客服提供，也只能记为“厂家提供、用户转存”，不得冒充 `bambu_system`。产品通用预设绑定产品；文件名或配置明确为 Clear/Transparent/White/Black 等颜色时绑定对应颜色。保留原文件、SHA-256、完整来源链、提取字段和警告。

## 库存

`stock_spools`是未开封整卷，`opened_remaining_percent`是至多一卷已开封耗材的估计余量。`1.5`等价于`1卷未开封 + 1卷在用余量50%`，不是任意浮点库存。总当量和总重量均计算得出。
