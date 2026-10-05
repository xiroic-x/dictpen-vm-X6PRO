# runtime 安装（rockchip-linux-ext4）

适用于：**原始 ext4 根分区 + U-Boot FIT boot** 的固件（如 RK3562 Melon 词典笔）。

```bash
cp rockchip_ext4.py <框架>/scripts/runtimes/
```

在 `<框架>/scripts/runtimes/__init__.py` 末尾注册：

```python
from . import rockchip_ext4
REGISTRY["rockchip-linux-ext4"] = rockchip_ext4.RockchipExt4Runtime
```

`rockchip_ext4` 做三件事：

1. `validate()`：确认 rootfs 是原始 ext4（offset 1080 处 superblock magic `0x53ef`）、分辨率与内核/initrd 就位；
2. `platform_args()`：给内核命令追加 `DICTPEN_ROOTFSTYPE=ext4`（框架 initramfs 按其选择挂载类型）；
3. `initramfs_extra()`：老版 initramfs 若把根挂载写死成 erofs，则就地替换为 ext4 只读挂载；契约变了会明确报错而不是静默失败。

依赖：框架自带的 `packlib` / `dpctl`，无第三方 Python 包。
