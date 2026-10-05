# 固件包：melon-pro（RK3562 Melon / Linux ext4）

`boot_a.img` + `system_a.img` 在本框架里运行的**全部**适配内容。框架只增加了一个 runtime
（`scripts/runtimes/rockchip_ext4.py`）与一条 runtime 注册；`dpctl.py` / `initramfs-init.sh` / `vmgui` 的核心逻辑未改。

## 1. 平台识别（证据链）

| 事实 | 证据 |
|------|------|
| 平台 | boot 是 U-Boot FIT（arm64 kernel + DTB + resource 多镜像，sha256,rsa2048 签名）；DTB `model = Rockchip RK3562 MELON LP4 V10 Board` |
| 系统 | `system_a.img` 是**原始 ext4**（非 erofs/稀疏，superblock magic 0x53ef）；`etc/os-release` 指向 Melon_pro_Package / RK3562-SDK、`rk3562_linux_melon_pro_defconfig` |
| 版本 | `/Version`：`DictPen_APP Version 4.3.5`，Build 2025-11-26 |
| 面板 | DSI `panel@0/1` 时序 `hactive=480 vactive=960`；`etc/xdg/weston/weston.ini` 对 DSI-1 做 rotate-90；`cfg.json` 逻辑屏 `width=960 height=266 direction=270 yoffset=107`（= (480-266)/2） |
| 用户态 | aarch64 + glibc 2.36（`libc.so.6` 导出到 GLIBC_2.36），因此可直接使用 Debian bookworm arm64 二进制 |
| 图形栈 | **ARM Mali（libmali）+ Rockchip RGA**：`libmali-bifrost-g52-g13p0-wayland-gbm.so`、`librga.so.2`；无 Mesa、无 `/usr/lib/dri` |

镜像来源：上游 release [X6pro](https://github.com/lbdl0030/dictpen-rootfs/releases/tag/X6pro)（`X6pro-firmware-OS4.3.5`，镜像包由 **@xiroic-x** 提供，感谢分享）；其中 `X6pro_boot_ext4.img` 与本包 `boot_a.img` 的 MD5 已核对一致。

镜像校验（`[checks]`，本地计算）：

| 文件 | MD5 |
|------|-----|
| `boot_a.img` | `5a1129a5bd70cf3099b793e512aabb57` |
| `system_a.img` | `db313878a4a151e140d9be7cca287e5d` |

## 2. 引导适配

- runtime `rockchip-linux-ext4`：只读挂 ext4 根（`DICTPEN_ROOTFSTYPE=ext4` 由 runtime 追加），其余走框架既有 overlay/状态盘路径；`validate()` 检查 rootfs 是原始 ext4 而不是 erofs。
- `patches/prepare.sh`（initramfs 钩子，跑在 overlay 上，不动源镜像）：停用实机专用的 `S21mountall.sh`、`S40network`（`/dev/block/by-name/*` 与 bes2600 在 QEMU 不存在）、`S50-app-launcher`、`S98usbdevice`、`S99-auto-reboot` 等；安装 `S50vm-ui`；把合成器载荷投送到 `/userdata/weston.tar`。
- `patches/get_pcba_version` 固定返回 `RK3562_Melon_V0`（原实现读 `/proc/device-tree/model`，与 QEMU 的 DTB 不符），使固件自身的板型分支与真机一致。

## 3. 显示：为什么必须换掉厂商 Weston

**症状**：厂商 Weston 11.0.1 能枚举 EDID、能发现 head，但每条输出都停在 `Failed to init output pixman state`，屏幕全黑。

**取证**：

1. ftrace `function_graph` + kretprobe 追 DRM 调用：`drm_mode_create_dumb_ioctl`、`drm_mode_addfb2_ioctl`、`drm_mode_setcrtc`、`drm_mode_mmap_dumb_ioctl`、`drm_gem_mmap` **全部返回 0**（`kprobes/* arg1=0x0`）——内核侧无问题，失败在用户态。
2. `libweston-11/drm-backend.so` 的 `DT_NEEDED` 含 `librga.so.2` + `libmali.so.1`，并含 `c_RkRgaInit` / `rga not supported` 字样；`/etc/profile.d/pixman.sh` 默认 `PIXMAN_USE_RGA=1`；而 QEMU 没有 `/dev/rga`。
3. 该机 `libgbm.so.1` 是 5.7KB 的 Mali 转发壳（`libmali_hook.so.1` → `libmali.so.1`，需 `/dev/mali`），用 `MALI_DEFAULT_WINSYS` 选后端；QEMU 无 Mali 内核态。

**结论**：这台固件的合成路径两条腿都在 Rockchip 专有硬件上——GL 要 Mali、pixman 要 RGA；QEMU 上两者都不存在，厂商 Weston 在虚拟机里没有可用的软件路径。

**对策（全部在包内，不改框架）**：用 Debian bookworm arm64 的 **Weston 10.0.1 + Mesa libgbm + pixman** 做纯软件合成，载荷随包分发（`weston.tar`，26MB；`[adapt].replace` 投送 → `prepare.sh` 落盘 → `S50vm-ui` 解包并启动）。

关键细节（都踩过）：

- 载荷必须含 `weston/libexec_weston.so.0`（`weston` 与 `kiosk-shell.so` 的依赖）——漏掉时合成器静默不启动；
- Debian 的 Weston 10 接 **logind（libsystemd）**而非 seatd；guest 没有 logind，必须 `--tty=1` 走 direct launcher 才能拿到 DRM master；
- socket 用 `--socket=wayland-0` 固定（否则会是 `wayland-1`，应用连不上）；
- **库隔离**：合成器用 `LD_LIBRARY_PATH=/userdata/debweston/...`，应用只用固件自己的 `/oem/YoudaoDictPen/output/libs:/etc/miniapp/jsapis:/etc/miniapp/messageknife`；混用会让应用加载到 Debian 的 `libfreetype`，进而缺 `libbrotlidec.so.1`（固件里没有这个库）而启动失败。

## 4. 已验证（干净状态盘 `up --fresh`）

| 项 | 证据 |
|----|------|
| 包校验 / runtime / MD5 | `dpctl packs melon-pro` 全部就位 |
| ext4 根 + 持久化 overlay + switch_root | 串口 `### ext4 root mounted ###`、`### state: ext4 created and mounted ###`、`### overlay: persistent upper ###`、`### switch_root -> /mnt, init /sbin/init ###` |
| 开发凭证 | `S00license: dev license written (174 bytes)`；`/userdata/cfg/license` 174 字节 |
| 合成器 | `S50vm-ui` 后 socket `/run/debweston/wayland-0` 就绪；`vm-weston.log`：`DRM: output Virtual-1 uses shadow framebuffer`、`Output 'Virtual-1' enabled with head(s) Virtual-1` |
| 应用接入 | `vm-miniapp*.log`：`wayland handle_global interface(wl_shm/xdg_wm_base/...)`、`WLNativeWindow::setSurfaceSize(960,480)`、`xdg_surface_configure`、`setSize(960,266)`、`setPosition(0,107)` |
| 界面像素 | `vm/melon-ui5.png`：固件真实 UI 上屏（激活页按钮），UI 条带位于 y=107 的 960×266 区域 |
| 触控（鼠标→触摸桥） | 自研 `patches/touchbridge.pl`：uinput 设备 name/phys=axs_ts → `/dev/input/by-path/axs_ts -> /dev/input/event2`；`dpctl tap 300 150` → 桥日志 `down 300,83`、`tap 600 350` → `down 599,193`（UI 像素坐标） |
| 桌面全渲染 | `vm/melon-home2.png`：查词翻译 / 语法精讲 / 随身听 三张卡片完整（960×266 条带，y=107）；资源来自 `vm/vm/desktop_x`（178 张图 + 页面 bundle），装入 `pkg/<id>/a/`（id 取应用日志的 topAppId：8080222437664451 / 8080252464522508）后图片错误从数百次降到 15 次 |
| 渲染耗时 | 应用启动 → 首帧全渲染 ≈ **77 s**（采样：65.2 s 仍是合成器背景，76.8 s 出现 315 KB 全渲染帧；TCG 纯软件模拟） |
| 越过激活 | 带开发凭证后日志出现 `Pin=Develop=homeModeIconShow=false` 与 30s 周期 `Message insert` 主循环 → 应用已进入首页逻辑 |

## 5. 未完成（按证据排序）

1. **首页绘画**：应用已进首页逻辑，但画面只有合成器背景，日志反复 `WXImage::onLoad failed, src=images/<hash>.png`。即 mini-app 包不完整：我从 `/etc/miniapp/resources/presetpkgs/*.amr` 手工解包到 `/userdisk/miniapp/data/mini_app/pkg/<id>/a/`，zip 内只有 `app.js.bin`/`index.js.bin`/`app_icon.png`，没有 `images/`。下一步应让固件自己的 `ResourceManager` 完成安装（它是正主），或补齐资源。
2. **触控**：`cfg.json` 的 `tp=/dev/input/by-path/platform-4020000.i2c-event` 在 QEMU 不存在；按 s6pro/a7pro/x7 的做法用 `[adapt].touchbridge`（本 guest 有 perl）+ `cfg_overlay` 把 `tp` 指到桥节点。
3. 面板归一化（可选）：x7 的先例是把 `direction`/偏移归零、`[display]` 声明成 UI 逻辑尺寸；本包当前保留 `cfg.json` 原值（实测应用在 960×480 输出上把 UI 正确画在 y=107）。

### 5.1 增量（同日深夜）

1. **全新状态盘的首启初始化不完成**：新盘第一次开机时固件停在自带 splash「正在初始化配置，请等待…」（>3 分钟不推进，补起 ResourceManager / SoundPlayer 也一样）。崩点前日志停在 `yocr_ncnn` 加载 `/oem/.../melon-pro-rec-32x1280-v9.0.1.2.rknn.encrypt` 并落 `YBreakpad` dump → OCR/NPU 初始化链在 QEMU 上不可用，与 s7pro README 同类（s7pro 的解法是把 `libyocr.so` 全导出桩化 + 中和构造器，让应用走 OCR 不可用容忍路径）。
2. 已初始化的状态盘上，应用能正常进桌面并按上表渲染；当前可复现路径是：用已初始化的状态盘（勿加 `--fresh`）启动并拉起应用。
3. 触控已完成（见上表）：桥脚本随包分发，`[adapt].touchbridge` + `cfg_overlay` 把 `tp` 指到 `/dev/input/by-path/axs_ts` 且 `tp_direction/tp_xoffset/tp_yoffset` 归零。


### 5.2 验收结论（本会话最终）

**已达成**：显示链路 + 固件真实 UI 全渲染。`vm/melon-home2.png` 是完整桌面（查词翻译 / 语法精讲 / 随身听 三张卡片，960×266 条带居中在 y=107）。渲染耗时为实测两轮独立数据：

| 轮次 | 应用启动 → 首帧全渲染 | 证据 |
|------|----------------------|------|
| 1 | ≈ 77 s | 65.2 s 仍是合成器背景（2843 B），76.8 s 出现 319 KB 全渲染帧 |
| 2 | ≈ 64 s | 41 s 背景，64 s 出现 218 KB 渲染帧 |

**未闭环**：全新状态盘的首启初始化。表现与证据：应用会进入自带 splash「正在初始化配置，请等待…」，日志显示它在做首启流程（`YLoginModule` 读 `/userdata/DictPenData/userId` 失败、`YHttpCommonParams` 使用 fallback 身份 `deviceSku=OVERHEAD_X62_SKU_CHN_PRO model=YDPX6-2 deviceSn=vendor_storage`、POST `https://hardware-iot.youdao.com/app/store/version/info/batch`，并逐个包校验 `pkg/<id>/a/libs/`），随后或停在 splash，或干净退出/段错误并落 Breakpad dump 到 `/userdisk/corefile/4.3.5/miniapp-*.dmp`（本轮 dump：`miniapp-20261005235623.dmp`）。

原因分类：应用自状态 + 设备身份。`vendor_storage` 在 QEMU 不存在，应用走 fallback SKU；首启那轮云端交互与自身状态写入在 TCG 慢速环境下没有稳定完成（DNS 通，`hardware-iot.youdao.com` 解析到 `luna-gz.alb.ntes53.netease.com`）。

**已内置的闭合手段**：`prepare.sh` 支持 `userdata-seed.tar`——把一台已完成首启初始化的机器（真机最佳）的 `/userdata` 与 `/userdisk/miniapp` 打成一包，声明到 `[adapt].replace`（源名 `userdata-seed.tar`），包钩子会在 initramfs 阶段解到 $TARGET，让全新状态盘跳过首启初始化。这是把该问题交给真机状态即可闭合的工程解。

### 5.3 OCR 桩化的关键约束

- 桩化 `libyocr.so` / `libYoudaoStitch.so` 的导出函数是必须的（否则模型加载链在 QEMU 崩）；但**必须保留构造器**（`DT_INIT` / `DT_INIT_ARRAY` / `DT_INIT_ARRAYSZ` 原样）。
- 实测：中和构造器 → 应用启动即 SIGILL（Illegal instruction）；保留构造器 → 应用正常起来并能进桌面。包内当前为保留构造器版本（`DT_INIT=513992`）。
- 桩化规则：函数名含 init/open/create/load/setup/start/connect/begin/prepare/config → 返回 -1，其余返回 0；文件大小不变、仅就地覆写。
## 6. 复现

```powershell
python scripts\dpctl.py packs melon-pro
python scripts\dpctl.py up --pack melon-pro --headless
python scripts\dpctl.py wait --timeout 240
python scripts\dpctl.py screenshot --out vm\melon.png
python scripts\dpctl.py sh --serial -c \"tail -3 /userdata/applog/vm-weston.log\"
```

本轮用的离线工具：`vm/work/depclosure.py`（依赖闭包）、`vm/work/debfetch.py`（Debian arm64 取包）、`vm/work/serial_ctrlc.py`（解卡串口）。

## 7. 坑

- 串口上不要让后台进程继承 stdout（`cmd | tail` 永远等不到 EOF，控制台被卡死）；后台一律 `>/file 2>&1 &`。
- `&` 后面不能紧跟 `;`（busybox ash 报 syntax error）。
- guest 的 busybox `tar` 不支持 `-z`，载荷用未压缩 tar。
- guest 的 lib32（armhf）库会让静态依赖检查误判已满足，算闭包前要先排除 `lib32` 与 `armhf`。
- `adb` 通道可用（`tools/platform-tools/adb.exe`）；SSH 在个别状态下 banner exchange 失败，串口兜底。
- **Perl 长驻进程必须 `$|=1`**：stdout 缓冲会让 print 永不落盘（桥看起来没日志，其实是没 flush）。
- Perl 的 `$1` 会被后续正则覆盖：`if ($line =~ /(event\d+)/ && $name =~ /Tablet/i)` 中第二个匹配清空 `$1` → 先存局部变量再判断。
- `pkill -f 关键字` 会匹配到自己的命令行 → 自杀；用精确 pid 或 `killall`。
- 串口控制台会打乱带变量的长命令；关键步骤拆短，或写成脚本投送后执行。
- 包内多份载荷必须在 initramfs 钩子里逐个投送（只加 `[adapt].replace` 声明不够）——`desktop.tar` 就漏投过一次。

## 8. 版权

镜像版权归**网易有道**；包内合成器为 Weston（**MIT 许可证**，含 10 及所有版本）+ 其依赖库（各自许可）。`weston.tar` 与 `images/` 均不进可传播代码包。
