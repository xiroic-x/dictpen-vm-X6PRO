#!/bin/sh
killall -9 miniapp 2>/dev/null
sleep 1
export XDG_RUNTIME_DIR=/run/debweston
export WAYLAND_DISPLAY=wayland-0
export LD_LIBRARY_PATH=/oem/YoudaoDictPen/output/libs:/etc/miniapp/jsapis:/etc/miniapp/messageknife
cd /oem/YoudaoDictPen/output
echo '--- foreground run (40s max) ---'
timeout 40 /usr/bin/miniapp 2>&1 | tail -12
echo "exit=$?"
echo '--- dmesg ---'
dmesg | tail -5