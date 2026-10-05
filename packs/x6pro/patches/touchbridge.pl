#!/usr/bin/perl
# QEMU virtio-tablet (mouse) -> uinput touchscreen published as /dev/input/by-path/axs_ts.
# The pen UI only reacts to BTN_TOUCH touch events; coordinates are scaled to the
# UI canvas (ABS_X 0..W-1, ABS_Y 0..H-1) so taps land 1:1 on UI pixels.
use strict;
use warnings;
use Fcntl;

$| = 1;    # unbuffered: this process never exits, so prints must flush

my ($W, $H) = @ARGV;
$W = 960 unless defined $W;
$H = 266 unless defined $H;

my $UI_SET_EVBIT   = 0x40045564;
my $UI_SET_KEYBIT  = 0x40045565;
my $UI_SET_ABSBIT  = 0x40045567;
my $UI_DEV_SETUP   = 0x405c5503;
my $UI_DEV_CREATE  = 0x00005501;
my $UI_SET_PHYS    = 0x40045502;
my $EV_SYN = 0; my $EV_KEY = 1; my $EV_ABS = 3;
my $SYN_REPORT = 0;
my $ABS_X = 0; my $ABS_Y = 1; my $ABS_MT_SLOT = 0x2f; my $ABS_MT_POSITION_X = 0x35;
my $ABS_MT_POSITION_Y = 0x36; my $ABS_MT_TRACKING_ID = 0x39;
my $BTN_TOUCH = 0x14a; my $BTN_LEFT = 0x110; my $BTN_TOOL_FINGER = 0x145;
my $LINK = '/dev/input/by-path/axs_ts';

sub find_tablet {
    open(my $fh, '<', '/proc/bus/input/devices') or return undef;
    my $name;
    while (my $line = <$fh>) {
        $name = $1 if $line =~ /^N: Name="(.*)"/;
        if ($line =~ /^H: Handlers=.*\b(event\d+)\b/) {
            my $node = $1;
            if (defined $name && $name =~ /Tablet/i) {
                close($fh);
                return '/dev/input/' . $node;
            }
        }
    }
    close($fh);
    return undef;
}

sub events_now {
    my @e = glob('/dev/input/event*');
    my %h; $h{$_} = 1 for @e;
    return %h;
}

my $src = find_tablet();
die "no virtio tablet found\n" unless $src;
print "touchbridge: source $src, canvas ${W}x${H}\n";

my %before = events_now();
my $u;
sysopen($u, '/dev/uinput', O_WRONLY | O_NONBLOCK) or die "open /dev/uinput: $!\n";
ioctl($u, $UI_SET_EVBIT, pack('i', $EV_KEY));
ioctl($u, $UI_SET_EVBIT, pack('i', $EV_ABS));
ioctl($u, $UI_SET_EVBIT, pack('i', $EV_SYN));
foreach my $k ($BTN_TOUCH, $BTN_TOOL_FINGER) { ioctl($u, $UI_SET_KEYBIT, pack('i', $k)); }
foreach my $a ($ABS_X, $ABS_Y, $ABS_MT_SLOT, $ABS_MT_POSITION_X, $ABS_MT_POSITION_Y, $ABS_MT_TRACKING_ID) {
    ioctl($u, $UI_SET_ABSBIT, pack('i', $a));
}
my $phys = 'axs_ts';
ioctl($u, ($UI_SET_PHYS | ((length($phys) + 1) << 16)), $phys);
my $name = 'axs_ts';
my $setup = pack('S<S<S<S<', 0x03, 0x1d6b, 0x0103, 1) . $name . ("\0" x (80 - length($name))) . pack('L<', 0);
ioctl($u, $UI_DEV_SETUP, $setup) or die "UI_DEV_SETUP: $!\n";
ioctl($u, $UI_DEV_CREATE, 0) or die "UI_DEV_CREATE: $!\n";
print "touchbridge: uinput device created\n";

my $new;
for my $i (1 .. 40) {
    if (-e $LINK) { $new = readlink($LINK); last; }
    for my $e (glob('/dev/input/event*')) {
        next if $before{$e};
        $new = $e;
    }
    last if $new;
    select(undef, undef, undef, 0.25);
}
if (!$new) { print "touchbridge: no new event node\n"; }
elsif (!-e $LINK) {
    mkdir '/dev/input/by-path' unless -d '/dev/input/by-path';
    symlink($new, $LINK) and print "touchbridge: linked $LINK -> $new\n";
}

my $ev;
sysopen($ev, $src, O_RDONLY | O_NONBLOCK) or die "open $src: $!\n";
my ($rx, $ry) = (0, 0);
my $down = 0;
sub emit {
    my $buf = '';
    foreach my $it (@_) { $buf .= pack('q<q<S<S<l<', 0, 0, $it->[0], $it->[1], $it->[2]); }
    $buf .= pack('q<q<S<S<l<', 0, 0, $EV_SYN, $SYN_REPORT, 0);
    syswrite($u, $buf);
}
sub scaled { my ($v, $max, $out) = @_; return int($v * ($out - 1) / $max + 0.5); }

print "touchbridge: ready\n";
my $btn = 0;
my $seen_abs = 0;
while (1) {
    my $n = sysread($ev, my $data, 24);
    if (!defined $n || $n < 24) { select(undef, undef, undef, 0.02); next; }
    my ($s, $us, $type, $code, $value) = unpack('q<q<S<S<l<', $data);
    if ($type == $EV_ABS) {
        if ($code == $ABS_X) { $rx = $value; $seen_abs = 1; }
        if ($code == $ABS_Y) { $ry = $value; $seen_abs = 1; }
    } elsif ($type == $EV_KEY && $code == $BTN_LEFT) {
        $btn = $value;
    } elsif ($type == $EV_SYN && $code == $SYN_REPORT) {
        # Commit on the frame boundary so the position of this batch is used.
        if ($btn && !$down && !$seen_abs) {
            # First press before any absolute position: wait one frame for ABS_*.
        } elsif ($btn && !$down) {
            my $px = scaled($rx, 32767, $W);
            my $py = scaled($ry, 32767, $H);
            $down = 1;
            emit([$EV_ABS, $ABS_MT_SLOT, 0], [$EV_ABS, $ABS_MT_TRACKING_ID, 1],
                 [$EV_KEY, $BTN_TOOL_FINGER, 1], [$EV_KEY, $BTN_TOUCH, 1],
                 [$EV_ABS, $ABS_X, $px], [$EV_ABS, $ABS_Y, $py],
                 [$EV_ABS, $ABS_MT_POSITION_X, $px], [$EV_ABS, $ABS_MT_POSITION_Y, $py]);
            print "touchbridge: down $px,$py\n";
        } elsif (!$btn && $down) {
            $down = 0;
            emit([$EV_KEY, $BTN_TOUCH, 0], [$EV_KEY, $BTN_TOOL_FINGER, 0], [$EV_ABS, $ABS_MT_TRACKING_ID, -1]);
            print "touchbridge: up\n";
        }
    }
}