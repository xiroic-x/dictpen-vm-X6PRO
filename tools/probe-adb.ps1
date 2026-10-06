$ErrorActionPreference = 'Continue'
$adb = Join-Path $PWD 'tools\platform-tools\adb.exe'
if (-not (Test-Path $adb)) { Write-Output ('NO ADB AT ' + $adb); exit 1 }
Write-Output '--- devices ---'
& $adb devices
Write-Output '--- input devices ---'
& $adb shell "cat /proc/bus/input/devices | grep -e '^N: Name' -e Handlers"
Write-Output '--- udev props of event2 ---'
& $adb shell 'udevadm info /dev/input/event2 2>/dev/null | grep -e ID_INPUT'
Write-Output '--- app fd on input nodes ---'
& $adb shell 'M=$(pidof miniapp); echo pid=$M; ls -l /proc/$M/fd 2>/dev/null | grep -c event'
Write-Output '--- weston fd on input nodes ---'
& $adb shell 'W=$(pidof weston); echo pid=$W; ls -l /proc/$W/fd 2>/dev/null | grep -c event'