#!/bin/bash
# 补充接口验证：bootstrap / AI 令牌 / 产品详情聚合 / desk
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
export no_proxy='*'
B=http://127.0.0.1:18088
CK=/root/pp-rt/ck.txt

curl -s -c "$CK" -X POST $B/api/login -d '{"username":"admin","password":"admin123"}' >/dev/null
echo "bootstrap: $(curl -s $B/api/bootstrap)"
AIT=$(curl -s -b $CK $B/api/settings | python3 -c 'import sys,json;print(json.load(sys.stdin)["ai"]["token"])')
PID=$(curl -s -b $CK $B/api/products | python3 -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')
echo "ai-pack(ok):   $(curl -s -o /dev/null -w '%{http_code}' $B/api/ai/materials -H "Authorization: Bearer $AIT")"
echo "ai-pack(bad):  $(curl -s -o /dev/null -w '%{http_code}' $B/api/ai/materials -H 'Authorization: Bearer nope')"
echo "llms.txt:      $(curl -s -o /dev/null -w '%{http_code}' $B/llms.txt -H "Authorization: Bearer $AIT")"
echo "presets:       $(curl -s -b $CK $B/api/presets)"
echo "prod-detail:   $(curl -s -b $CK $B/api/products/$PID | python3 -c 'import sys,json;d=json.load(sys.stdin);print(sorted(d.keys()))')"
echo "desk(authAI):  $(curl -s -o /dev/null -w '%{http_code}' $B/api/desk -H "Authorization: Bearer $AIT")"
echo "desk(cookie):  $(curl -s -o /dev/null -w '%{http_code}' $B/api/desk -b $CK)"
echo "ai-draft:      $(curl -s -X POST $B/api/ai/drafts -H "Authorization: Bearer $AIT" -H 'Content-Type: application/json' -d '{"drafts":[{"product_id":"'"$PID"'","source":"资料","key":"烘干","value":"55°C 6h"}]}' | head -c 160)"
echo "claims-list:   $(curl -s -b $CK "$B/api/claims?product_id=$PID" | head -c 200)"
DID=$(curl -s -b $CK "$B/api/claims?product_id=$PID" | python3 -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')
echo "review-ok:     $(curl -s -b $CK -X POST $B/api/claims/review -d '{"id":"'"$DID"'","status":"confirmed"}')"
echo "claim-del:     $(curl -s -b $CK -X DELETE "$B/api/claims?id=$DID")"
echo "compare:       $(curl -s -b $CK $B/api/compare | head -c 120)"
