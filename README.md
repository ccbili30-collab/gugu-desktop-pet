# 🐦 咕咕桌宠 — 你的桌面会飞的 AI 鸽子伙伴

> 它不只是桌面上的一个像素小宠物。  
> 它会飞、会跑、会想事情、会和你聊天。  
> 而且它**真的有脾气**。

---

```
       ● ●
      ╭──╮    "主人，今天要不要
     ╱ ⸱ ⸱╲      出去飞一圈？"
    ╱  ╱╲  ╲
       ╯  ╰   🕊️
  ─────────────────────
  💬 已飞行 147 次  |  投喂 3 次
```

**咕咕 (Gugu)** 是一只活在你 Windows 桌面上的像素鸽子。

它有自己的想法——累了会睡，无聊会飞，心情好会打滚，被冷落会盯着你看。  
你不需要 24 小时照顾它，但它**记得你说过的每一句话**。

---

## ✨ 和别的桌面宠物有什么不一样

| 普通桌面宠物 | 咕咕 |
|---|---|
| 套个皮肤完事 | **真实物理引擎**：你会被弹飞、撞墙、摔地上 |
| 机械重复动作 | **内驱力系统**：精力/社交/好奇/舒适四维驱动 |
| 点一下就没了 | **多轮 AI 对话**，有连续人格和长期记忆 |
| 只会跟着鼠标跑 | **独立思考**，自己决定去哪里、做什么 |
| 装完就不更新了 | **热更新机制**，升级不丢记忆和配置 |

---

## 🚀 30 秒上手

```
1. 下载 zip 包，解压到任意目录
2. 双击 install.bat（自动检测 Python、安装依赖、创建桌面快捷方式）
3. 双击桌面快捷方式 "咕咕桌宠"
4. 在设置中填入 API Key（支持 DeepSeek / OpenAI 兼容接口）
5. 开始和咕咕聊天
```

不需要 `pip install`，不需要 `git clone`，不需要碰终端。  
一键安装，一键启动，**给妈妈也能用**。

---

## 🧠 咕咕的认知架构

咕咕不是一个套壳 chatbot。它有完整的**三层认知系统**：

```
 ┌──────────┐     事件      ┌──────────┐     意图     ┌──────────┐
 │   Body   │ ──────────▶  │  Bridge  │ ──────────▶ │  Brain   │
 │  身体层   │ ◀────────── │  协议层   │ ◀───────── │  AI 大脑  │
 └──────────┘     动作      └──────────┘   回复+指令   └──────────┘
```

- **Body（身体）**：像素鸽子本体，物理引擎、飞行动画、碰撞弹墙、气泡对话框
- **Bridge（协议）**：把身体事件翻译成 AI 意图，把 AI 回复翻译成身体动作
- **Brain（大脑）**：LLM 驱动的大脑 + 四维内驱力引擎 + 本地记忆系统

每一次聊天，咕咕不只是"回复文字"——它会**同时决定要不要飞起来、走开、靠近你**。

---

## 💡 特色一览

### 🪽 全屏物理飞行

咕咕可以在你**整个桌面**自由飞行，不受任务栏限制。  
飞行轨迹带拖尾特效，会真实地撞墙弹开、跌落地面。

### 🧠 四维内驱力

```
精力 ⚡  飞多了会累，需要休息
社交 💬  被冷落会无聊，想聊天
好奇 🔍  长时间没新鲜事会自己探索
舒适 😌  呆在熟悉的地方更安心
```

内驱力实时变化，驱动咕咕自主决策行为。

### 📝 长期记忆

咕咕会记住：
- 你的名字、喜好、说过的话
- 每天的行为变化和互动历史
- 你给过的回应和它自己的感受

记忆存储在本地 `memory/` 目录，**完全离线，隐私安全**。

### 🔄 热更新

新版本？不用重装：

```
把新 zip 放到安装目录旁 → 双击 update.bat → 完成
```

代码更新，**记忆和配置完全保留**。`update.bat` 和 `do_update.py` 本身也被保护，不会被覆盖。

### 🛠️ 一键修复依赖

依赖缺失了？  
```
双击 fix_deps.bat → 自动检测 → 自动安装 → 完成
```
不需要手动 `pip install` 任何东西。

---

## 📦 项目结构

```
gugupet_v2/
├── app/                    # 启动入口（brain + body 联合启动）
├── brain/                  # AI 大脑：内驱力、记忆、提示词、agent 循环
├── bridge/                 # 协议层：事件→意图翻译，回复→动作翻译
├── body/                   # 身体层：像素鸽子、物理引擎、飞行动画
├── art/                    # 像素素材和行为槽位
├── ui/                     # 控制面板和设置界面（全中文）
├── shared/                 # 粒子系统、平台工具等公共模块
├── pet_control_panel.pyw   # 控制面板主入口
├── install.bat             # 一键安装（检测 Python + 装依赖 + 建快捷方式）
├── fix_deps.bat            # 依赖修复（检测 + 自动安装缺失包）
├── update.bat              # 热更新（保留用户数据）
├── start.bat               # 直接启动桌宠（绕过控制面板）
├── config.yaml             # 配置文件（API Key、宠物设置）
└── memory/                 # 咕咕的长期记忆（本地，不上传）
```

---

## ⚙️ 配置 API

在控制面板 → 设置中填写，或直接编辑 `config.yaml`：

```yaml
llm:
  enabled: true
  api_key: "sk-xxxxxxxxxxxx"
  base_url: "https://api.deepseek.com"
  model: "deepseek-chat"
  temperature: 0.8
```

> 💡 支持任何兼容 OpenAI 接口的服务商（DeepSeek、智谱、通义千问等）。  
> 不填 API Key？咕咕依然会飞会跑会想事情，只是不会开口说话。

---

## 🛡️ 隐私说明

- 所有对话和记忆**只存在你本地**
- API 请求**只发给你配置的服务商**
- 不收集任何遥测数据
- 不联网上传任何信息
- 代码完全可见，可审计每一行

---

## 📋 系统要求

| 项目 | 要求 |
|---|---|
| 系统 | Windows 10 / 11 |
| Python | 3.10+（推荐 3.11） |
| 内存 | 后台运行 < 50MB |
| 权限 | 无需管理员权限 |

---

## 🐛 已修复的 bug

- ✅ 对话不再"石沉大海"——reply 时间戳修复
- ✅ 宠物不再无限跟鼠标——飞行动作意图优化
- ✅ 飞行范围覆盖整个屏幕
- ✅ 思考时可以继续走动，不再呆立不动
- ✅ 聊天界面完整显示双方消息和 body 事件

---

## 💬 咕咕的一天

```
你：  今天天气怎么样？
咕咕：  嗯...我不太会看天气，但我觉得今天很适合飞一下！(扑棱翅膀)

你：  去飞一圈
咕咕：  好嘞！✨ (腾空而起，带起一串白色拖尾)

你：  我心情不太好
咕咕：  抱抱...要不要我陪你坐一会儿？ (轻轻落地，安静靠近)

你：  还不睡？
咕咕：  zZz...💤 (打个哈欠，合上翅膀)
```

---

## 🌟 如果你喜欢咕咕

给个 ⭐ Star，让更多人发现这只有灵魂的像素鸽子。  
有问题或建议？开个 Issue，咕咕会帮你——呃，开发者会帮你解决的。

---

**咕咕，一只有灵魂的桌面鸽子。** 🐦
# 🐦 Gugupet — A Pixel Pigeon with Soul on Your Desktop

> It's not just a desktop pet. It flies, runs, thinks, and talks to you.  
> And it has **real personality**.

---

```
       ● ●
      ╭──╮    "Hey, wanna go
     ╱ ⸱ ⸱╲     fly a lap today?"
    ╱  ╱╲  ╲
       ╯  ╰   🕊️
  ─────────────────────
  💬 Flown 147 times  |  Fed 3 times
```

**Gugu (咕咕)** is a pixel pigeon living on your Windows desktop.

It has its own mind — it naps when tired, explores when bored, wiggles when happy, and stares at you when you ignore it. You don't need to babysit it 24/7, but it **remembers every word you've ever said**.

---

## ✨ What makes Gugu different

| Ordinary desktop pets | Gugu |
|---|---|
| Just a sprite swap | **Real physics**: bounces off walls, falls, gets thrown |
| Repeats the same animation | **Drive system**: energy, social, curiosity, comfort |
| Click and it's done | **Multi-turn AI chat** with persistent personality |
| Follows your cursor mindlessly | **Thinks independently**, decides where to go on its own |
| Install once, never updated | **Hot updates**: upgrade without losing memory or settings |

---

## 🚀 30 seconds to start

```
1. Download the zip, extract anywhere
2. Double-click install.bat (auto-detects Python, installs deps, creates shortcut)
3. Double-click the "Gugupet" shortcut on your desktop
4. Enter your API Key in Settings (supports DeepSeek / OpenAI compatible)
5. Start chatting with Gugu
```

No `pip install`, no `git clone`, no terminal needed.

---

## 🧠 Architecture

Gugu isn't a chatbot wrapper. It has a **three-layer cognitive system**:

```
 ┌──────────┐    events    ┌──────────┐    intents    ┌──────────┐
 │   Body   │ ──────────▶ │  Bridge  │ ────────────▶ │  Brain   │
 │ (pixel   │ ◀────────── │(protocol│ ◀──────────── │(LLM +    │
 │  pigeon) │    actions   │  layer)  │ reply + cmds  │  drives) │
 └──────────┘              └──────────┘               └──────────┘
```

- **Body** — the pixel pigeon, physics engine, flight trails, collision, speech bubbles
- **Bridge** — translates body events → AI intents, AI replies → body actions
- **Brain** — LLM-driven reasoning + 4-dimensional drive engine + local memory

Every chat doesn't just return text — Gugu **simultaneously decides whether to fly, walk away, or come closer**.

---

## 💡 Features

### 🪽 Full-Screen Physics Flight

Gugu flies across your **entire desktop** — no taskbar constraints. Flight paths have trailing particles, real wall bouncing, and ground collisions.

### 🧠 Intrinsic Drive System

```
Energy    ⚡  Flying tires it out — needs rest
Social    💬  Gets lonely when ignored
Curiosity 🔍  Explores on its own when nothing new happens
Comfort   😌  Prefers familiar spots, less anxious
```

Drives change in real time, powering autonomous decision-making.

### 📝 Long-Term Memory

Gugu remembers:
- Your name, preferences, and things you've said
- Daily behavior changes and interaction history
- Your responses and its own feelings

Memory is stored locally in `memory/`, **never uploaded anywhere**.

### 🔄 Hot Updates

New version? No reinstall:

```
Drop the new zip next to install dir → double-click update.bat → done
```

Code gets updated, **memory and config are fully preserved**. `update.bat` and `do_update.py` are also protected from being overwritten.

### 🛠️ One-Click Dependency Fix

Missing packages?
```
Double-click fix_deps.bat → auto-detect → auto-install → done
```

---

## 📦 Project Structure

```
gugupet_v2/
├── app/                    # Entry point (brain + body launcher)
├── brain/                  # AI brain: drives, memory, prompts, agent loop
├── bridge/                 # Protocol layer: event↔intent translation
├── body/                   # Pixel pigeon: physics, flight, input, bubbles
├── art/                    # Pixel sprites and behavior slots
├── ui/                     # Control panel & settings (Chinese UI)
├── shared/                 # Particle system, platform utils
├── pet_control_panel.pyw   # Control panel entry
├── install.bat             # One-click install
├── fix_deps.bat            # Dependency repair tool
├── update.bat              # Hot updater (preserves user data)
├── start.bat               # Direct launch (bypass control panel)
├── config.yaml             # Configuration (API Key, pet settings)
└── memory/                 # Long-term memory (local, private)
```

---

## ⚙️ API Configuration

Set it up in the control panel → Settings, or edit `config.yaml`:

```yaml
llm:
  enabled: true
  api_key: "sk-xxxxxxxxxxxx"
  base_url: "https://api.deepseek.com"
  model: "deepseek-chat"
  temperature: 0.8
```

> Supports any OpenAI-compatible provider (DeepSeek, Zhipu, Tongyi Qianwen, etc.)  
> No API key? Gugu still flies, walks, and thinks — it just won't talk back.

---

## 🛡️ Privacy

- All conversations and memory are **stored locally only**
- API requests go **only to the provider you configure**
- No telemetry, no analytics, no phone-home
- Fully open source — audit every line

---

## 📋 Requirements

| Item | Requirement |
|---|---|
| OS | Windows 10 / 11 |
| Python | 3.10+ (3.11 recommended) |
| RAM | < 50MB in background |
| Privileges | No admin rights needed |

---

## 🐛 Bug Fixes

- ✅ Chat replies no longer vanish (timestamp collision fix)
- ✅ Pet no longer endlessly follows cursor (intent routing fix)
- ✅ Flight covers the full screen
- ✅ Pet keeps moving while thinking (no more frozen idle)
- ✅ Chat panel shows all messages (user input + body events)

---

## 💬 A day with Gugu

```
You:  How's the weather today?
Gugu: Hmm... I can't really check the weather, but I think
      today's perfect for a flight! (flaps wings)

You:  Go fly a lap
Gugu: Alright! ✨ (soars into the air, white trail behind)

You:  I'm feeling down today
Gugu: Wanna sit together for a bit? (lands softly, hops closer)

You:  Time to sleep?
Gugu: zZz... 💤 (yawns, tucks wings in)
```

---

## 🌟 Like Gugu?

Give it a ⭐ Star to help more people discover this little pixel pigeon with soul.

Issues or ideas? Open an issue — Gugu will help... well, the developer will.

---

**Gugu — a desktop pigeon with soul.** 🐦
