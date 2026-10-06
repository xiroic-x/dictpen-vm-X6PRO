#!/bin/sh
mkdir -p /etc/udev/rules.d
cat > /etc/udev/rules.d/99-axs-ts.rules <<'EOF'
# x6pro: the emulated touch node must look like a touchscreen, not a touchpad.
ACTION=="add|change", SUBSYSTEM=="input", ATTRS{name}=="axs_ts", ENV{ID_INPUT}="1", ENV{ID_INPUT_TOUCHSCREEN}="1", ENV{ID_INPUT_TOUCHPAD}="0"
EOF
udevadm control --reload-rules 2>/dev/null || true
udevadm trigger --subsystem-match=input --action=change 2>/dev/null || true
sleep 2
echo -n 'props: '; udevadm info /dev/input/event2 2>/dev/null | grep -e ID_INPUT | tr '\n' ' '
killall -9 miniapp 2>/dev/null
sleep 2
export XDG_RUNTIME_DIR=/run/debweston; export WAYLAND_DISPLAY=wayland-0; export LC_ALL=zh_CN.utf8
export LD_LIBRARY_PATH=/oem/YoudaoDictPen/output/libs:/etc/miniapp/jsapis:/etc/miniapp/messageknife
cd /oem/YoudaoDictPen/output
setsid /usr/bin/miniapp >/userdata/applog/vm-ux2.log 2>&1 < /dev/null &
echo RESTARTED