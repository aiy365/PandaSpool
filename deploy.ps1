
wsl -e bash -c "scp /mnt/c/work/3D模型/printpilot-hub/dist/printpilot root@3d.bstccc.cn:/tmp/printpilot"
wsl -e bash -c "ssh root@3d.bstccc.cn 'mv /tmp/printpilot /usr/local/bin/printpilot && chmod +x /usr/local/bin/printpilot && systemctl restart printpilot'"

