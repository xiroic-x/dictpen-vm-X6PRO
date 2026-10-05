#!/bin/sh
killall -9 miniapp 2>/dev/null; killall -9 guardian_run 2>/dev/null
sleep 1
echo '=== A: clean env, no profile ==='
env -i sh -c 'export PATH=/usr/sbin:/usr/bin:/sbin:/bin XDG_RUNTIME_DIR=/run/debweston WAYLAND_DISPLAY=wayland-0 LD_LIBRARY_PATH=/oem/YoudaoDictPen/output/libs:/etc/miniapp/jsapis:/etc/miniapp/messageknife; cd /oem/YoudaoDictPen/output; exec /usr/bin/miniapp' >/tmp/A.log 2>&1 &
sleep 12
echo -n 'A_alive='; ps | grep -c '[m]iniapp'
echo 'A_tail:'; tail -3 /tmp/A.log
killall -9 miniapp 2>/dev/null
sleep 1
echo '=== B: login shell (sources /etc/profile) ==='
env -i sh -lc 'cd /oem/YoudaoDictPen/output; export XDG_RUNTIME_DIR=/run/debweston WAYLAND_DISPLAY=wayland-0 LD_LIBRARY_PATH=/oem/YoudaoDictPen/output/libs:/etc/miniapp/jsapis:/etc/miniapp/messageknife; exec /usr/bin/miniapp' >/tmp/B.log 2>&1 &
sleep 12
echo -n 'B_alive='; ps | grep -c '[m]iniapp'
echo 'B_tail:'; tail -3 /tmp/B.log
killall -9 miniapp 2>/dev/null