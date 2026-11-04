# UniXNU-nabu-sweet

把 **Xiaomi Pad 5（nabu，SM8150）** 跑上 **iOS 16.7.16**，走到 SpringBoard 桌面。

本仓库基于已跑通的 `JohnLeeeeeee678/UniXNU-raphael`（红米 K20 Pro，**同一颗 SM8150**）
改造而来，只替换设备树和 ADT 面板参数。

---

## 为什么这套能行

| | 你之前用的方案 | 本仓库 |
|---|---|---|
| 引导 | 自写 shim + DarwinBoot | **Project Aloha UEFI**（Aloha 官方有 `xiaomi-nabu` 目录） |
| 内核 | 定制 NABU 配置（图形是空壳） | **SWEET 内核**（已进过桌面） |
| 串口 | 无 | `sweetusb=2` **USB CDC-ACM 实时日志** |
| 结果 | 卡在 AGX 后静默 | 一加 7 Pro / 红米 K20 Pro 均已进桌面 |

---

## 一、把代码传到 GitHub

1. 在 GitHub 新建空仓库，名字随意，比如 `unixnu-nabu-sweet`，**不要**勾选 README。
2. 把本目录所有文件传上去（网页拖拽或 `git push` 都行）：

```bash
cd unixnu-nabu-sweet
git init
git add -A
git commit -m "nabu SM8150 SWEET port"
git branch -M main
git remote add origin https://github.com/<你的用户名>/unixnu-nabu-sweet.git
git push -u origin main
```

---

## 二、跑 GitHub Actions

1. 进仓库页面 → **Actions** 标签
2. 左侧选 **build-nabu**
3. 右侧 **Run workflow** → 绿色按钮
4. 等约 **40–60 分钟**（内核在 macOS runner 上编译约 30 分钟，固件在 Ubuntu 上约 15 分钟）

### 跑完会产出两个 artifact

| 名字 | 内容 |
|---|---|
| `nabu-kernel` | 编译好的 `kernel.macho`（SWEET 内核） |
| `boot-nabu.img` | **最终 boot 镜像**，直接刷这个 |

如果失败，仓库里还有 `build-logs` 可以看。

---

## 三、下载镜像

Actions 的 artifact 需要登录才能下。两个办法：

**办法 1（登录下载）**：打完包点开 run → 页面底部 Artifacts → 点 `boot-nabu.img`。

**办法 2（匿名下载，用 nightly.link）**：

```text
https://nightly.link/<你的用户名>/unixnu-nabu-sweet/workflows/build-nabu/main/boot-nabu.img.zip
```

---

## 四、刷 iOS 根镜像

内核要求 `userdata` 分区开头有一个 **HFS+ 卷**。用 raphael 已发布的成品（iOS 16.7.16）：

```bash
# 下载 4 个分片（约 5.7 GB）
gh release download iosroot-dense-16.7.16-20261101-093843 \
    -R JohnLeeeeeee678/UniXNU-raphael -p 'p0*.simg' -D parts/

# 按降序刷入（每片自带绝对起始块的 DONT_CARE，降序才不会互相覆盖）
for p in $(ls parts/p*.simg | sort -r); do
  fastboot flash userdata "$p"
done
```

> ⚠️ **这一步会清空 userdata 分区，Android 数据全部丢失。**

如果 fastboot 报 `Bad Buffer Size` 或 `not a multiple of the block size`，
说明你的 ABL 不接受这么大的单块传输。解决办法见下面的「分片重切」一节。

---

## 五、启动

```bash
fastboot boot boot-nabu.img
```

屏幕上看这些标志：

```text
=== SWEET t=60s exec=42 crash=3 sb=1/1 fb=9 sw=16 dn=0 m=1 gui=1 ===
```

| 字段 | 含义 |
|---|---|
| `sw=` | 成功提交到面板的帧数。非 0 说明 GUI 拿到了屏幕 |
| `gui=1` | 面板已让位给 GUI |
| `sb=x/y` | SpringBoard 启动次数 / 崩溃次数 |
| `crash=` | 崩溃进程列表 |

---

## 六、读实时日志（重要）

内核会把日志通过 **USB CDC-ACM 串口** 输出，Windows 自带驱动即可识别：

```text
USB\Class_02&SubClass_02&Prot_01
VID 0x1209 / PID 0x0001
```

```python
pip install pyserial
python scripts/console_log.py - ios-console.log
```

脚本会自动找 COM 口、自动重连，把内核打印全部写进文件。
**以后排查不用再拍照。**

---

## 七、分片重切（如果刷不进去）

raphael 的分片是按红米 K20 Pro 的 userdata 几何切的。nabu 的分区大小不同
（`0x1AB57BB000` ≈ 114 GB），如果 ABL 拒绝，需要重新切：

```bash
# 1. 拼接成完整镜像
cat parts/p00.simg > full.simg   # 占位，实际用 assemble_hfsroot.py

# 2. 重新切成小块
python3 scripts/split_for_abl.py full.simg -o newparts/ --limit-gib 1.0

# 3. 验证
python3 scripts/verify_pieces.py full.simg newparts/

# 4. 降序刷
for p in $(ls newparts/p*.simg | sort -r); do fastboot flash userdata "$p"; done
```

---

## 八、已知限制

- **没有 SEP / 安全隔区**，无法登录 Apple ID、无法用蜂窝网络
- **蓝牙 / 指纹 / 摄像头** 预计不可用
- **触摸** 在 raphael 上还没接好，nabu 大概率同样需要额外工作
- `fastboot boot` 是临时启动，重启就回 Android

---

## 九、目录说明

```text
board.toml                     nabu 设备定义（面板 1600x2560、TARGET_DEVICE=xiaomi-nabu）
inputs/uefi-prebuilt/nabu.dtb  真机抓的 nabu 设备树（715 KB）
patches/
  01xx-sweet-*.patch           SWEET 内核的串口/面板/诊断补丁（11 个）
  unixnu-guacamole.patch       UniXNU 驱动补丁（SM8150 通用）
  aloha-guacamole.patch        Aloha UEFI 补丁（SM8150 通用）
  darwinboot-guacamole.patch   DarwinBoot 补丁
scripts/
  devices.py                   hardware profile（已加 nabu）
  mkadt.py                     ADT 生成器
  make-nabu-adt.py             nabu 的 ADT 步骤
  build-firmware.py            编译 UEFI 固件
  build-payload.py             打 FAT payload
  build-bootimg.py             打 Android boot 镜像
  console_log.py               读 USB 串口日志
  split_for_abl.py             重切分片
.github/workflows/build-nabu.yml   一键构建
```

---

## 十、来源

- [UniXNU](https://github.com/UniXNU/UniXNU) — UEFI/XNU 引导框架
- [Project Aloha](https://github.com/Project-Aloha/mu_aloha_platforms) — SM8150 UEFI（含 `xiaomi-nabu`）
- [dipa-studio/ios-sweet](https://github.com/dipa-studio/ios-sweet) — SWEET 内核构建
- [JohnLeeeeeee678/UniXNU-raphael](https://github.com/JohnLeeeeeee678/UniXNU-raphael) — 已进桌面的同 SoC 方案
- [wochgn/UniXNU-guacamole](https://github.com/wochgn/UniXNU-guacamole) — SM8150 原始突破