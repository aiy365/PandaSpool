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

### 📄 协议 (License)
MIT License
