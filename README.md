<div align="center">

# PandaSpool 🐼

**拓竹 Bambu Lab 3D 打印机的自托管中控：打印机监控 · 物理料盘管理 · 环境联动 · 耗材档案**

一个 Go 单二进制，把打印机、摄像头、智能插座和耗材库存装进同一个网页。

[![Release](https://img.shields.io/github/v/release/aiy365/PandaSpool?style=flat-square)](https://github.com/aiy365/PandaSpool/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Go](https://img.shields.io/badge/Go-1.22+-00ADD8?style=flat-square&logo=go&logoColor=white)](https://go.dev)
[![SQLite](https://img.shields.io/badge/SQLite-WAL-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Bambu Lab](https://img.shields.io/badge/Bambu_Lab-MQTT-00AE42?style=flat-square)](https://bambulab.com)

*[English](#english) · [中文](#中文)*

</div>

---

<a id="中文"></a>

## 这是什么

PandaSpool 面向 3D 打印农场和硬核玩家，解决几件拓竹生态里没人管好的事：

| 痛点 | PandaSpool 的做法 |
|---|---|
| 第三方料盘 AMS 识别混乱，实物和 App 对不上 | 入库时在**拓竹云端创建自定义耗材**、注入短编号备注。盘上写 `pm001`，云端和本站 1:1 对应；称重后余量同步云端 |
| 30 卷白 PLA 分不清哪卷在哪 | 色系 × 材料的库存矩阵、未开封/开封台账、入库记账加权均价、参数横评（冲突并存不覆盖） |
| 打 ABS 忘开净化器，打完忘关 | 易微联插座联动：打印自动开排风/净化，结束后延时关闭；状态变化才下发指令 |
| 舱内情况要切三四个 App | 拓竹 MQTT 实时数据 + 萤石云直播同一页面；首层完成和打印结束自动截图推企业微信 |
| 调好的参数散落在聊天记录里 | 产品/颜色/参数档案，支持 AI 起草 → 人工确认的治理流（AI 只能写草稿，不能改库存） |

## 功能一览

- **机台监控**：喷嘴/热床温度、进度、层号、剩余时间、速度档、AMS 装载；自动识别外部料架的闲置占位报文，不误报耗材
- **物理料盘**：快捷入库分配短编号 → 拓竹云端建档 → 记号笔写盘；称重同步、开封/用完状态流转、报废联动云端删除
- **耗材档案**：品牌/系列/材质、色卡与在架库存、烘干/喷嘴/热床参数多来源并存、冲突提示、横评对比
- **环境联动**：易微联继电器（多通道自动拆分）、打印加强延时、补光灯、车间有人感应
- **监控**：萤石云 iframe 直播，画面旋转/裁切，验证码加密设备支持
- **空气**：ESP32 探头上报 PM2.5/温湿度/人体存在，GB/T 18883 对照
- **通知**：企业微信自建应用，首层完成 + 打印结束 10 分钟自动抓图推送
- **AI 接口**：`GET /api/ai/materials` 只读全量档案，`POST /api/ai/drafts` 起草，`/llms.txt` 自述文档

## 快速开始

**方式一：直接下载**（推荐，从 [Releases](https://github.com/aiy365/PandaSpool/releases) 获取 `printpilot-linux-amd64`）：

```bash
wget https://github.com/aiy365/PandaSpool/releases/latest/download/printpilot-linux-amd64
chmod +x printpilot-linux-amd64

# 数据目录放哪都行，建议独立目录便于备份
mkdir -p /var/lib/printpilot
PRINTPILOT_DATA_DIR=/var/lib/printpilot PRINTPILOT_LISTEN=127.0.0.1:8088 ./printpilot-linux-amd64
```

浏览器打开 `http://你的主机:8088`，首次进入会要求创建管理员账号，然后到「设置」页填拓竹/易微联/萤石账号即可。

**方式二：源码构建**（Go ≥ 1.22，前端无需 Node，静态资源已内置）：

```bash
git clone https://github.com/aiy365/PandaSpool.git
cd PandaSpool
go build -o pandaspool ./cmd/pandaspool
```

**systemd 常驻**：参考 [`deploy/printpilot.service`](deploy/printpilot.service)。忘记管理员密码时，在服务器上执行 `./printpilot-linux-amd64 reset-admin 新密码` 重置。

> 🔐 放到公网请务必套一层 HTTPS 反向代理（Caddy / Nginx）。登录基于 Cookie 会话（14 天），空气探头与 AI/桌面端走独立 Bearer 令牌（设置页可查），所有密钥接口均需鉴权且返回时脱敏。

## 配置指引（全部在网页设置页完成）

| 模块 | 填什么 | 备注 |
|---|---|---|
| 拓竹云 | 地区 + 打印机 SN + 账号 | 国内通常需要验证码登录，登录一次后记住 Token；也可直接粘贴 accessToken |
| 易微联 | App 同一套账号 | 登录后点选绑定各路继电器，三联会拆成三路；密码登录报 407 时改用网页版 Token |
| 萤石 | AppKey/Secret + 设备序列号 | 验证码在设备底部标签；画面支持旋转与上下左右裁切 |
| 企业微信 | 企业ID + 应用Secret + AgentID + AESKey | 按"接收消息"URL 校验流程配置，用于图片推送 |
| 空气探头 | 复制空气令牌到 ESP32 固件 | `POST /api/ingest/air`，格式见 [`firmware/air-post.example.json`](firmware/air-post.example.json) |

## 仓库结构

```text
├── cmd/pandaspool/       # 入口（serve / reset-admin）
├── internal/
│   ├── bambu/            # 拓竹：云登录、云端耗材 CRUD、局域网 MQTT 状态机
│   ├── ewelink/          # 易微联：登录（含社区 APPID 回退）、设备/通道、token 自动续期
│   ├── ezviz/            # 萤石：AccessToken、取流
│   ├── server/           # HTTP 路由、会话鉴权、通知、自动化巡检
│   └── store/            # SQLite（WAL）：库存/料盘/参数/收集箱/预设/治理
├── web/                  # 原生 JS SPA + Tailwind/DaisyUI，go:embed 打包进二进制
├── desk/                 # PandaSpool Desk —— Windows 托盘常驻（WPF，任务栏看进度）
├── enclosure-sensor/     # 机箱环境探头：3D 打印外壳 + ESP32-C3 + PMS5003 + SHT31
├── material-lab/         # 耗材实验室：参数测试与数据分析
├── firmware/             # 探头上报报文示例
└── deploy/               # systemd 服务文件
```

## API 摘要

| 端点 | 鉴权 | 用途 |
|---|---|---|
| `GET /api/health` | 无 | 健康检查 |
| `POST /api/ingest/air` | 空气令牌 (Bearer) | ESP32 上报空气数据 |
| `GET /api/ai/materials` | AI 令牌 (Bearer) | 全量耗材档案（只读） |
| `POST /api/ai/drafts` | AI 令牌 (Bearer) | 提交参数草稿（仅草稿，待人工确认） |
| `GET /llms.txt` | AI 令牌 (Bearer) | 给 AI 看的自述文档 |
| `GET /api/desk` | AI 令牌 (Bearer) | 桌面托盘轮询的机台摘要 |
| 其余 `/api/*` | 会话 Cookie | 页面功能 |

---

<a id="english"></a>

## English

**PandaSpool** is a self-hosted control hub for Bambu Lab 3D printers: printer telemetry, physical spool inventory synced 1:1 with Bambu Cloud, environment automation (eWeLink smart plugs), camera viewing (Ezviz), filament knowledge base with an AI draft → human review workflow — all in a single Go binary with an embedded web UI.

**Highlights**

- **Spool management**: intake generates short codes (e.g. `pm001`), registers a custom filament on Bambu Cloud with the code in its note, and syncs remaining weight after you weigh the spool.
- **Printer monitoring**: local MQTT telemetry (temps, progress, layers, AMS loadout), with sane handling of the idle-state `tray_now=254` placeholder quirk.
- **Environment automation**: exhaust/purifier auto-on while printing, delayed auto-off, fill light, presence sensing via eWeLink relays.
- **Filament archive**: products, colors, stock ledger, purchase cost averaging, multi-source parameter claims with conflict detection and comparison views.
- **AI-friendly**: read-only material pack + draft-only write API (`/llms.txt` documents it), so agents can help without touching inventory.
- **Zero-ops stack**: Go stdlib + pure-Go SQLite (WAL) + vanilla JS SPA embedded via `go:embed`. One binary, one data directory.

**Run it**

```bash
# from Releases, or: go build -o pandaspool ./cmd/pandaspool
PRINTPILOT_DATA_DIR=/var/lib/printpilot PRINTPILOT_LISTEN=127.0.0.1:8088 ./pandaspool
# open http://127.0.0.1:8088 and create the admin account on first run
```

Configure Bambu / eWeLink / Ezviz / WeCom on the Settings page. Put it behind HTTPS if exposed. See the Chinese section above for the full guide.

## License

MIT — see [LICENSE](LICENSE). Independent community project, **not** affiliated with or endorsed by Bambu Lab, Ezviz, or eWeLink. All product names are trademarks of their respective owners.
