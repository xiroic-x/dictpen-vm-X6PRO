#!/bin/sh
M=$(pidof miniapp | awk '{print $1}')
W=$(pidof weston | awk '{print $1}')
echo "miniapp=$M weston=$W"
echo '--- app fds on input devices ---'
ls -l /proc/$M/fd 2>/dev/null | grep -c -e 'input/event' -e axs_ts
echo '--- weston fds on input devices ---'
ls -l /proc/$W/fd 2>/dev/null | grep -c -e 'input/event'
echo '--- udev class of the touch node ---'
udevadm info /dev/input/event2 2>/dev/null | grep -e 'ID_INPUT' -e 'DEVNAME' | tr '\n' ' '
echo
echo '--- app log: input/page hints ---'
L=$(ls -t /userdata/applog/vm-*.log 2>/dev/null | head -1)
echo "log=$L lines=$(wc -l < $L 2>/dev/null)"
grep -a -i -e 'touch' -e 'pointer' -e 'jump' -e 'page' -e 'home' $L 2>/dev/null | tail -6 | cut -c1-120
echo '--- weston log: input devices ---'
grep -a -i -e 'input device' -e 'touch' -e 'libinput' /userdata/applog/vm-weston.log 2>/dev/null | tail -5 | cut -c1-120