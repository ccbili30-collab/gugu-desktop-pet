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
