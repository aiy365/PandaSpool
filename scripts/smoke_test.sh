#!/bin/bash
# PandaSpool 本地冒烟测试：起一个全新实例，验证鉴权与核心 API。
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
export no_proxy='*'
BIN=/root/pp-rt/pp-test
BASE=http://127.0.0.1:18088
DATA=/root/pp-rt/data

pkill -f "$BIN" 2>/dev/null
rm -rf "$DATA"
mkdir -p "$DATA"

PRINTPILOT_DATA_DIR="$DATA" PRINTPILOT_LISTEN=127.0.0.1:18088 "$BIN" >"$DATA/server.log" 2>&1 &
SRV=$!
sleep 2

say() { echo "== $1"; }
say "health:      $(curl -s $BASE/api/health)"
say "bootstrap:   $(curl -s $BASE/bootstrap 2>/dev/null || curl -s $BASE/api/bootstrap)"
say "me(no auth): $(curl -s -o /dev/null -w '%{http_code}' $BASE/api/me)"
say "summary401:  $(curl -s -o /dev/null -w '%{http_code}' $BASE/api/summary)"

say "setup:       $(curl -s -X POST $BASE/api/setup -d '{"title":"测试站","username":"admin","password":"admin123"}')"
say "login(bad):  $(curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/api/login -d '{"username":"admin","password":"wrong"}')"
say "login(ok):   $(curl -s -c /root/pp-rt/cookie.txt -X POST $BASE/api/login -d '{"username":"admin","password":"admin123"}')"
say "me(auth):    $(curl -s -b /root/pp-rt/cookie.txt $BASE/api/me)"

say "create product: $(curl -s -b /root/pp-rt/cookie.txt -X POST $BASE/api/products -d '{"brand":"测试牌","product_line":"光滑","material":"PLA"}' | head -c 120)"
PID=$(curl -s -b /root/pp-rt/cookie.txt $BASE/api/products | python3 -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')
say "add color:   $(curl -s -b /root/pp-rt/cookie.txt -X POST $BASE/api/colors -d "{\"product_id\":\"$PID\",\"name\":\"黑色\",\"unopened\":2,\"opened\":1}" | head -c 150)"
CID=$(curl -s -b /root/pp-rt/cookie.txt $BASE/api/colors | python3 -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')
say "colors all:  $(curl -s -b /root/pp-rt/cookie.txt $BASE/api/colors | head -c 150)"
say "stock-in:    $(curl -s -b /root/pp-rt/cookie.txt -X POST $BASE/api/stock-ins -d "{\"color_id\":\"$CID\",\"qty\":2,\"unit_price\":88,\"apply\":true}" | head -c 150)"
say "stock-list:  $(curl -s -b /root/pp-rt/cookie.txt "$BASE/api/stock-ins?product_id=$PID" | head -c 150)"

AIRTOKEN=$(curl -s -b /root/pp-rt/cookie.txt $BASE/api/settings | python3 -c 'import sys,json;print(json.load(sys.stdin)["air"]["token"])')
say "air token len: ${#AIRTOKEN}"
say "ingest(no auth): $(curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/api/ingest/air -d '{"pm25":12}')"
say "ingest(bad):     $(curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/api/ingest/air -H "Authorization: Bearer wrong" -d '{"pm25":12}')"
say "ingest(ok):      $(curl -s -X POST $BASE/api/ingest/air -H "Authorization: Bearer $AIRTOKEN" -d '{"ts":1776500000,"zone":"room","pm25":12,"t_c":26.4,"rh":55,"presence":true}')"
say "air list:    $(curl -s -b /root/pp-rt/cookie.txt $BASE/api/air | head -c 200)"
say "summary:     $(curl -s -b /root/pp-rt/cookie.txt $BASE/api/summary | head -c 300)"

say "settings redacted: $(curl -s -b /root/pp-rt/cookie.txt $BASE/api/settings | python3 -c 'import sys,json;d=json.load(sys.stdin);print("air_token_visible=",d["air"]["token"][:6],"ai_len=",len(d["ai"]["token"]))')"
say "logout:      $(curl -s -b /root/pp-rt/cookie.txt -c /root/pp-rt/cookie.txt -X POST $BASE/api/logout)"
say "me(after logout): $(curl -s -b /root/pp-rt/cookie.txt -o /dev/null -w '%{http_code}' $BASE/api/me)"

say "static:      $(curl -s -o /dev/null -w '%{http_code}' $BASE/)"
kill $SRV 2>/dev/null
echo DONE
