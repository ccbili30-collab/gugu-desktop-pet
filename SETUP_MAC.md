# 咕咕桌宠 — macOS 移植说明

> **分支**：`macos-port`  
> **Windows 版**在 `main` 分支，本分支只增加 macOS 相关文件，不覆盖任何 Windows 专用代码。

---

## 新增文件一览

| 文件 | 说明 |
|------|------|
| `body/pet_window_mac.py` | macOS 渲染核心，继承原版 `DesktopPet`，覆盖平台层 |
| `shared/platform_mac.py` | AppKit / Quartz 平台 API（鼠标坐标、工作区、宠物生成） |
| `shared/platform.py` | 跨平台包装，macOS 自动转发到 `platform_mac` |
| `app/launcher_mac.py` | macOS 专用启动入口 |
| `start_mac.command` | 可双击运行的 shell 启动脚本 |
| `requirements_mac.txt` | macOS 额外依赖列表 |
| `ui/widgets.py` | 字体按平台切换（PingFang SC / Menlo / SF Pro） |
| `ui/control_panel.py` | 移除 Windows 进程 flags，启动器跨平台兼容 |

---

## 环境要求

- macOS 12 Monterey 或更高版本
- Python 3.10+（推荐 3.11/3.12）
- Apple Silicon（M1/M2/M3）或 Intel 均支持

---

## 安装步骤

### 1. 克隆仓库（切换到 mac 分支）

```bash
git clone -b macos-port https://github.com/ccbili30-collab/gugu-desktop-pet.git
cd gugu-desktop-pet
```

### 2. 创建虚拟环境（推荐）

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖

```bash
# 公共依赖
pip install -r requirements.txt

# macOS 额外依赖（pygame + pyobjc）
pip install -r requirements_mac.txt
```

### 4. 配置 LLM

编辑 `config.yaml`，填入你的 API Key 和模型名称（与 Windows 版相同）。

### 5. 授予辅助功能权限

**跟随鼠标功能需要辅助功能权限**：

系统设置 → 隐私与安全性 → 辅助功能 → 添加 Terminal（或你的 Python 解释器）

首次运行时系统也会自动弹出授权请求。

### 6. 启动

```bash
# 方法一：命令行
python3 app/launcher_mac.py

# 方法二：双击（需先在 Finder 中右键 → 打开）
open start_mac.command
```

---

## 架构差异（与 Windows 版对比）

| 功能 | Windows | macOS |
|------|---------|-------|
| 透明窗口 | tkinter `-transparentcolor` | PyObjC `NSPanel` + `clearColor` |
| 置顶无边框 | tkinter `-topmost -toolwindow` | `NSFloatingWindowLevel` |
| 像素渲染 | tkinter Canvas `create_rectangle` | pygame `draw.rect` |
| 鼠标坐标 | `ctypes.windll.user32.GetCursorPos` | `Quartz.CGEventGetLocation`（Y 轴翻转） |
| 工作区边界 | `SystemParametersInfoW` | `NSScreen.visibleFrame` |
| 气泡渲染 | PIL → tkinter Canvas | PIL → pygame Surface blit |
| 主循环 | `tkinter.mainloop` | `pygame.Clock` |
| 快捷方式 | PowerShell `.lnk` | `.command` shell 脚本 |
| 字体 | Microsoft YaHei UI / Consolas | PingFang SC / Menlo / SF Pro |

**brain/、bridge/、art/、config/、service_runtime.py 完全零修改复用。**

---

## 已知限制 / TODO

- [ ] 历史对话面板（`open_history_panel`）目前为空实现，待补充
- [ ] 弹出式对话框使用 pygame overlay，样式较简陋
- [ ] 尚未测试 `py2app` 打包为 `.app`
- [ ] 若 pyobjc 未安装，透明置顶降级为普通 pygame 窗口（功能仍可用）

---

## 权限说明

跟随鼠标功能使用 `Quartz.CGEventCreate` 读取全局鼠标位置，这需要辅助功能权限。  
程序**不会**记录、上传或以任何方式持久化鼠标轨迹，仅用于实时位置计算。
