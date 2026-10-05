# dictpen-vm-X6PRO · 有道词典笔 X6pro 虚拟机适配

> 有道词典笔 **X6pro**（平台标识 RK3562 Melon / Linux ext4 / 固件 4.3.5）在 [lbdl0030/dictpen-rootfs](https://github.com/lbdl0030/dictpen-rootfs) 的 dictpen-vm 框架上的适配。固件包目录沿用框架内标识 `melon-pro`，对应设备即 **X6pro**。
> 许可：本项目采用 PolyForm Noncommercial License 1.0.0（非商业许可），条款见 [LICENSE](LICENSE)。

## 包含什么

| 内容 | 说明 |
|------|------|
| `packs/melon-pro/` | **设备 X6pro** 的固件包本体：`pack.toml` + `patches/`（initramfs 钩子、UI 启动脚本、触摸桥、配置覆盖） |
| `runtime/rockchip_ext4.py` | 框架 runtime 插件，让「原始 ext4 根 + U-Boot FIT boot」这类固件能挂起来 |
| `tools/` | 本轮用到的可复现工具：依赖闭包计算、Debian 取包、aarch64 导出函数桩化、桌面资源匹配、串口解卡 |
| `DEVLOG.md` | 开发日志：平台取证、黑屏根因、桩化约束、渲染实测、踩坑清单 |
| `ASSETS.md` | **不含版权内容**的资产获取步骤（固件镜像 / 合成器载荷 / 桌面资源 / 桩库），含警示与免责 |

## 为什么仓库里没有镜像和大文件

固件镜像、桌面资源、OCR 桩库的版权属于**网易有道**，本仓库不转载。固件镜像来自上游 release [X6pro](https://github.com/lbdl0030/dictpen-rootfs/releases/tag/X6pro)（镜像包由 @xiroic-x 提供），其余按需在本地生成，步骤见 [ASSETS.md](ASSETS.md)。

## 快速开始

```bash
# 1) 取框架（原作者：lbdl0030）与固件镜像 —— 见 ASSETS.md
# 2) 装 runtime：把 runtime/rockchip_ext4.py 放进框架 scripts/runtimes/，并在其 __init__.py 注册
cp runtime/rockchip_ext4.py  <框架>/scripts/runtimes/
#    然后在该目录 __init__.py 里加两行：
#      from . import rockchip_ext4
#      REGISTRY["rockchip-linux-ext4"] = rockchip_ext4.RockchipExt4Runtime
# 3) 放包
cp -r packs/melon-pro  <框架>/packs/
#    并把固件镜像放到 packs/melon-pro/images/{boot_a.img,system_a.img}
#    需要 UI 时再放 packs/melon-pro/{weston.tar,desktop.tar}（可选，见 ASSETS.md）
# 4) 起
python scripts/dpctl.py packs melon-pro
python scripts/dpctl.py up --pack melon-pro --headless
python scripts/dpctl.py screenshot --out shot.png
python scripts/dpctl.py tap 480 240          # 触摸（经包内触摸桥）
python scripts/dpctl.py down
```

## 当前状态（本仓库最后更新时）

| 环节 | 状态 | 证据 |
|------|------|------|
| 引导：ext4 根 + 持久化 overlay + switch_root | 通过 | 串口日志 `### ext4 root mounted ###`、`### overlay: persistent upper ###`、`### switch_root -> /mnt ###` |
| 显示：软件合成器（Debian Weston 10 + Mesa libgbm + pixman） | 通过 | `Output 'Virtual-1' enabled with head(s) Virtual-1` |
| 固件真实 UI 上屏 | 通过 | 激活页与完整桌面均可渲染（详见 DEVLOG 截图与尺寸） |
| 渲染耗时（应用启动 → 首帧全渲染） | 实测 | 77 s / 64 s（两轮，QEMU TCG 纯软件模拟） |
| 触控 | 通过 | `tap 300 150` → 桥日志 `down 300,83`；`tap 600 350` → `down 599,193`（UI 像素坐标） |
| 全新状态盘首启初始化 | 未闭环 | 应用停在自带「正在初始化配置」splash；缺 `vendor_storage` 设备身份 + 云端首启流程未完成。**闭合手段**：`ASSETS.md` 里的 `userdata-seed.tar` 机制 |

## 使用前必读：QEMU 模拟的硬约束

这台固件的图形栈两条腿都在 Rockchip 专有硬件上：GL 走 ARM Mali（`libmali.so.1`），pixman 走 RGA（`librga.so.2`）。QEMU 既无 `/dev/mali` 也无 `/dev/rga`，所以**厂商 Weston 在虚拟机里没有可用的软件路径**，必须换软件合成器——本仓库就是这么做的。同理，OCR/NPU（`*.rknn.encrypt` + `librknnrt`）在 QEMU 上不可用，包内提供的是「桩化让应用走容错路径」的本地生成方案。

## 授权

- 本仓库自有代码与文档采用 **PolyForm Noncommercial License 1.0.0**，完整条款见 [LICENSE](LICENSE)；协议主页：<https://polyformproject.org/licenses/noncommercial/1.0.0>。
- 第三方：**Weston（含 10 及所有版本）为 MIT 许可证**；软件合成器载荷中的其余依赖库按各自许可证（多为 MIT/BSD/LGPL）分发；Rockchip / U-Boot / NetEase Youdao 组件版权归各自权利人。
- 本项目与**网易有道**、**Rockchip** 无任何隶属关系，不代表其立场。

## 免责声明

本项目面向个人学习与研究场景。刷机、改造固件可能导致设备变砖、数据丢失、保修失效；请在你自己合法持有的设备上操作，并自行承担全部后果。作者不对任何直接或间接损失负责，也不提供任何担保。
