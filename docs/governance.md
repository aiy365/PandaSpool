# 耗材治理（已裁决）

系统记住所有说法和证据；人负责采用哪一条；AI 负责读、比、起草，绝不静默覆盖。

## 做什么

- 资料 / Studio / 实测 三条来源并存。厂家和商家不再区分，一律记成资料。
- 同一字段不同值 = 冲突，并排显示，不挑赢家。
- 人手在产品页「记一条」= 已确认。
- AI 只能 `POST /api/ai/drafts` 进草稿箱；人点确认或驳回。
- 库存仍是未开封卷 + 开封有/无。不按打印扣料。
- 不根据档案生成切片参数，不控制打印机。

## 不做什么

- 不搬回 Python 的 stage/manifest/review.md 三件套。
- 不要余量百分比、不要单卷资产、不要自动扣料。
- 不从「最高打印速度」推最大体积流量。

## 收集箱

人在某个耗材详情页上传 JPG/PNG/WebP。系统只存原图（SHA-256 去重），不识图、不写参数。

叫 AI 处理时：读 `GET /api/ai/materials` 的 `inbox`，拉 `/api/inbox/{id}/file`，抽出字段 `POST /api/ai/drafts`，再 `POST /api/inbox/{id}/processed`。

颜色目录与库存分开：商家色名可空可填（下拉或手打）。色卡只建 0 库存目录，不假装已进货。

预设：产品页上传 JSON / bbsflmt。抽出流量、MVS、温度等到草稿，和已有资料并排。Studio 截图只能标 Studio，不得冒充产品资料。

## AI

设置页「AI 令牌」。`GET /api/ai/materials` 只读包，`GET /llms.txt` 说明接口。
