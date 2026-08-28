# PandaSpool 🐼🛠️

![Bambu Lab](https://img.shields.io/badge/Ecosystem-Bambu%20Lab-00AE42.svg)
![Go](https://img.shields.io/badge/Backend-Go-00ADD8.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg)

*( [Read in English](#english) | [中文说明往下看](#中文-chinese) )*

<a id="english"></a>
## 🇬🇧 English

**PandaSpool** is the ultimate self-hosted Filament Inventory and AMS (Automatic Material System) Management Hub designed exclusively for the Bambu Lab 3D printing ecosystem. 

Say goodbye to generic spool names and "Unsupported Filament" errors in Bambu Studio. PandaSpool ensures a strict 1:1 binding between your physical filament shelves, your Bambu Studio custom slice presets, and the Bambu Cloud.

### 🌟 Key Features
- **3-Way Preset Syncing (The "Steal" Mechanism)**: Automatically fetches your custom user presets (UUIDs) from Bambu Cloud. When you mount a spool created via PandaSpool into your AMS, Bambu Studio recognizes it perfectly.
- **Smart Short Codes & Physical Labels**: Automatically generates intelligent short codes (e.g., `pt001` for Polymaker PETG Transparent) upon intake. 
- **Cloud Note Injection**: Pushes the generated short code directly into the Bambu Cloud Spool `Note` field, making physical stick-on labeling and matching effortless.
- **Lightweight & Self-Hosted**: Powered by a blazing-fast Go backend and an embedded SQLite database. No heavy containers required.
- **Monorepo Ecosystem**: Includes companion tools for a full makerspace setup:
  - `desk/`: Windows desktop companion utility.
  - `enclosure-sensor/`: 3D WebGL dashboard for monitoring printer enclosure temperature and humidity.
  - `material-lab/`: Data analytics and telemetry for filament calibration and testing.

### 🌪️ Smart IoT & Environmental Control
PandaSpool goes beyond just filament tracking—it is a full-fledged smart enclosure controller:
- **eWeLink (易微联) Smart Relay Integration**: Natively controls dual-channel air purifiers/exhaust fans. It automatically manages VOCs and fumes when printing toxic materials (like ABS/ASA).
- **Ezviz (萤石) Camera Integration**: Seamlessly integrates cloud cameras for remote print monitoring.
- **3D Digital Twin**: The `enclosure-sensor` module provides a WebGL-based real-time 3D dashboard displaying in-enclosure temperature, humidity, and environmental telemetry.

### 🤖 AI-Native Engineering & Human-AI Collaboration
PandaSpool is a proud product of **Human-AI Pair Programming**. 
- **"Talk to Deploy"**: Built entirely through continuous dialogue with advanced AI agents. The user defines the physical pain points (e.g., "Bambu Studio says the filament is unsupported"), and the AI diagnoses the cloud UUID mismatches, rewrites the Go logic, and deploys it live to the server in minutes.
- **Complex API Resolution**: Challenges like analyzing Bambu Cloud's undocumented filament structures and building the 3-way synchronization logic were achieved through AI's powerful data analysis and logical deduction.
- **A New Paradigm**: This project proves that AI is no longer just a code-autocompleter. It acts as a full-stack co-architect, drastically lowering the barrier for makers to build complex, enterprise-grade IoT systems.

### 🚀 Getting Started
```bash
# Clone the repository
git clone https://github.com/aiy365/PandaSpool.git
cd PandaSpool

# Build the main hub
GOOS=linux GOARCH=amd64 go build -o pandaspool ./cmd/pandaspool

# Run
./pandaspool
```

---

<a id="中文-chinese"></a>
## 🇨🇳 中文 (Chinese)

**PandaSpool** 是专为拓竹 (Bambu Lab) 3D打印生态打造的终极私有化耗材库存 (Filament Inventory) 与 AMS (Automatic Material System) 管理中枢。

告别 Bambu Studio 中烦人的“不支持的耗材 (Unsupported Filament)”报错！PandaSpool 通过云端级联，确保你的物理耗材架、拓竹切片预设 (Slicing Presets) 与 Bambu Cloud 之间实现 100% 的精准绑定。

### 🌟 核心功能 (Core Features)
- **预设无缝级联同步 (Preset Sync)**：打破拓竹生态壁垒，一键从拓竹云端 (Bambu Cloud) 抓取你的自定义切片预设 ID (Custom UUIDs)。在 PandaSpool 选定预设并入库后，AMS 装载将完美被电脑端 Studio 识别，永不报错。
- **智能短编号生成 (Smart Short Codes)**：耗材入库时，系统会自动提取品牌与颜色的中英文首字母，生成极具辨识度的短编号（例如：Polymaker 透明 PETG -> `pt001`），彻底解放手工编目。
- **云端备注自动注入 (Cloud Note Injection)**：PandaSpool 在向拓竹云推送新建料盘 (Spool) 时，会自动将短编号注入到拓竹的备注 (Note) 字段中。你在手机 App 里看一眼备注，就能精准对应货架上的实体标签。
- **极致轻量私有化 (Lightweight Self-Hosted)**：基于 Go 语言构建的极速后端 + SQLite 嵌入式数据库。仅需一个可执行文件即可完成部署，无任何重度容器依赖。
- **支持动态白标命名 (Dynamic Branding)**：在后台设置即可实时修改全站 UI 标题，打造你的专属耗材库。

### 🛠️ 创客空间全家桶 (Monorepo Ecosystem)
本项目采用 Monorepo 架构，集成了完善的周边创客生态工具：
* **`PandaSpool (Root)`**：核心库存与拓竹云同步管家 (Main Hub)。
* **`desk/`**：桌面端常驻辅助挂件 (Desktop Companion)。
* **`enclosure-sensor/`**：基于 3D WebGL 的打印机封箱环境（温湿度）监控看板 (Enclosure Telemetry Dashboard)。
* **`material-lab/`**：耗材极限测试与参数调优的数据分析看板 (Material Analytics Lab)。

### 🌪️ 智能 IoT 与环境中控 (Smart IoT & Environment Control)
PandaSpool 不仅仅是一个耗材库，它更是你的硬核打印机中控台，**原生自带**强大的智能家居与环境联动能力：
- **易微联 (eWeLink) 深度接入**：原生支持智能继电器，精准控制 **2 路空气净化器 / 抽风排气系统**。打印 ABS/ASA 等高温毒气材料时，系统自动接管环境净化，保护创客健康。
- **萤石 (Ezviz) 监控联动**：无缝接入萤石云摄像头，实时串流掌控打印机舱内画面。
- **3D 数字孪生封箱监控**：内置 `enclosure-sensor` 模块，通过精美的 3D WebGL 界面，实时透视打印机封箱内的温湿度与环境传感数据，极具赛博朋克感。

### 🤖 AI 原生工程与人机协同 (Human-AI Collaboration)
PandaSpool 是 **AI 与人类结对编程 (Pair Programming)** 的极佳范例。本项目在开发过程中，深度践行了 AI 原生工程理念：
- **“对话即部署” (Talk to Deploy)**：用户仅需输入业务痛点（例如：“PC端一直报错不支持该耗材”），AI 助手即可自主排查、分析底层的拓竹预设 UUID 映射冲突，随后自动修改 Go 后端源码并一键通过 SSH 部署到服务器，实现分钟级迭代。
- **降维解析复杂架构**：针对拓竹云非公开 API 的结构解析、多端 (PC/App/Web) 数据同步闭环的搭建，完全依托人机协同的逻辑推演完成。
- **开发范式转移 (Paradigm Shift)**：PandaSpool 证明了现代 AI 工具不仅是“代码补全器”，更是懂业务、懂运维的“系统架构合伙人”。它极大降低了 3D 打印创客们搭建复杂、全栈 IoT 系统的技术门槛。

### 🚀 快速开始 (Getting Started)
```bash
# 克隆项目仓库 (Clone)
git clone https://github.com/aiy365/PandaSpool.git
cd PandaSpool

# 编译主程序 (Build)
GOOS=linux GOARCH=amd64 go build -o pandaspool ./cmd/pandaspool

# 运行 (Run)
./pandaspool
```

> **最佳实践工作流 (Best Practice Workflow)**：
> 1. 在 Bambu Studio 电脑端调优并保存你的【自建材料 (Custom Filament)】。
> 2. 在拓竹 Handy App 手机端新建一个虚拟库存，选中该自建材料。
> 3. 在 PandaSpool 后台点击【抓取已有料盘作预设】，随后在下拉框绑定它。
> 4. 点击【入库 (Intake)】，打印标签机贴在实物料盘上，直接塞入 AMS！

### ⚖️ 免责声明 (Disclaimer)
PandaSpool 是一个独立的社区开源项目，与拓竹科技 (Bambu Lab) 官方无任何关联、赞助、授权或背书。“Bambu Lab” 及相关商标均归其合法所有者所有。本项目仅作为辅助工具，使用用户自行提供的合法凭证与公开网络接口进行交互，使用者需自行承担因使用本软件可能带来的任何数据或账号风险。

### 📄 协议 (License)
MIT License
