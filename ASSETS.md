# 资产获取步骤（本仓库不含版权内容）

> ⚠️ **警示**：下列资产含**网易有道**（固件/应用/资源）与第三方（Debian、Rockchip）的版权或授权内容。
> **请勿把它们提交到本仓库或任何公开仓库、请勿再分发。** 本仓库只提供**在你自己的设备上生成本地副本**的步骤。
> 许可：本项目采用 PolyForm Noncommercial License 1.0.0，条款见 [LICENSE](LICENSE)。

## 1. 固件镜像 `boot_a.img` / `system_a.img`

来源：上游 release **[X6pro](https://github.com/lbdl0030/dictpen-rootfs/releases/tag/X6pro)**（词典笔 OS 4.3.5，ext4 版本）。取用前请先阅读该 release 页面自身的说明（设备型号、分区说明、大文件的下载方式）。

对应到本包（下列 MD5 取自 release 页面公布的校验表，与本包 `pack.toml` 的 `[checks]` 完全一致）：

| 上游文件名 | 本包位置 | MD5 |
|------------|----------|-----|
| `X6pro_boot_ext4.img`（16 MB） | `images/boot_a.img` | `5a1129a5bd70cf3099b793e512aabb57` |
| `X6pro_rootfs_ext4.img` | `images/system_a.img` | `db313878a4a151e140d9be7cca287e5d` |

```bash
gh release download X6pro --repo lbdl0030/dictpen-rootfs --dir ./fw   # 取 boot 镜像
# 根文件系统镜像按 release 页面说明取回后：
cp ./fw/X6pro_boot_ext4.img   packs/x6pro/images/boot_a.img
cp ./fw/X6pro_rootfs_ext4.img packs/x6pro/images/system_a.img
file ./fw/X6pro_boot_ext4.img ./fw/X6pro_rootfs_ext4.img   # boot 应为 U-Boot FIT；rootfs 应为原始 ext4（magic 0x53ef）
md5sum packs/x6pro/images/boot_a.img packs/x6pro/images/system_a.img
```

校验值对不上就说明拿到的是别的版本：换镜像，或同步修改 `pack.toml` 里的 `[checks]`。

## 2. 软件合成器载荷 `weston.tar`

厂商 Weston 依赖 Mali/RGA，QEMU 里跑不起来；本包用 Debian arm64 的 Weston 10 + Mesa libgbm + pixman 自建。生成方式（全自动）：

```bash
# 需要网络（能访问 deb.debian.org）与 host 上的 python
python tools/debfetch.py            # 下载并解出 Debian arm64 包到 work/weston-root
python tools/depclosure.py          # 计算依赖闭包（跳过 lib32/armhf），缺啥补啥
python tools/pack_weston2.py        # 组装最小集到 packs/x6pro/weston/
python tools/pack_weston3.py        # 补 weston/libexec_weston.so（漏了合成器会静默不启动）
tar -cf packs/x6pro/weston.tar -C packs/x6pro/weston .
```

把结果放成 `packs/x6pro/weston.tar`（包钩子会投送到 guest，`S50vm-ui` 负责解包启动）。

> **也可以直接取用 release 附件**：`x6pro-pack-v4.3.5.zip` 已内置 `packs/x6pro/weston.tar` 与其 `licenses/`（32 个依赖包的协议清单 + 各包 copyright 原件），无需自行构建；自建时用 `tools/license_final.py` 重新生成同一份清单。
许可：**Weston 本体（含 10 及所有版本）为 MIT 许可证**；随包依赖库按各自许可证（多为 MIT/BSD/LGPL）分发，随包保留各自的许可证文本。

## 3. 桌面资源 `desktop.tar`

首页 mini-app 的页面 bundle 与图片（内容寻址的 `images/<hash>.png`）。本仓库不含它。

```bash
# 从你自己的设备导出：
#   /userdisk/miniapp/data/mini_app/pkg/<id>/a/   （<id> 取应用日志里的 topAppId）
# 打成未压缩 tar（guest 的 busybox tar 不支持 -z）：
tar -cf desktop.tar -C <导出的目录> .
```

放成 `packs/x6pro/desktop.tar`；`S50vm-ui` 会把它解到 `pkg/<id>/a/`（当前脚本覆盖 3 个已知 id）。

## 4. OCR/NPU 桩库 `libyocr.so` / `libYoudaoStitch.so`（本地生成，勿分发）

应用启动会加载 `*.rknn.encrypt` 模型走 NPU，QEMU 无 NPU 会崩；需要对**你自己固件里的库**做本地桩化：

```bash
# 从固件 system 镜像里取出（路径固定）：
#   oem/YoudaoDictPen/output/libs/libyocr.so
#   oem/YoudaoDictPen/output/libs/libYoudaoStitch.so
KEEP_CTORS=1 python tools/a64stub.py \
    libyocr.so  packs/x6pro/patches/libyocr.so \
    libYoudaoStitch.so  packs/x6pro/patches/libYoudaoStitch.so
python tools/check_ctor.py packs/x6pro/patches/libyocr.so   # 确认 DT_INIT 非 0
```

⚠️ **必须保留构造器**（`KEEP_CTORS=1`）：中和 `DT_INIT`/`DT_INIT_ARRAY` 会让应用启动即 SIGILL（该固件其它库依赖 `libyocr` 构造器）。
桩化产物是**厂商二进制的衍生品**，仅限本地使用，**不要提交、不要分发**。

## 5. 可选：`userdata-seed.tar`（跳过全新盘的首启初始化）

全新状态盘首启时应用会走一遍初始化（读设备身份、请求云端 store、校验 mini-app 包）。把一台**已完成首启初始化**的机器（真机最佳）的 guest 状态打包，即可让新盘直接进桌面：

```bash
# 在已初始化好的 guest 里：
tar -cf /userdata/userdata-seed.tar -C / userdata userdisk/miniapp
# 取出后放到 packs/x6pro/userdata-seed.tar，并在 pack.toml 的 [adapt.replace] 里声明：
#   "userdata-seed.tar" = "/tmp/userdata-seed.tar"
```

包钩子 `prepare.sh` 会在 initramfs 阶段把它解到目标根，从而跳过首启初始化。

## 免责声明

以上步骤面向个人学习与研究场景。资产版权归**网易有道**及各自权利人；本项目与网易有道、Rockchip 无隶属关系。请遵守当地法律与设备授权，自行承担一切后果。
