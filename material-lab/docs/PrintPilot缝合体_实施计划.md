# PrintPilot 缝合体：整体实施计划

| 项 | 内容 |
|---|---|
| 日期 | 2026-08-18 |
| 原则 | 推倒重来。旧看板、旧库、旧语义不兼容。 |
| 服务器 | 腾讯云 yby `159.75.227.95`（**共享机**，不是专属） |
| 域名 | `https://3d.bstccc.cn` |
| 第一期不上 | Newifi D2、仓内空气探头、RTSP、门磁、第三方打印控制 |

本文是施工主计划。选型细节见：

- `PrintPilot缝合体_v2.1_传感器与服务器栈.md`
- `PrintPilot缝合体_仓外低成本BOM.md`

---

## 1. 做成什么样

一个人用的车间后台，四件事在同一站点：

1. **耗材**：这款料什么参数、资料整理、横评；厂家 / 商家 / Studio / 实测分层，冲突并存。
2. **架子账**：未开封卷数 + 有没有开封卷。不按任务扣，不要余量 %。
3. **机台只读**：绑拓竹账号，yby 连云 MQTT。热床 / 喷嘴 / 层数 / 进度 / 剩余 / 阶段。不暂停、不加热、不发任务。Handy / Studio 不动。
4. **封箱周边**：萤石云预览 + 补光手开；三路净化器（仓内长开 / 仓内打印+30 分钟 / 车间有人）；仓外空气（PMS5003 + SHT30 + LD2410C）上报并画曲线。

仓内 SPS30/SGP41、D2、本地 RTSP —— 以后再说。

---

## 2. 服务器治理（先于写代码）

yby 是共享机：Caddy 管整机 HTTPS，云镜常驻，OpenClaw 卸过一次还留渣。新服务必须当邻居。

### 2.1 保留（动了会伤整机）

| 留下 | 原因 |
|---|---|
| Debian 12、SSH、root 密钥 | 登录 |
| 腾讯云 tat / barad / 云镜 | 平台组件 |
| **Caddy** + 80/443 证书 | 整机唯一入口 |
| 系统 Python 3.11 | 以后脚本可能用，不是旧看板 |
| 时区、ntp、journald | 系统 |

### 2.2 删除 / 停用（旧 PrintPilot 及残留）

| 处理 | 对象 |
|---|---|
| stop + disable | `printpilot-material-dashboard.service` |
| stop + disable | `printpilot-material-backup.timer` / `.service` |
| 归档后删除 | `/opt/printpilot-material-lab/`（含 venv） |
| 归档后删除 | `/var/lib/printpilot-material-lab/` |
| 删除 | `/etc/printpilot-material-lab/`（若还在） |
| 删除 | systemd unit 文件并 `daemon-reload` |
| 删除用户 | `printpilot` 系统用户（新系统再建干净的） |
| Caddy | 去掉旧反代；先挂静态「重建中」页，避免 502 |
| 日志 | `/var/log/caddy/printpilot-access.log*` 可清 |

卸载前在服务器打 **一份** tar 到 `/var/backups/printpilot-material-lab-final-*.tar.gz`，只为误删可回，**不迁入新系统**。

### 2.3 顺带清的历史渣（已卸的 OpenClaw）

服务早已停。磁盘还占着，和「干净」冲突则清掉：

- `/root/.openclaw/`、各 `workspace-*`、`/tmp/openclaw/`
- `/root/self-improving/`（若确认只属 OpenClaw）
- 用户级 `openclaw-gateway.service` 残片
- **不删** `/root/.nvm` 除非盘点后确认无任何脚本依赖（留给以后 Bot；新 PrintPilot **不用** Node）

新 PrintPilot 禁止使用 `/root/.nvm`、禁止占 18789、禁止装 Docker/PM2/Nginx。

### 2.4 新系统落位（治理完的目标形态）

```text
Caddy :80/:443
  └── 3d.bstccc.cn → 127.0.0.1:8088

/opt/printpilot/            只读发布：二进制 + 前端 dist
/var/lib/printpilot/        数据：app.sqlite3、files/、secrets（600）
/etc/systemd/system/printpilot.service
用户 printpilot（nologin）

RSS 目标 < 150MB
公网仍只有 22 / 80 / 443
```

技术栈：本机交叉编译的 **Go 单进程** + 静态 React；服务器不装 Go、不装 Docker。

---

## 3. 分期

### P0  服务器干净（本轮做）

- 旧服务停、归档、删、Caddy 维护页、台账更新。
- 本地仓库另开新目录写新系统，旧 `src/` 不再作为运行代码。

### P1  空壳上线

- Go 登录空站接到 `3d.bstccc.cn`。
- 新库、新密码。不导入旧 13 产品。

### P2  耗材实验室

- 产品 / 颜色 / 资料 / 冲突 / 横评。
- 库存：未开封 + 开封布尔。

### P3  机台只读

- 拓竹云账号绑定、yby MQTT、六项状态。
- 代码层不封装 pause / print / 调温。

### P4  易微联 + 萤石

- 补光手开；三路净化器策略。
- 萤石 EZUIKit 云预览（CS-C6H / CS-XP1）。

### P5  仓外空气

- ESP32-C3 + PMS5003 + SHT30 + LD2410C。
- HTTPS ingest、曲线、24h 对照 50 µg/m³（写明参考）。
- 有人 → 车间净化器。

仓内探头、D2、RTSP 不进上述期次。

---

## 4. 验收（第一期结束）

- [ ] yby 上无旧 dashboard / 旧 sqlite / 旧 venv
- [ ] `3d.bstccc.cn` 是新站或维护页，不是旧看板
- [ ] Handy / Studio 不受影响
- [ ] 无打印控制按钮
- [ ] 耗材 + 架子账 + 横评可用
- [ ] 机台六项只读
- [ ] 三路净化器 + 补光 + 萤石云画面
- [ ] 仓外 PM / 温湿 / 人体有曲线
- [ ] 台账已更新

---

## 5. 风险

| 风险 | 处理 |
|---|---|
| 删旧站后域名空窗 | Caddy 先挂维护页 |
| 共享机再上 Bot | Go 常驻压在 150MB 内，不用 nvm |
| 萤石 C6H 云取流失败 | 只用 XP1 |
| PMS5003 数值虚 | UI 标明参考 |
| 误删 | `/var/backups/` 留一份 final tar，不回迁业务 |
