# PandaSpool 🐼🛠️

![Bambu Lab](https://img.shields.io/badge/Ecosystem-Bambu%20Lab-00AE42.svg)
![Go](https://img.shields.io/badge/Backend-Go-00ADD8.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg)

*( [Read in English](#english) | [中文说明往下看](#chinese) )*

<a id="english"></a>
## 🇬🇧 English

**PandaSpool** is the ultimate self-hosted Filament Inventory and Enclosure Management Hub, born to solve the most frustrating pain points of the Bambu Lab 3D printing ecosystem.

### 💔 The Pain Points & 🐼 The PandaSpool Solutions

**💣 Pain Point 1: The "Unsupported Filament" Nightmare**
* **The Problem**: You spend hours tuning a custom preset for a third-party filament in Bambu Studio. But when you load the physical spool into your AMS via the Handy App, Bambu Studio stubbornly yells *"Unsupported Filament"* because the cloud UUIDs don't match.
* **The Solution (True Preset Sync)**: PandaSpool directly hooks into the Bambu Cloud API to "steal" your exact Custom Preset UUIDs. When you intake a spool through PandaSpool, it binds the physical spool to your actual custom preset. Result? 100% perfect recognition in the AMS. Zero errors.

**📦 Pain Point 2: The "Which White PLA is This?" Chaos**
* **The Problem**: You have 30 spools on the shelf. Five of them are White PLA. Which one is loaded in Slot 3? You resort to messy sharpie marks that don't match the digital UI.
* **The Solution (Smart Short Codes)**: Upon intake, PandaSpool generates an elegant, readable short code (e.g., `pt001`). More importantly, it **automatically injects this code into the Bambu Cloud Spool Note**. Print a physical label `pt001`, stick it on the spool, and your physical shelf perfectly matches your digital Bambu UI.

**☠️ Pain Point 3: Toxic Fumes & Manual Fans**
* **The Problem**: Printing ABS/ASA creates toxic VOCs. You have to manually turn on an external air purifier, and remember to turn it off 30 minutes after the print finishes.
* **The Solution (Smart eWeLink Exhaust)**: Built-in eWeLink IoT integration. PandaSpool natively controls dual-channel smart relays for air purifiers and exhaust fans, automating environmental safety.

**👁️ Pain Point 4: Blind Spots in the Enclosure**
* **The Problem**: Juggling multiple apps just to check your printer's camera, enclosure temperature, and humidity.
* **The Solution (3D Digital Twin & Ezviz)**: Seamlessly integrates Ezviz cloud cameras and features `enclosure-sensor`—a gorgeous 3D WebGL dashboard that displays real-time telemetry (temp/humidity) of your printer's enclosure.

### 🤖 AI-Native Engineering
PandaSpool was built using **Human-AI Pair Programming**. By simply describing business pain points ("Bambu Studio rejects my filament"), AI agents diagnosed undocumented cloud APIs, engineered the 3-way sync architecture, and deployed the Go backend in minutes—proving AI is now a full-stack co-architect.

### 🚀 Getting Started
```bash
git clone https://github.com/aiy365/PandaSpool.git
cd PandaSpool
GOOS=linux GOARCH=amd64 go build -o pandaspool ./cmd/pandaspool
./pandaspool
```

### ⚖️ Disclaimer & License
PandaSpool is an independent open-source project and is **not** affiliated with Bambu Lab. (MIT License)

---

<a id="chinese"></a>
## 🇨🇳 中文 (Chinese)

**PandaSpool** 是专为拓竹 (Bambu Lab) 生态打造的终极私有化耗材与环境中控平台。它的诞生，是为了彻底消灭 3D 打印玩家在日常使用中最抓狂的四大痛点。

### 💔 用户痛点与 🐼 PandaSpool 破局方案

**💣 痛点一：第三方耗材永远报“不支持的耗材”？**
* **抓狂瞬间**：你花了一整晚在 Bambu Studio 调教 Polymaker 的参数并存为“自建预设”。结果把料盘塞进 AMS，手机 App 选完后，电脑端却无脑闪烁红字警告：“不支持的耗材 (Unsupported Filament)”。
* **破局方案 (预设无缝级联)**：PandaSpool 打通了拓竹云底层接口，直接“偷取”你账号下真实的自定义切片预设 ID (Custom UUIDs)。以后只要在 PandaSpool 录入耗材，物理料盘与切片预设就能实现 100% 的完美底层绑定，插上 AMS 瞬间识别，再无报错。

**📦 痛点二：30卷耗材，究竟哪个是哪个？**
* **抓狂瞬间**：货架上有 5 卷白色的 PLA，AMS 里也显示白色 PLA。用到最后根本不知道对应哪一卷，只能用记号笔在盘子上乱涂乱画。
* **破局方案 (短编号与云备注注入)**：入库时，系统会自动提取品牌与颜色的中英文首字母，生成极简短编号（如 `pt001`）。更绝的是，系统会**自动将该编号注入到拓竹云端料盘的备注 (Cloud Note) 中**。你只需用标签机打个 `pt001` 贴在实体盘上，实物与手机/PC 端的 UI 就实现了精密的“卡片级”对齐。

**☠️ 痛点三：打 ABS/ASA 毒气弥漫，总是忘开净化器？**
* **抓狂瞬间**：打高温毒气材料时，必须手动去开外置抽风机；打完了还要自己算时间去关，麻烦且伤身。
* **破局方案 (易微联环境联动)**：系统原生接入易微联 (eWeLink) 智能继电器协议，直接接管 **2路空气净化 / 抽风排气系统**。伴随打印机状态，彻底实现有毒气体排出的自动化管理。

**👁️ 痛点四：机箱内部环境瞎子摸象？**
* **抓狂瞬间**：看个监控要切萤石 App，看个舱内温湿度还要去瞟单独的温湿度计，极其割裂。
* **破局方案 (萤石监控 & 3D 数字孪生)**：系统整合了萤石 (Ezviz) 云监控，并内置了极具赛博朋克感的 `enclosure-sensor` 3D WebGL 数字孪生看板。电脑屏幕前，舱内温湿度传感数据、实时画面一览无余。

### 🤖 AI 原生工程与人机协同 (Human-AI Collaboration)
PandaSpool 是 **AI 与人类结对编程 (Pair Programming)** 的极佳范例。
本项目的核心架构（包括逆向解析非公开拓竹云 API、搭建多端同步闭环）均通过“对话即部署 (Talk to Deploy)”完成。玩家只需抛出痛点，AI 即可自主完成抓包排查、Go 逻辑重写及 SSH 一键部署。它极大降低了创客搭建复杂 IoT 全栈系统的门槛。

### 🛠️ 创客空间全家桶 (Monorepo Ecosystem)
本项目采用大仓库 (Monorepo) 架构：
* **`PandaSpool (Root)`**：核心 Go 后端与库存管理主 Web 中枢。
* **`desk/`**：桌面端常驻辅助挂件。
* **`enclosure-sensor/`**：基于 3D WebGL 的打印机封箱环境监控看板。
* **`material-lab/`**：耗材极限测试与参数调优数据分析室。

### 🚀 快速开始
```bash
git clone https://github.com/aiy365/PandaSpool.git
cd PandaSpool
GOOS=linux GOARCH=amd64 go build -o pandaspool ./cmd/pandaspool
./pandaspool
```

### ⚖️ 免责声明与协议 (Disclaimer & License)
PandaSpool 是一个独立的社区开源项目，与拓竹科技 (Bambu Lab) 无任何关联或背书。“Bambu Lab” 及相关商标均归其合法所有者所有。本项目基于 MIT 协议开源。
