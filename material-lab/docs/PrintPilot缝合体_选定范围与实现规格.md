# PrintPilot 缝合体：选定范围与实现规格

| 项 | 内容 |
|---|---|
| 日期 | 2026-08-18 |
| 性质 | 按你勾选的功能收口，作为后续实现的唯一范围 |
| 前序调研 | `docs/PrintPilot_Mars_A1_易微联_调研报告.md` |
| 生产站 | `https://3d.bstccc.cn/` |
| 硬约束 | 不影响 Handy / Studio；**不做**第三方打印控制（暂停 / 加热 / 发任务） |

本文只写「要做的东西怎么落地」。未勾选的 Mars 订单、自动扣重、关 A1 电源，一律不进范围。

---

## 1. 产品一句话

网页上同时能做四件事：

1. 查这款料的参数、资料、冲突，并做横评。
2. 人工记下架子上还有几卷（未开封 + 是否已开封，**不要余量 %**）。
3. 只读看 A1：热床 / 喷嘴温度、层数、进度、剩余时间、阶段。
4. 看萤石监控，并一键开易微联补光灯 / 空气净化器。仓内外环境、人体感应、舱门用低成本开源硬件补上（A1 本身没有腔体）。

控制权分工：

| 谁 | 只做什么 |
|---|---|
| Handy / Studio | 发任务、暂停、调温、换色 |
| PrintPilot 网页 | 档案、盘点、只读机台、监控、补光、净化器、环境 |
| 易微联 App | 继续配网、改名、升级；网页也可开关补光和净化器 |
| 萤石云 App | 继续配网、回放、云存储；网页只做预览 |

---

## 2. 你选定的功能（已收口）

### 2.1 耗材实验室（主产品，语义有一处改动）

| 要做 | 说明 |
|---|---|
| 这款料是什么参数 | 厂家 / 商家声明，开放字段 |
| 整理上传资料 | 截图 / PDF / 原话 / 预设，SHA-256 去重，OCR 只出草稿 |
| 架子上还有几卷 | **未开封整卷数 + 是否有开封卷**。不要 `opened_remaining_percent` |
| 不按任务扣 | 盘点账，不是流水账 |
| 分层与冲突 | 厂家 / 商家 / Studio 预设 / 个人实测并存，不覆盖 |
| **耗材参数横评 / 分析** | 新产品能力：跨产品、跨来源对比喷嘴温、热床、风扇、密度、流量、K/PA、力学等 |

库存新语义：

```text
某颜色 = 未开封 N 卷 + 开封 0 或 1 卷
当量卷数 = N + (开封 ? 1 : 0)     // 开封卷按「有一卷在用」计，不再估 50%
1.5 这种小数导入不再作为一等公民
```

现网 SQLite 里的 `opened_remaining_percent` 上线前要迁移：有余量则视为「已开封」，百分比丢弃或只进历史备注。**实现前必须你确认迁移规则。**

### 2.2 机台只读（绑拓竹账号，云 MQTT）

只订 `device/<SN>/report`，禁止封装 pause / print / 调温。

展示字段（A1）：

- 热床实际 / 目标温度
- 喷嘴实际 / 目标温度
- 当前层 / 总层
- 进度 %
- 剩余时间
- 阶段（打印中 / 暂停 / 完成 / 空闲 / 故障等原始 stage）

可选附属（实现时顺手留下，页面可折叠）：AMS Lite 四槽只读、HMS 错误。不作为本期验收必选项。

### 2.3 易微联（可控制，但对象收窄）

| 设备 | 做 | 不做 |
|---|---|---|
| 补光灯 | 网页开关；和监控页放一起 | — |
| 空气净化器 | 网页开关（能读档位就读，不能就通断） | — |
| A1 市电 | **不做** | 你已明确不是用来关 A1 |

打印开始 / 结束是否自动开灯、开净化器：做成**可选场景**，默认关，由你在网页里打开。

### 2.4 监控

目标：网页里看画面 + 开补光。

优先级：

1. **家里看**：萤石本地 RTSP → D2 上 go2rtc → 浏览器 WebRTC（低延迟，不占云上行）。
2. **外出看 `3d.bstccc.cn`**：萤石开放平台 EZUIKit / HLS（流量走萤石 CDN，不穿 D2、不穿 6 Mbps 云机）。
3. **退路**：任意 `rtsp://` 自定义设备，走同一套 go2rtc，页面不绑死萤石品牌。

### 2.5 低成本环境 + 人体感应（A1 没有的，自己补）

A1 是开放机，没有原生腔体 / 仓温 / 舱门 / 主副灯。这些全部定义为 **「仓内 / 仓外」两个区域的外挂传感器**，假定你有外罩或至少有「机位附近」和「车间」两个空间。

| 量 | 仓内 | 仓外（车间） | 做法 |
|---|---|---|---|
| 温度 | 要 | 要 | SHT30 / SHT40 |
| 湿度 | 要 | 要 | 同上 |
| 空气质量 | 建议 | 要 | 仓外 PMS5003（PM2.5）；仓内可选 VOC |
| 人体感应 | 一般不要对着喷头 | **要** | LD2410C 毫米波（优于普通 PIR） |
| 舱门 | 要 | — | 磁簧门磁 |
| 主灯 / 副灯 | 补光灯 = 易微联 | 车间灯若已有易微联可后加 | 不接 A1 协议 |
| 腔体存在 | 用「舱门关闭」近似 | — | 不做复杂腔体逻辑 |

---

## 3. 萤石能不能连进网页：结论

**能。** 两条路都成立，建议两条都做，按访问位置自动选。

### 3.1 本地 RTSP（局域网，推荐当「家里实时画面」）

萤石 App：`我的 → 工具 → 局域网设备预览 → 选中设备 → 设置 → 更多设置 → 本地服务`，打开 RTSP。

常见地址（验证码是机身 6 位，不是账号密码）：

```text
rtsp://admin:<验证码>@<摄像机IP>:554/h264/ch1/main/av_stream
rtsp://admin:<验证码>@<摄像机IP>:554/h264/ch1/sub/av_stream      # 辅码流，D2 更轻松
rtsp://admin:<验证码>@<摄像机IP>:554/11                         # 部分型号
```

浏览器**不能**直接播 RTSP。D2（MT7621A / mipsel）上跑官方二进制 [go2rtc_linux_mipsel](https://github.com/AlexxIT/go2rtc)，把 RTSP **拷流**成 WebRTC / MSE，不转码。

- 只要拷流、不开 ffmpeg 转码，512 MB 的 D2 扛一路辅码流没问题。
- 网页用 go2rtc 的 `stream.html` 或 WebRTC 组件，套在 PrintPilot 登录后的监控页。
- 补光灯按钮和画面同一卡片：先开灯，再看画面。

限制：你人在外网时，浏览器连不上家里 go2rtc，除非做内网穿透。**不要把 RTSP 密码映射到公网 554。**

### 3.2 萤石云开放平台（外出看 `3d.bstccc.cn`）

- 注册 <https://open.ys7.com/>，创建应用，拿到 `appKey` / `appSecret`。
- 用账号授权或把摄像机加到该应用下，服务端换 `accessToken`。
- 网页用官方 **EZUIKit-JS** 播 `ezopen://open.ys7.com/<序列号>/1.hd.live`，或接口取 HLS / FLV。
- 视频从摄像机 → 萤石云 → 用户浏览器，**不经过 yby，也不经过 D2**。云机只下发短时 token。
- 试用套餐常见限制：取流码率上限约 1 Mbps，超了会断后一路。个人自用一般够。HLS 互联网直播地址有的套餐要按路付费（量级约每月数元），先走 ezopen + UIKit 试用。
- 加密设备播流要设备验证码；**不要为了图省事在公网关加密**。token 只放服务端，页面必须先登录 PrintPilot。

### 3.3 自定义 RTSP（退路，接口按这个设计）

监控源在系统里就是一条记录：

```text
camera
  id, name, zone          # enclosure | room
  kind                    # ezviz_cloud | ezviz_rtsp | generic_rtsp
  rtsp_url                # 仅存在 D2 / 服务端，不进前端仓库
  ezviz_serial, channel
```

页面不写死萤石。以后换海康、小米、任意 IPC，只要有 RTSP，就还是 go2rtc。

### 3.4 明确不要的做法

| 不要 | 原因 |
|---|---|
| 把家里 RTSP 经 D2 推到 yby 再给用户 | 6 Mbps 上行 + 转码，D2 和云机都亏 |
| 公网裸映射 554 | 验证码等于密码 |
| 未登录的公开直播页 | 车间画面是隐私 |
| 在 D2 上 ffmpeg 转 1080p | MT7621A 会打满 |

---

## 4. 部署拓扑（按你指定的两台机器）

```text
                    Handy / Studio
                          │
                     拓竹云（官方）
                          │
                     A1 保持云模式
                          │ 只读 report
                          ▼
┌────────────────── 家里局域网 ──────────────────┐
│  萤石摄像机 ──RTSP──► Newifi D2                 │
│  ESP 仓内/仓外 ──MQTT──► D2 mosquitto            │
│  易微联补光 / 净化器 ──易微联云（App 仍可用）    │
│                                                 │
│  D2 职责：                                      │
│   · go2rtc（RTSP→WebRTC，仅局域网 / 可选隧道）  │
│   · mosquitto + 小转发进程                      │
│   · 把环境 JSON、摄像机在线、A1 若走本地备份     │
│     用 HTTPS 推到 yby                           │
└───────────────────────┬─────────────────────────┘
                        │ 家里已有端口映射或反代
                        ▼
              腾讯云 yby  159.75.227.95
              Caddy :443  3d.bstccc.cn
              PrintPilot（呈现 + 档案 + 会话）
              · 拓竹云 MQTT 只读（主路径，不依赖 D2）
              · 易微联云 API 开关补光 / 净化器
              · 萤石 accessToken + EZUIKit（外出预览）
              · 收 D2 上报的仓内外环境 / 人体 / 舱门
```

**为什么拓竹 MQTT 主路径放 yby：** 打印机状态在拓竹云上，云机直连更稳，D2 重启不影响机台页。D2 专管「只有局域网才有的东西」：RTSP、传感器。

D2 内存预算（512 MB）：

| 进程 | 约 |
|---|---|
| OpenWrt 本身 | 40–80 MB |
| mosquitto | 2–5 MB |
| go2rtc 一路拷流 | 15–40 MB |
| 转发小程序（Go） | 10–20 MB |
| 余量 | 留给路由 |

不在 D2 上装 HA、Node 大盘、ffmpeg 转码、Python 看板。

---

## 5. 低成本硬件：人体感应 + 仓内外环境

### 5.1 原则

- 协议开放：**MQTT**（JSON），D2 当 broker。不绑 HA，不绑易微联账号。
- 固件：电脑上编好再刷，推荐 ESPHome 或 Arduino + PubSubClient。D2 不跑编译器。
- 供电：仓外 USB 5V；仓内尽量 USB，远离热床线。
- 两块板，分区清楚，线短、好修。

### 5.2 推荐 BOM（约 80–130 元就能把主量做齐）

**板 A · 仓内（enclosure）**

| 件 | 型号 | 约价 | 作用 |
|---|---|---|---|
| 主控 | ESP32-C3 SuperMini | 8–12 | WiFi + MQTT |
| 温湿度 | SHT30 或 SHT40 | 5–10 | 仓温 / 仓湿（你要的「腔体/仓温」） |
| 舱门 | 磁簧 + 磁铁 | 1–2 | 开/关 |
| 可选 | SGP40 / SGP41 | 15–25 | 仓内 VOC（树脂/ABS 味） |
| 可选 | 1 路继电器或直接用易微联 | — | 仓内灯；**优先用已有易微联补光，板子不要再加继电器** |

**板 B · 仓外 / 车间（room）**

| 件 | 型号 | 约价 | 作用 |
|---|---|---|---|
| 主控 | ESP32-C3 SuperMini | 8–12 | WiFi + MQTT |
| 温湿度 | SHT30 / SHT40 | 5–10 | 室温 / 室湿 |
| 人体 | HLK-**LD2410C** | 12–18 | 有人/无人、距离；比 HC-SR501 强，坐着不动也在 |
| 空气 | PMS5003 / PMSA003 | 25–40 | PM1/2.5/10，给净化器一个对照 |
| 可选 | SCD40 | 40–55 | CO2，以后再说 |

**不要用 HC-SR501 当主方案。** 打印机运动、热床辐射容易误报；人坐着看机也会「消失」。LD2410C 是目前最便宜的「存在」方案。

易微联人体传感器也能用，但协议不开放、上报慢。有现成的可以后接，**新买走 ESP+LD2410C**。

### 5.3 开放接口（D2 mosquitto，实现就按这个）

主题前缀：`printpilot/v1/{zone}/{kind}`  
`zone` = `enclosure` | `room`  
保留 `retain=true` 的最新一条，qos 0 即可。

```json
{
  "ts": 1776500000,
  "zone": "enclosure",
  "online": true,
  "temperature_c": 31.2,
  "humidity_rh": 42.0,
  "door": "closed",
  "voc_index": 120,
  "firmware": "enc-0.1.0"
}
```

```json
{
  "ts": 1776500000,
  "zone": "room",
  "online": true,
  "temperature_c": 26.4,
  "humidity_rh": 55.0,
  "presence": true,
  "presence_distance_cm": 180,
  "pm1": 8,
  "pm25": 12,
  "pm10": 18,
  "firmware": "room-0.1.0"
}
```

发现与健康：

```text
printpilot/v1/enclosure/state
printpilot/v1/room/state
printpilot/v1/{zone}/lwt          // offline
```

D2 转发进程每 5–10 秒（或数值变化超过阈值时）打包推 yby：

```http
POST https://3d.bstccc.cn/api/ingest/env
Authorization: Bearer <D2 设备令牌>
```

yby 只信这个令牌，不把 MQTT 端口敞到公网。

### 5.4 网页怎么呈现

机台页两列：

```text
仓内                         仓外
温度 / 湿度 / 门              温度 / 湿度 / PM2.5
（门开红色）                  有人 / 无人
补光灯 ●                     空气净化器 ●
萤石画面（可点开灯再看）
A1 热床 / 喷嘴 / 层数 / 进度 / 剩余 / 阶段
```

场景（默认关，你自己打开）：

- 有人 + 打印中 → 建议开补光（不自动断净化器）。
- PM2.5 超标 → 飞书提醒，可选自动开净化器。
- 舱门在打印中被打开 → 飞书提醒（只提醒，不暂停打印机）。

### 5.5 ESPHome 骨架（仓外，实现时按此刷）

```yaml
esphome:
  name: pp-room
esp32:
  board: esp32-c3-devkitm-1
wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_pass
mqtt:
  broker: 192.168.x.x          # D2
  username: !secret mqtt_user
  password: !secret mqtt_pass
  topic_prefix: printpilot/v1/room
  birth_message: { topic: printpilot/v1/room/lwt, payload: online }
  will_message:  { topic: printpilot/v1/room/lwt, payload: offline }

i2c:
  sda: GPIO8
  scl: GPIO9
uart:
  tx_pin: GPIO4
  rx_pin: GPIO5
  baud_rate: 256000

sensor:
  - platform: sht3xd
    temperature: { name: "temperature_c" }
    humidity: { name: "humidity_rh" }
  - platform: pmsx003
    type: PMSX003
    pm_2_5: { name: "pm25" }
    pm_1_0: { name: "pm1" }
    pm_10_0: { name: "pm10" }

ld2410:
binary_sensor:
  - platform: ld2410
    occupancy:
      name: "presence"
sensor:
  - platform: ld2410
    moving_distance:
      name: "presence_distance_cm"
```

仓内板去掉 LD2410 / PMS，加上 GPIO 门磁（`binary_sensor.gpio`，`device_class: door`）。

---

## 6. 软件模块怎么切（仍是一台 yby 应用）

不要新开微服务。yby 上还是 PrintPilot 单体，多几个包：

| 模块 | 职责 |
|---|---|
| `catalog` | 产品 / 颜色 / 资料 / 声明 / 预设 / 实测 / **横评** |
| `inventory` | 未开封 + 开封布尔，盘点流水，不要按任务扣 |
| `bambu_cloud` | 账号绑定、Token 刷新、只读 MQTT、状态快照 |
| `ewelink` | 设备列表、补光 / 净化器开关、状态 |
| `camera` | 萤石 token、自定义 RTSP 元数据；真正的流不经本模块转发 |
| `env_ingest` | 收 D2 环境包，存时序（SQLite 够用，按小时降采样） |
| `notify` | 飞书：打印结束 / 失败、舱门、PM 超标（可后做） |

前端页面：

1. 库存 / 颜色矩阵（改库存语义，强化手机盘点）
2. 产品详情（资料 + 冲突）
3. **横评**（多选产品或颜色，表格式对比各来源参数）
4. **机台**（A1 只读 + 仓内外 + 监控 + 补光 + 净化器）
5. 设置（拓竹绑定、易微联绑定、摄像机、D2 令牌）

横评最小可用：

- 行：喷嘴温、热床、风扇、密度、流量比、最大体积流量、K/PA、拉伸强度…
- 列：产品 A 厂家 / 产品 A Studio / 产品 A 实测 / 产品 B …
- 冲突格标色。没有的值空着，不编造。

---

## 7. 技术栈（收窄后）

| 层 | 选定 |
|---|---|
| yby | 继续 Caddy + systemd；后端收到 FastAPI + Pydantic + SQLite；前端 React + shadcn |
| 拓竹 | yby 上 `paho-mqtt` 连 `cn.mqtt.bambulab.com:8883`，只订 report |
| 易微联 | 酷宅开放平台云 API（E1）。补光 / 净化器不刷机 |
| 萤石外出 | open.ys7.com + EZUIKit-JS |
| 萤石家里 | D2 `go2rtc_linux_mipsel` + 本地 RTSP |
| 退路摄像 | 同一 go2rtc，自定义 RTSP |
| 传感器 | ESP32-C3 + MQTT → D2 mosquitto → HTTPS ingest |
| 通知 | 飞书 webhook，第二期 |

不引入：Docker、HA、PG、Redis、Klipper、第三方打印控制 API。

---

## 8. 建议实施顺序

| 期 | 内容 | 你就能用什么 |
|---|---|---|
| P0 | 库存语义改成「未开封 + 开封」、横评页、移动端盘点 | 耗材实验室更好用 |
| P1 | 拓竹云 MQTT 只读机台页 | 手机看温度和进度 |
| P2 | 易微联补光 + 净化器 + 监控页（先接萤石云 UIKit） | 外出开灯看画面 |
| P3 | D2 go2rtc + 本地 RTSP | 家里低延迟画面 |
| P4 | 两块 ESP：仓内外温湿度、门、人体、PM2.5 | 环境补齐 |
| P5 | 可选场景和飞书 | 人走、门开、空气差时提醒 |

P0 不依赖任何外设。P2 只要现有萤石账号和易微联设备。P3 要你在 App 里打开摄像机 RTSP，并给 D2 刷 go2rtc。P4 要买约 100 元零件。

---

## 9. 实现前需要你补充的 4 个事实（有就回，没有就按默认）

1. 萤石具体型号（C6c / C6c Pro / 球形电池机等）。个别猫眼 / 门铃没有 RTSP，只能走云。
2. 补光灯、净化器在易微联里的名称，是「插座通断」还是带风速的净化器面板。
3. 「仓」是已经有外罩，还是先把传感器放在机位桌面当仓内。
4. 库存迁移：现有「开封余量 50%」是当成「已开封 1 卷」即可，还是要先导出备份再清百分比。

默认假设：摄像机支持 RTSP；两个易微联都是开关；仓 = 机位附近先当 enclosure；开封余量一律升成「已开封」。

---

## 10. 验收清单（按这个才算本期完成）

- [ ] 登录后能建产品、上传资料、看冲突。
- [ ] 能横评至少两个产品的厂家 vs Studio vs 实测。
- [ ] 盘点只有「未开封卷数」和「有/无开封卷」，没有余量 %。
- [ ] 不出现按打印任务自动改库存。
- [ ] 机台页只读 A1 六项：热床、喷嘴、层数、进度、剩余、阶段。
- [ ] 没有任何暂停 / 加热 / 发任务按钮。
- [ ] 监控页能看萤石（云或本地至少一条通）。
- [ ] 同一页能开关补光灯和净化器。
- [ ] 没有「关闭 A1 电源」入口。
- [ ] 自定义 RTSP 能作为第二种摄像机加进去。
- [ ] 仓内温湿度 + 门、仓外温湿度 + 人体 + PM2.5 能在机台页更新（P4 后）。
- [ ] Handy / Studio 发任务、暂停仍正常。
