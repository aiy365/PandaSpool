#!/bin/bash
set -e
cd "/mnt/c/work/3D模型/printpilot-hub"
unset http_proxy https_proxy
GOOS=linux /usr/local/go/bin/go build -o printpilot-linux-amd64 ./cmd/pandaspool
echo BUILD_LINUX_AMD64_SUCCESS
