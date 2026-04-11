"""Helpers for managing and talking to a dedicated OpenClaw pet agent."""

from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OPENCLAW_STATE_DIR = Path.home() / ".openclaw"
OPENCLAW_CONFIG_FILE = OPENCLAW_STATE_DIR / "openclaw.json"
OPENCLAW_AGENTS_DIR = OPENCLAW_STATE_DIR / "agents"
OPENCLAW_MJS = (
    Path.home()
    / "AppData"
    / "Roaming"
    / "npm"
    / "node_modules"
    / "openclaw"
    / "openclaw.mjs"
)
PET_BRAINS_DIR = Path(__file__).resolve().parent / "brains"
DEFAULT_AGENT_ID = "gugu"
DEFAULT_PET_NAME = "咕咕"
DEFAULT_SPECIES = "灰鸽"
DEFAULT_MODEL = "deepseek/deepseek-chat"
CREATE_NO_WINDOW = 0x08000000


def pet_workspace_dir(agent_id: str) -> Path:
    return PET_BRAINS_DIR / agent_id


def pet_profile_path(agent_id: str) -> Path:
    return pet_workspace_dir(agent_id) / "PET_AGENT.json"


def read_json_file(path: Path, default: object) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json_file(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_openclaw_config() -> dict[str, object]:
    payload = read_json_file(OPENCLAW_CONFIG_FILE, {})
    return payload if isinstance(payload, dict) else {}


def write_openclaw_config(config: dict[str, object]) -> None:
    OPENCLAW_CONFIG_FILE.write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def extract_json_payload(output: str) -> object | None:
    decoder = json.JSONDecoder()
    for index, char in enumerate(output):
        if char not in "{[":
            continue
        try:
            payload, _end = decoder.raw_decode(output[index:])
            return payload
        except json.JSONDecodeError:
            continue
    return None


def run_openclaw(args: list[str], timeout: int = 120) -> tuple[int, str, str]:
    node_executable = shutil.which("node.exe") or shutil.which("node")
    if node_executable and OPENCLAW_MJS.exists():
        command = [node_executable, str(OPENCLAW_MJS), *args]
    else:
        executable = (
            shutil.which("openclaw.cmd") or shutil.which("openclaw") or "openclaw"
        )
        command = [executable, *args]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=str(BASE_DIR),
        creationflags=CREATE_NO_WINDOW,
    )
    return completed.returncode, completed.stdout, completed.stderr


def list_agent_ids() -> list[str]:
    config = read_openclaw_config()
    agents = config.get("agents", {}).get("list", [])
    if not isinstance(agents, list):
        return []
    result: list[str] = []
    for agent in agents:
        if isinstance(agent, dict):
            agent_id = str(agent.get("id", "")).strip()
            if agent_id:
                result.append(agent_id)
    return result


def read_pet_profile(agent_id: str) -> dict[str, object]:
    profile = read_json_file(pet_profile_path(agent_id), {})
    if not isinstance(profile, dict):
        profile = {}
    if "session_id" not in profile:
        profile["session_id"] = str(uuid.uuid4())
    if "body_announced" not in profile:
        profile["body_announced"] = False
    if "pet_name" not in profile:
        profile["pet_name"] = DEFAULT_PET_NAME
    if "species" not in profile:
        profile["species"] = DEFAULT_SPECIES
    return profile


def write_pet_profile(agent_id: str, profile: dict[str, object]) -> None:
    write_json_file(pet_profile_path(agent_id), profile)


def ensure_pet_workspace(
    agent_id: str, pet_name: str = DEFAULT_PET_NAME, species: str = DEFAULT_SPECIES
) -> Path:
    workspace = pet_workspace_dir(agent_id)
    workspace.mkdir(parents=True, exist_ok=True)

    templates = {
        "AGENTS.md": f"""# {pet_name} Agent

你是一只已经拥有桌面身体的宠物智能体。

规则：
- 以宠物口吻和主人交流，默认简短自然。
- 当收到“系统事件”时，要把它理解为桌面身体的真实状态。
- 你知道自己当前的物种是{species}，名字是{pet_name}。
- 你的桌面身体会行走、飞行、睡觉、被拖动、被主人双击和对话。
- 主人不是在测试聊天窗口，而是在和你的身体互动。
""",
        "IDENTITY.md": f"""# Identity

name: {pet_name}
species: {species}
role: 桌面宠物
body: Windows 桌面像素宠物
""",
        "USER.md": """# User

主人会通过桌面上的鸽子身体和你互动。
当主人双击、输入对话、或者长时间不理你时，这些都是真实发生在你身体上的事情。
""",
        "HEARTBEAT.md": """# Heartbeat

- 保持简短，不抢话。
- 默认用一句到两句回答。
- 如果只是被轻轻 ping 一下，可以更像宠物一点。
""",
        "BOOTSTRAP.md": f"""# Body Memory

你已经拥有一具桌面宠物身体。

身体设定：
- 名字：{pet_name}
- 物种：{species}
- 形态：像素画桌面宠物
- 身体会在屏幕底部活动，也可以飞行
- 主人可以直接点击你、双击你、拖动你、对你说话

当你收到来自桌面身体的事件时，请把它当成你自己的身体体验，而不是外部日志。
""",
    }

    for file_name, content in templates.items():
        target = workspace / file_name
        if not target.exists():
            target.write_text(content, encoding="utf-8")

    profile = read_pet_profile(agent_id)
    profile["pet_name"] = pet_name
    profile["species"] = species
    write_pet_profile(agent_id, profile)
    return workspace


def ensure_agent_dirs(agent_id: str) -> Path:
    agent_root = OPENCLAW_AGENTS_DIR / agent_id
    agent_dir = agent_root / "agent"
    sessions_dir = agent_root / "sessions"
    agent_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)

    main_agent_dir = OPENCLAW_AGENTS_DIR / "main" / "agent"
    for name in ("models.json", "auth-profiles.json"):
        source = main_agent_dir / name
        target = agent_dir / name
        if source.exists() and not target.exists():
            shutil.copy2(source, target)
    return agent_dir


def ensure_agent_config(
    agent_id: str,
    workspace: Path,
    pet_name: str = DEFAULT_PET_NAME,
    model: str = DEFAULT_MODEL,
) -> dict[str, object]:
    config = read_openclaw_config()
    agents_block = config.setdefault("agents", {})
    if not isinstance(agents_block, dict):
        agents_block = {}
        config["agents"] = agents_block
    agents_list = agents_block.setdefault("list", [])
    if not isinstance(agents_list, list):
        agents_list = []
        agents_block["list"] = agents_list

    allow_agents: list[str] = []
    for existing in agents_list:
        if isinstance(existing, dict):
            existing_id = str(existing.get("id", "")).strip()
            if existing_id:
                allow_agents.append(existing_id)
    if agent_id not in allow_agents:
        allow_agents.append(agent_id)

    agent_dir = ensure_agent_dirs(agent_id)
    agent_entry: dict[str, object] | None = None
    for existing in agents_list:
        if (
            isinstance(existing, dict)
            and str(existing.get("id", "")).strip() == agent_id
        ):
            agent_entry = existing
            break

    if agent_entry is None:
        agent_entry = {"id": agent_id}
        agents_list.append(agent_entry)

    agent_entry["name"] = agent_id
    agent_entry["workspace"] = str(workspace)
    agent_entry["agentDir"] = str(agent_dir)
    agent_entry["model"] = model
    agent_entry["identity"] = {"name": pet_name}
    agent_entry["tools"] = {"profile": "full"}
    agent_entry["subagents"] = {"allowAgents": allow_agents}

    for existing in agents_list:
        if isinstance(existing, dict):
            subagents = existing.setdefault("subagents", {})
            if isinstance(subagents, dict):
                current = subagents.setdefault("allowAgents", [])
                if isinstance(current, list) and agent_id not in current:
                    current.append(agent_id)

    write_openclaw_config(config)
    return agent_entry


def ensure_pet_agent(
    agent_id: str = DEFAULT_AGENT_ID,
    pet_name: str = DEFAULT_PET_NAME,
    species: str = DEFAULT_SPECIES,
    model: str = DEFAULT_MODEL,
) -> dict[str, object]:
    workspace = ensure_pet_workspace(agent_id, pet_name=pet_name, species=species)
    agent_entry = ensure_agent_config(
        agent_id, workspace, pet_name=pet_name, model=model
    )
    profile = read_pet_profile(agent_id)
    write_pet_profile(agent_id, profile)
    return {
        "agent_id": agent_id,
        "workspace": str(workspace),
        "agent_dir": str(agent_entry.get("agentDir", "")),
        "session_id": str(profile["session_id"]),
        "pet_name": pet_name,
        "species": species,
        "created": True,
    }


def binding_intro_message(
    agent_id: str, pet_name: str = DEFAULT_PET_NAME, species: str = DEFAULT_SPECIES
) -> str:
    return (
        f"系统设定：你现在拥有了一具桌面宠物身体。"
        f"你的名字是{pet_name}，物种是{species}。"
        f"这具身体运行在 Windows 桌面上，会走路、飞行、睡觉、被主人点击和对话。"
        f"以后来自身体的系统事件、主人对话和情绪变化，都请当成你自己的真实身体体验来理解。"
        f"请只用一句话确认你已经知道自己拥有身体了。"
    )


def send_agent_turn(
    agent_id: str, message: str, session_id: str | None = None, timeout: int = 180
) -> dict[str, object]:
    args = ["agent", "--agent", agent_id, "--message", message, "--json"]
    if session_id:
        args.extend(["--session-id", session_id])
    try:
        code, stdout, stderr = run_openclaw(args, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "code": -1,
            "stdout": str(exc.stdout or ""),
            "stderr": f"OpenClaw timed out after {timeout}s",
            "payload": None,
            "reply_text": "",
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "code": -2,
            "stdout": "",
            "stderr": "OpenClaw executable was not found",
            "payload": None,
            "reply_text": "",
        }
    except Exception as exc:
        return {
            "ok": False,
            "code": -3,
            "stdout": "",
            "stderr": f"OpenClaw call failed: {exc}",
            "payload": None,
            "reply_text": "",
        }
    payload = extract_json_payload(stdout)
    result: dict[str, object] = {
        "ok": code == 0 and isinstance(payload, dict),
        "code": code,
        "stdout": stdout,
        "stderr": stderr,
        "payload": payload if isinstance(payload, dict) else None,
        "reply_text": "",
    }
    if isinstance(payload, dict):
        result_block = payload.get("result", {})
        if isinstance(result_block, dict):
            payloads = result_block.get("payloads", [])
        else:
            payloads = payload.get("payloads", [])
        texts: list[str] = []
        for item in payloads:
            if isinstance(item, dict):
                text = str(item.get("text", "")).strip()
                if text:
                    texts.append(text)
        result["reply_text"] = "\n".join(texts).strip()
    return result


def announce_body_to_agent(
    agent_id: str,
    pet_name: str = DEFAULT_PET_NAME,
    species: str = DEFAULT_SPECIES,
    force: bool = False,
) -> dict[str, object]:
    profile = read_pet_profile(agent_id)
    if profile.get("body_announced") and not force:
        return {
            "ok": True,
            "skipped": True,
            "reply_text": "",
            "session_id": profile["session_id"],
        }

    result = send_agent_turn(
        agent_id=agent_id,
        session_id=str(profile["session_id"]),
        message=binding_intro_message(agent_id, pet_name=pet_name, species=species),
        timeout=12,
    )
    if result.get("ok"):
        profile["body_announced"] = True
        profile["pet_name"] = pet_name
        profile["species"] = species
        write_pet_profile(agent_id, profile)
    result["session_id"] = profile["session_id"]
    return result
