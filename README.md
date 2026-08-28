# PrintPilot Hub

封箱车间后台：耗材档案、架子账、A1 只读、易微联开关、萤石云预览、仓外空气。

前端是 **Go embed 的静态页**（`web/dist`），UI 用 [daisyUI 5](https://daisyui.com/)（MIT，已 vendor 进 `web/dist/vendor/daisyui.css`），没有在服务器上跑 Node。

**UI 约定（以后都按这个）：** 默认 `data-theme="light"`，顶栏切换 daisyUI `dark`，记在 `localStorage.pp-theme`。控件一律用官方类：`btn` / `input input-bordered` / `select select-bordered` / `textarea` / `card card-body card-title` / `table` / `badge` / `stats` / `alert` / `menu`。颜色只用 `--color-*`，不要写死色值。登录页和后台同一套。

**给第二个人：** 拷贝一个二进制 + 本 README。第一次打开浏览器创建管理员，所有密钥都在「设置」里填，不用改配置文件。

## 本机运行

```bash
./printpilot
# 浏览器打开 http://127.0.0.1:8088
```

可选环境变量（只有这两项，其余全在设置页）：

| 变量 | 默认 | 含义 |
|---|---|---|
| `PRINTPILOT_DATA_DIR` | `./data` | 数据库和上传文件 |
| `PRINTPILOT_LISTEN` | `127.0.0.1:8088` | 监听地址 |

公网请放在反向代理后面（Caddy / Nginx），不要把 8088 直接暴露。

## 设置页要填什么

1. 站点名称、登录用户名/密码  
2. 拓竹：账号、密码、地区（cn）、打印机 SN  
3. 易微联：填和手机 App 同一套账号密码 →「登录并拉设备」→ 在列表里点绑定（三联会拆成通道 1/2/3）→ 试开/试关。APPID 不用填。
4. 萤石开放平台：AppKey、AppSecret、设备序列号、通道  
5. 空气上报令牌（给 ESP32）  
6. AI 令牌：只读档案 / 起草草稿（不能确认、不能改库存）  

耗材治理：资料/Studio/实测并存，冲突不覆盖。厂家和商家不再区分。人手记的是已确认；AI 只进草稿箱，人在产品页确认或驳回。详见 `docs/governance.md`。

保存后自动重连拓竹 MQTT。不会控制打印机（无暂停/加热/发任务）。

## 轮询节拍

| 谁 | 空闲 | 打印中 / 打印加强 |
|---|---|---|
| Hub 易微联自动化 | 60 秒 | 20 秒 |
| 网站机台页 | 15 秒（离开页面或切后台会停） | 同左 |
| Desk 托盘 | 设置里的间隔，默认 30 秒 | 取 10 秒和设置值的较小者 |

静态 `app.js` / `styles.css` 带内容 hash，更新后不用强刷。同名颜色再次「加入」会改这一条，不会复制一行。空颜色名仍是独立色卡槽，不合并。

## 从源码打包

前端就是 `web/dist`（手改 `app.js` / `styles.css`），**不要**走 npm build。嵌入进 Go：

```bash
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o dist/printpilot ./cmd/printpilot
```

把 `dist/printpilot` 拷到目标机器，`chmod +x` 后运行。部署脚本：`scripts/deploy-bin.sh`。

## 空气探头（仓外一期）

见仓库文档 `docs/PrintPilot缝合体_实用主义BOM_v3.md` 里的硬件部署方案与 BOM 表。固件向 `POST /api/ingest/air` 上报，Header：`Authorization: Bearer <设置页令牌>`。
