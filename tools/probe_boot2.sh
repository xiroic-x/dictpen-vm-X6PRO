#!/bin/sh
echo -n 'desktop_tar='; ls -l /userdata/desktop.tar 2>/dev/null | awk '{print $5}'
echo -n 'desktop_marker='; ls /userdisk/miniapp/.desktop-installed 2>/dev/null | wc -l
echo -n 'pkg_target_dirs='; ls /userdisk/miniapp/data/mini_app/pkg/8080222437664451/a/images 2>/dev/null | wc -l
echo -n 'app_alive='; ps | grep -c '[m]iniapp'
echo -n 'img_errors='; grep -a -c WXImage /userdata/applog/vm-miniapp.log 2>/dev/null
echo -n 'cfg_init='; grep -a -c -i '初始化配置' /userdata/applog/vm-miniapp.log 2>/dev/null
echo 'tail:'; tail -4 /userdata/applog/vm-miniapp.log 2>/dev/null