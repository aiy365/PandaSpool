#!/bin/bash
set -euo pipefail
systemctl stop printpilot
install -o printpilot -g printpilot -m 755 /tmp/printpilot.new /opt/printpilot/printpilot
systemctl start printpilot
systemctl is-active printpilot
