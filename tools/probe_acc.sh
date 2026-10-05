#!/bin/sh
echo -n 'app_alive='; ps | grep -c '[m]iniapp'
echo -n 'sysconfig_alive='; ps | grep -c '[r]unSysconfigMgr'
echo -n 'desktop_marker='; ls /userdisk/miniapp/.desktop-installed 2>/dev/null | wc -l
echo -n 'pkgs='; ls /userdisk/miniapp/data/mini_app/pkg 2>/dev/null | wc -l
echo -n 'imgs_8001='; ls /userdisk/miniapp/data/mini_app/pkg/8001661999525016/a/images 2>/dev/null | wc -l
echo -n 'app_lines='; wc -l < /userdata/applog/vm-miniapp.log 2>/dev/null
echo 'app_tail:'; tail -5 /userdata/applog/vm-miniapp.log 2>/dev/null