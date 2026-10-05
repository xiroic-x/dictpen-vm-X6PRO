#!/bin/sh
# Probe which DRM/KMS calls fail while Weston's pixman path initialises.
mount -t debugfs none /sys/kernel/debug 2>/dev/null
T=/sys/kernel/tracing
[ -d "$T" ] || T=/sys/kernel/debug/tracing
cd "$T" || exit 9
echo 0 > tracing_on
echo > trace
echo > kprobe_events 2>/dev/null
echo "--- filter functions present (1 = exists) ---"
for f in drm_mode_create_dumb_ioctl drm_mode_map_dumb_ioctl drm_mode_addfb2_ioctl drm_mode_addfb_ioctl drm_mode_setcrtc drm_mode_atomic_ioctl; do
    printf '%s ' "$f"
    grep -c "^$f" available_filter_functions 2>/dev/null || echo 0
done
echo 'r:dumbres drm_mode_create_dumb_ioctl $retval' >> kprobe_events 2>/dev/null
echo 'r:mapres drm_mode_map_dumb_ioctl $retval' >> kprobe_events 2>/dev/null
echo 'r:addfbres drm_mode_addfb2_ioctl $retval' >> kprobe_events 2>/dev/null
echo 'r:addfb1res drm_mode_addfb_ioctl $retval' >> kprobe_events 2>/dev/null
echo 'r:crtcres drm_mode_setcrtc $retval' >> kprobe_events 2>/dev/null
echo 'r:atomres drm_mode_atomic_ioctl $retval' >> kprobe_events 2>/dev/null
echo "--- installed probes ---"
cat kprobe_events
echo 1 > events/kprobes/enable 2>/dev/null
echo 1 > tracing_on
export WESTON_DISABLE_ATOMIC=1
export XDG_RUNTIME_DIR=/run/vm-wayland
mkdir -p "$XDG_RUNTIME_DIR"
pkill -f weston
sleep 1
/usr/bin/weston --backend=drm-backend.so --renderer=pixman --idle-time=0 > /userdata/applog/wtrace.out 2>&1 &
sleep 10
pkill -f weston
sleep 1
echo 0 > tracing_on
echo "=== KPROBE RETURNS ==="
grep -E "res:" trace | head -40
echo "=== KMS FRAMEBUFFERS ==="
cat /sys/kernel/debug/dri/0/framebuffer 2>/dev/null | head -6
echo "=== WESTON LOG TAIL ==="
tail -8 /userdata/applog/wtrace.out
