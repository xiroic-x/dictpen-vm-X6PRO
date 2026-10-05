#!/bin/sh
echo -n 'weston_alive='; ps | grep -c '[b]in/weston'
echo -n 'app_alive='; ps | grep -c '[m]iniapp'
echo -n 'yocr_size='; ls -l /oem/YoudaoDictPen/output/libs/libyocr.so 2>/dev/null | awk '{print $5}'
echo -n 'stitch_size='; ls -l /oem/YoudaoDictPen/output/libs/libYoudaoStitch.so 2>/dev/null | awk '{print $5}'
echo -n 'desktop_marker='; ls /userdisk/miniapp/.desktop-installed 2>/dev/null | wc -l
echo -n 'dumps_now='; ls /userdisk/corefile/4.3.5 2>/dev/null | wc -l
echo -n 'img_errors='; grep -a -c WXImage /userdata/applog/vm-miniapp.log 2>/dev/null
echo 'app_tail:'; tail -8 /userdata/applog/vm-miniapp.log 2>/dev/null
echo 'weston_tail:'; tail -3 /userdata/applog/vm-weston.log 2>/dev/null