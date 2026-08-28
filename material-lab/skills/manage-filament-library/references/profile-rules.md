# A1 0.4预设编译规则

## 低温增稳板

- 默认打印板为 BIQU Glacier（必趣 冰川），仅映射到Bambu Studio的低温板字段 `cool_plate_temp` 与 `cool_plate_temp_initial_layer`。
- 厂家图示范围：PLA 45–55 °C、PETG 60–75 °C。
- 首轮保守起点使用范围中部：PLA 50 °C、PETG 65 °C；后续实测写入个人校准层。
- 不用Glacier策略覆盖工程板、纹理板或高温板字段；不支持的材料必须停止自动生成，不能猜温度。

## 基线顺序

1. 品牌、产品线、材料和 `Bambu Lab A1 0.4 nozzle` 完全匹配的Bambu Studio内置预设：直接使用。
2. 透明/半透明材料：优先 `Bambu <材料> Translucent @BBL A1`。
3. 哑光材料：优先 `Bambu <材料> Matte @BBL A1`。
4. HF/高速材料：优先 `Bambu <材料> HF @BBL A1`。
5. 其他材料：使用 `Generic <材料> @BBL A1`；没有兼容基线则停止。

## 可覆盖字段

- 密度
- 喷嘴标称温度与范围
- 风扇最小/最大范围
- 最大体积流量、流量比例仅限 `manufacturer_profile`、`bambu_system`、`calibration`

热床范围用于检查基线是否落在厂家范围，不仅凭一个宽范围选择新温度。机械性能、营销速度、烘干、回抽和K/PA不是共享预设覆盖字段。

## 输出状态

- `official_profile_available`：已有精确官方预设，不生成重复文件。
- `draft_needs_calibration`：输出完整JSON/BBSFLMT，必须校准和切片。
- `slice_validated`：Bambu Studio成功加载并切片，不代表打印质量认证。
- `print_calibrated`：用户接受实测校准结果。
