#!/bin/sh
# Runs against the writable overlay, never the source firmware.
mkdir -p "$TARGET/etc/vm-disabled" "$TARGET/userdisk" "$TARGET/userdata/bin" "$TARGET/userdata/applog"
for script in S01DisableDebugUart S10async_commit.sh S21mountall.sh S40network S40rkaiq_3A S50-app-launcher S50launcher S50launcher.disabled S98usbdevice S99-auto-reboot S99_run_test_scripts S99input-event-daemon; do
    if [ -f "$TARGET/etc/init.d/$script" ]; then
        mv "$TARGET/etc/init.d/$script" "$TARGET/etc/vm-disabled/$script"
    fi
done
cp /patches/S50vm-ui "$TARGET/etc/init.d/S50vm-ui"
chmod 755 "$TARGET/etc/init.d/S50vm-ui"
# Compositor payload for the guest side to unpack (busybox tar, uncompressed).
if [ -f /patches/weston.tar ]; then
    cp -f /patches/weston.tar "$TARGET/userdata/weston.tar"
    echo "x6pro: weston payload staged"
fi
# Optional pre-initialised guest state (from a device/VM where the app finished its
# first-run initialisation). Drop userdata-seed.tar into the pack to use it.
if [ -f /patches/userdata-seed.tar ]; then
    tar xf /patches/userdata-seed.tar -C "$TARGET" 2>/dev/null && echo "x6pro: userdata seed applied"
fi
if [ -f /patches/desktop.tar ]; then
    cp -f /patches/desktop.tar "$TARGET/userdata/desktop.tar"
    echo "x6pro: desktop resources staged"
fi
# Keep the generic virtual network path; remove only the unavailable dropbear entry.
if [ ! -x "$TARGET/usr/sbin/dropbear" ]; then
    sed -i '\|::sysinit:/usr/sbin/dropbear |d' "$TARGET/etc/inittab"
fi
# The original fstab targets physical A/B partitions; initramfs owns VM mounts.
[ -e "$TARGET/etc/vm-disabled/fstab.original" ] || cp "$TARGET/etc/fstab" "$TARGET/etc/vm-disabled/fstab.original"
printf '# VM mounts are established by initramfs.\n' > "$TARGET/etc/fstab"
# Seed existing settings once because generic init mounts userdata separately.
if [ ! -e "$TARGET/userdata/.vm-seeded" ]; then
    cp -a /ro/userdata/. "$TARGET/userdata/" 2>/dev/null || true
    touch "$TARGET/userdata/.vm-seeded"
fi
printf 'x6pro: overlay prepared; source image remains read-only\n'