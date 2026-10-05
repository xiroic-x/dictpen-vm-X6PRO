#!/bin/sh
echo -n 'license='; ls -l /userdata/cfg/license 2>/dev/null | awk '{print $5}'
echo -n 'desktop_marker='; ls /userdisk/miniapp/.desktop-installed 2>/dev/null | wc -l
echo -n 'pkg_dirs='; ls /userdisk/miniapp/data/mini_app/pkg 2>/dev/null | wc -l
echo -n 'app_alive='; ps | grep -c '[m]iniapp'
echo -n 'img_errors='; grep -a -c WXImage /userdata/applog/vm-miniapp.log 2>/dev/null
echo -n 'bridge_dev='; ls /dev/input/by-path/axs_ts 2>/dev/null | wc -l
echo 'app_tail:'; tail -3 /userdata/applog/vm-miniapp.log 2>/dev/null
echo 'weston_tail:'; tail -2 /userdata/applog/vm-weston.log 2>/dev/null