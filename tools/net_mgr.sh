#!/bin/sh
killall -q wifi-manager 2>/dev/null
mkdir -p /userdata/cfg /var/run/wpa_supplicant
cat > /userdata/cfg/wpa_supplicant.conf <<'EOF'
ctrl_interface=/var/run/wpa_supplicant
update_config=1
network={
    ssid="Youdao-VM"
    key_mgmt=NONE
}
EOF
cp -f /userdata/cfg/wpa_supplicant.conf /userdata/wpa_supplicant-vm.conf
printf 'wifi opend\n' > /dev/bes2600
killall -q wpa_supplicant 2>/dev/null
sleep 1
setsid /usr/sbin/wpa_supplicant -Dnl80211 -iwlan0 -c/userdata/cfg/wpa_supplicant.conf -f /userdata/applog/vm-wpa.log >/dev/null 2>&1 < /dev/null &
n=0; while [ $n -lt 25 ]; do /usr/sbin/wpa_cli -iwlan0 status 2>/dev/null | grep -q COMPLETED && break; n=$((n+1)); sleep 1; done
echo -n 'before_mgr='; /usr/sbin/wpa_cli -iwlan0 status 2>/dev/null | grep -e wpa_state -e ^ssid | tr '\n' ' '
setsid /usr/bin/wifi-manager >/userdata/applog/vm-wifimgr.log 2>&1 < /dev/null &
sleep 18
echo -n 'after_mgr='; /usr/sbin/wpa_cli -iwlan0 status 2>/dev/null | grep -e wpa_state -e ^ssid | tr '\n' ' '
echo -n 'addr='; ip addr show wlan0 2>/dev/null | grep -o 'inet [0-9.]*' | tr '\n' ' '
echo -n 'mgr_alive='; ps | grep -c '[w]ifi-manager'
echo '--- mgr log ---'; tail -6 /userdata/applog/vm-wifimgr.log 2>/dev/null