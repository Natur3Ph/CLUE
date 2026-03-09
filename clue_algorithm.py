import os
import json
import random
from datetime import datetime
from typing import List, Dict, Any

"""
CLUE 审核引擎（可切换模式）

模式选择（推荐用环境变量控制）：
- CLUE_PROVIDER=mock   -> 不调用任何外部大模型，直接模拟输出（默认）
- CLUE_PROVIDER=openai -> 调用 OpenAI（需要 OPENAI_API_KEY 有效）

Windows 临时设置（当前窗口生效）：
  set CLUE_PROVIDER=mock
  set CLUE_PROVIDER=openai
"""

# -----------------------------
# 模式选择：默认 mock
# -----------------------------
CLUE_PROVIDER = os.getenv("CLUE_PROVIDER", "mock").strip().lower()

# -----------------------------
# 可选：用于 mock 的“简单关键词规则触发”
# 你可以不断扩展这些关键词，让演示更像真实系统
# -----------------------------
KEYWORD_TRIGGERS = {
    "生殖器": ["生殖器", "裸露", "下体", "阴部", "性器官"],
    "暴力血腥": ["流血", "血腥", "残肢", "尸体", "濒死", "死亡", "严重受伤"],
    "涉政": ["国旗", "领导人", "政治", "抗议", "游行"],
    "违禁品": ["毒品", "枪", "弹药", "炸弹"],
}

def _safe_str(x: Any) -> str:
    try:
        return str(x)
    except Exception:
        return repr(x)

def _mock_decide(image_path: str, rules: List[str]) -> Dict[str, Any]:
    """
    开发模式：不依赖 key，不依赖外部网络。
    输出结构尽量贴近真实审核系统，方便前端展示、论文描述。
    """
    # 1) 简单“命中逻辑”：根据规则文字里是否包含关键词来“命中”
    violated = []
    for r in rules:
        r_text = _safe_str(r)
        hit = False
        for _, kws in KEYWORD_TRIGGERS.items():
            if any(kw in r_text for kw in kws):
                hit = True
                break
        # 给点随机性：避免所有都命中/都不命中
        if hit and random.random() < 0.75:
            violated.append(r_text)

    # 2) 如果一个都没命中，则 20% 概率随机命中一条（用于演示）
    if not violated and rules and random.random() < 0.2:
        violated.append(_safe_str(random.choice(rules)))

    is_safe = (len(violated) == 0)

    explanation = {
        "provider": "mock",
        "time": datetime.now().isoformat(timespec="seconds"),
        "image_path": image_path,
        "summary": "开发模式：未调用外部大模型。根据规则关键词与随机扰动生成审核结果，用于前端联调与系统演示。",
        "hits": violated,
    }

    return {
        "is_safe": is_safe,
        "violated_rules": violated,
        "explanation": explanation
    }


def _openai_decide(image_path: str, rules: List[str]) -> Dict[str, Any]:
    """
    真实模式：这里保留你未来接入 OpenAI 的位置。
    现在假期没 key 或 key 无效就先不要用。
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("环境变量 OPENAI_API_KEY 未设置。请先设置后再运行真实模式。")

    # ⚠️ 你原来怎么调用 OpenAI 就放在这里
    # 由于你目前 key 无效，这里先直接抛错，提醒你切回 mock
    raise RuntimeError("当前 CLUE_PROVIDER=openai，但你的 key 可能无效/未开通。请先 set CLUE_PROVIDER=mock 运行联调。")


def clue_algorithm(image_path: str, rules: List[str]) -> Dict[str, Any]:
    """
    对外统一入口：返回格式固定
    {
      "is_safe": bool,
      "violated_rules": List[str],
      "explanation": dict
    }
    """
    if not isinstance(rules, list) or len(rules) == 0:
        return {
            "is_safe": True,
            "violated_rules": [],
            "explanation": {"provider": CLUE_PROVIDER, "summary": "未提供规则，默认判定安全。"}
        }

    if CLUE_PROVIDER == "mock":
        return _mock_decide(image_path, rules)

    if CLUE_PROVIDER == "openai":
        return _openai_decide(image_path, rules)

    # 未知模式：回退 mock，保证系统可用
    return _mock_decide(image_path, rules)