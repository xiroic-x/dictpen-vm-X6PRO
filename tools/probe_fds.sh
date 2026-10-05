#!/bin/sh
W=$(pidof weston | awk '{print $1}')
M=$(pidof miniapp | awk '{print $1}')
echo "pids weston=$W miniapp=$M"
echo -n 'weston_shm_fds='; ls -l /proc/$W/fd 2>/dev/null | grep -c -e shm -e memfd -e haasui
echo -n 'miniapp_shm_fds='; ls -l /proc/$M/fd 2>/dev/null | grep -c -e shm -e memfd -e haasui
echo -n 'app_image_errors='; grep -a -c WXImage /userdata/applog/vm-home2.log 2>/dev/null
echo -n 'app_lines='; wc -l < /userdata/applog/vm-home2.log 2>/dev/null
echo 'app_tail:'; tail -3 /userdata/applog/vm-home2.log 2>/dev/null
echo -n 'weston_enabled='; grep -a -c 'enabled with head' /userdata/applog/vm-weston.log 2>/dev/null