#!/usr/bin/env python3
import json
import collections

p = r"C:\Users\user\.grok\sessions\C%3A%5Cwork%5C3D%E6%A8%A1%E5%9E%8B\01a01299-2c87-7ea0-8d8e-f3380749bff2\terminal\call-f3fd21c6-bd77-4b57-876b-12fd2e3e13e8-167.log"
rows = []
for line in open(p, encoding="utf-8", errors="replace"):
    line = line.strip()
    if line.startswith("{"):
        rows.append(json.loads(line))
print("n", len(rows))
keys_keep = {
    "密度",
    "热变形温度",
    "热变形温度 0.45 MPa",
    "热变形温度 1.8 MPa",
    "维卡软化温度",
    "拉伸强度",
    "拉伸强度 XY",
    "弯曲强度",
    "弯曲强度 XY",
    "断裂伸长率",
    "断裂伸长率 XY",
    "冲击强度",
    "冲击强度 XY",
    "缺口冲击强度",
    "简支梁冲击强度 XY",
    "简支梁冲击强度 XY 无缺口",
    "简支梁冲击强度 XY 缺口",
    "抗冲击强度",
    "喷嘴温度",
    "打印温度",
    "热床温度",
    "打印速度",
    "熔融指数",
    "最大体积流量",
    "流量比例",
    "杨氏模量 XY",
    "拉伸模量 XY",
    "弯曲模量",
    "弯曲模量 XY",
}
by = collections.defaultdict(list)
for r in rows:
    if r["source"] == "Studio":
        continue
    if r["claim_key"] not in keys_keep:
        continue
    name = f"{r['brand']} {r['product_line']} {r['material']}".replace("  ", " ").strip()
    by[name].append((r["claim_key"], r["claim_value"], r["unit"]))
for name, items in sorted(by.items()):
    print("\n##", name)
    for k, v, u in items:
        print(f"  {k}: {v} {u}")
