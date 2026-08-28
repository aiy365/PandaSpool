#!/bin/bash
set -euo pipefail
systemctl stop pandaspool
install -o pandaspool -g pandaspool -m 755 /tmp/pandaspool.new /opt/pandaspool/pandaspool
systemctl start pandaspool
systemctl is-active pandaspool
