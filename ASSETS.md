# 资产获取步骤（本仓库不含版权内容）

> ⚠️ **警示**：下列资产含**网易有道**（固件/应用/资源）与第三方（Debian、Rockchip）的版权或授权内容。
> **请勿把它们提交到本仓库或任何公开仓库、请勿再分发。** 本仓库只提供**在你自己的设备上生成本地副本**的步骤。
> 商用一律禁止（见 [LICENSE](LICENSE)）。

## 1. 固件镜像 `boot_a.img` / `system_a.img`

两个来源，任选其一：

**A. 官方 OTA 包（公开下载，注意仍是厂商版权）**

```bash
# 上游仓库 lbdl0030/dictpen-rootfs 的 releases 里有本机型的 OTA 包：
#   RK3562_Melon-OTA-OS99.99.91  ->  RK3562_Melon-OTA-OS99.99.91.img (≈2027 MB)
gh release download RK3562_Melon-OTA-OS99.99.91 --repo lbdl0030/dictpen-rootfs --dir ./ota
# 解包得到分区镜像（OTA 包内一般含 boot/system 分区镜像或压缩包，按实际结构展开）
```

**B. 自己的设备**

```bash
# 通过设备自带的升级包或调试通道导出 boot/system 分区镜像；
# 导出后用 file/xxd 自检：boot 应为 U-Boot FIT（含 DTB），system 应为原始 ext4（superblock magic 0x53ef）
file boot_a.img system_a.img
md5sum boot_a.img system_a.img   # 与 packs/melon-pro/pack.toml 的 [checks] 对齐（不一致就改 checks 或换镜像）
```

放到位：`packs/melon-pro/images/boot_a.img`、`packs/melon-pro/images/system_a.img`。

## 2. 软件合成器载荷 `weston.tar`

厂商 Weston 依赖 Mali/RGA，QEMU 里跑不起来；本包用 Debian arm64 的 Weston 10 + Mesa libgbm + pixman 自建。生成方式（全自动）：

```bash
# 需要网络（能访问 deb.debian.org）与 host 上的 python
python tools/debfetch.py            # 下载并解出 Debian arm64 包到 work/weston-root
python tools/depclosure.py          # 计算依赖闭包（跳过 lib32/armhf），缺啥补啥
python tools/pack_weston2.py        # 组装最小集到 packs/melon-pro/weston/
python tools/pack_weston3.py        # 补 weston/libexec_weston.so（漏了合成器会静默不启动）
tar -cf packs/melon-pro/weston.tar -C packs/melon-pro/weston .
```

把结果放成 `packs/melon-pro/weston.tar`（包钩子会投送到 guest，`S50vm-ui` 负责解包启动）。
Debian 二进制按各自许可证（GPL/LGPL/BSD/MIT 等）分发，**保留其许可证文本**。

## 3. 桌面资源 `desktop.tar`

首页 mini-app 的页面 bundle 与图片（内容寻址的 `images/<hash>.png`）。本仓库不含它。

```bash
# 从你自己的设备导出：
#   /userdisk/miniapp/data/mini_app/pkg/<id>/a/   （<id> 取应用日志里的 topAppId）
# 打成未压缩 tar（guest 的 busybox tar 不支持 -z）：
tar -cf desktop.tar -C <导出的目录> .
```

放成 `packs/melon-pro/desktop.tar`；`S50vm-ui` 会把它解到 `pkg/<id>/a/`（当前脚本覆盖 3 个已知 id）。

## 4. OCR/NPU 桩库 `libyocr.so` / `libYoudaoStitch.so`（本地生成，勿分发）

应用启动会加载 `*.rknn.encrypt` 模型走 NPU，QEMU 无 NPU 会崩；需要对**你自己固件里的库**做本地桩化：

```bash
# 从固件 system 镜像里取出（路径固定）：
#   oem/YoudaoDictPen/output/libs/libyocr.so
#   oem/YoudaoDictPen/output/libs/libYoudaoStitch.so
KEEP_CTORS=1 python tools/a64stub.py \
    libyocr.so  packs/melon-pro/patches/libyocr.so \
    libYoudaoStitch.so  packs/melon-pro/patches/libYoudaoStitch.so
python tools/check_ctor.py packs/melon-pro/patches/libyocr.so   # 确认 DT_INIT 非 0
```

⚠️ **必须保留构造器**（`KEEP_CTORS=1`）：中和 `DT_INIT`/`DT_INIT_ARRAY` 会让应用启动即 SIGILL（该固件其它库依赖 `libyocr` 构造器）。
桩化产物是**厂商二进制的衍生品**，仅限本地使用，**不要提交、不要分发**。

## 5. 可选：`userdata-seed.tar`（跳过全新盘的首启初始化）

全新状态盘首启时应用会走一遍初始化（读设备身份、请求云端 store、校验 mini-app 包）。把一台**已完成首启初始化**的机器（真机最佳）的 guest 状态打包，即可让新盘直接进桌面：

```bash
# 在已初始化好的 guest 里：
tar -cf /userdata/userdata-seed.tar -C / userdata userdisk/miniapp
# 取出后放到 packs/melon-pro/userdata-seed.tar，并在 pack.toml 的 [adapt.replace] 里声明：
#   "userdata-seed.tar" = "/tmp/userdata-seed.tar"
```

包钩子 `prepare.sh` 会在 initramfs 阶段把它解到目标根，从而跳过首启初始化。

## 免责声明

以上步骤仅供**个人学习研究**。资产版权归**网易有道**及各自权利人；本项目与网易有道、Rockchip 无隶属关系。请遵守当地法律与设备授权，自行承担一切后果。
