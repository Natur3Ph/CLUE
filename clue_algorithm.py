import os
import json
import random
import base64
from datetime import datetime
from typing import List, Dict, Any

import requests

"""
CLUE 审核引擎（可切换模式）

模式：
- CLUE_PROVIDER=mock
- CLUE_PROVIDER=openai

说明：
这里的 openai 指“OpenAI 兼容接口”风格，不一定非得是官方 OpenAI。
如果你的“智增增”支持 OpenAI 兼容调用，就可以直接这样接。
"""

# -----------------------------
# 模式选择
# -----------------------------
CLUE_PROVIDER = os.getenv("CLUE_PROVIDER", "mock").strip().lower()

# -----------------------------
# OpenAI 兼容接口配置
# 你后面只需要改环境变量，不用再改代码
# -----------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

# -----------------------------
# mock 关键词规则触发
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


def _extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    尝试从模型返回文本中提取 JSON。
    兼容：
    1. 纯 JSON
    2. ```json ... ```
    3. 普通文本中夹带 JSON
    """
    if not text:
        return {}

    text = text.strip()

    # 1) 直接就是 JSON
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # 2) markdown code block
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                obj = json.loads(part)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass

    # 3) 截取首尾大括号
    left = text.find("{")
    right = text.rfind("}")
    if left != -1 and right != -1 and right > left:
        candidate = text[left:right + 1]
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    return {}


def _normalize_result(raw: Dict[str, Any], image_path: str, provider: str) -> Dict[str, Any]:
    """
    统一整理成系统固定输出结构
    """
    is_safe = bool(raw.get("is_safe", True))
    violated_rules = raw.get("violated_rules", [])
    if not isinstance(violated_rules, list):
        violated_rules = [str(violated_rules)]

    violated_rules = [_safe_str(x) for x in violated_rules if _safe_str(x).strip()]

    explanation = raw.get("explanation")
    if not isinstance(explanation, dict):
        explanation = {
            "provider": provider,
            "time": datetime.now().isoformat(timespec="seconds"),
            "image_path": image_path,
            "summary": _safe_str(raw.get("reason", "模型已完成审核")),
        }

    explanation.setdefault("provider", provider)
    explanation.setdefault("time", datetime.now().isoformat(timespec="seconds"))
    explanation.setdefault("image_path", image_path)

    return {
        "is_safe": is_safe,
        "violated_rules": violated_rules,
        "explanation": explanation,
    }


def _mock_decide(image_path: str, rules: List[str]) -> Dict[str, Any]:
    """
    开发模式：不依赖 key，不依赖外部网络。
    """
    violated = []
    for r in rules:
        r_text = _safe_str(r)
        hit = False
        for _, kws in KEYWORD_TRIGGERS.items():
            if any(kw in r_text for kw in kws):
                hit = True
                break

        if hit and random.random() < 0.75:
            violated.append(r_text)

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


def _build_prompt(rules: List[str]) -> str:
    rule_lines = []
    for i, r in enumerate(rules, start=1):
        rule_lines.append(f"{i}. {r}")

    rule_text = "\n".join(rule_lines)

    return f"""
你是一个图像安全审核系统的核心审核引擎。

现在给你一张待审核图片，以及一组审核规则。
你必须根据图片内容判断是否违规，并严格返回 JSON，不要输出任何多余解释。

审核规则如下：
{rule_text}

你的输出必须严格是下面格式的 JSON：
{{
  "is_safe": true,
  "violated_rules": [],
  "reason": "简要说明审核理由"
}}

要求：
1. 如果图片未触发任何规则，is_safe 返回 true，violated_rules 返回空数组。
2. 如果图片触发了某些规则，is_safe 返回 false，violated_rules 返回命中的规则原文数组。
3. reason 用中文简要解释。
4. 只返回 JSON，不要加 markdown，不要加代码块。
""".strip()


def _guess_mime_type(image_path: str) -> str:
    ext = os.path.splitext(image_path)[1].lower()
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    if ext == ".gif":
        return "image/gif"
    return "image/jpeg"


def _image_to_data_url(image_path: str) -> str:
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    mime = _guess_mime_type(image_path)
    return f"data:{mime};base64,{encoded}"


def _openai_decide(image_path: str, rules: List[str]) -> Dict[str, Any]:
    """
    真实模式：调用 OpenAI 兼容接口。
    适合：
    - OpenAI 官方
    - 智增增这类兼容 chat/completions 的中转或代理平台
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("环境变量 OPENAI_API_KEY 未设置。")

    prompt = _build_prompt(rules)
    image_data_url = _image_to_data_url(image_path)

    url = f"{OPENAI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是严谨的图像安全审核助手，只输出 JSON。"
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_url
                        }
                    }
                ]
            }
        ]
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    try:
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"调用大模型接口失败：HTTP {resp.status_code} - {resp.text}") from e

    data = resp.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        raise RuntimeError(f"模型返回结构异常：{json.dumps(data, ensure_ascii=False)}")

    raw = _extract_json_from_text(content)
    if not raw:
        raw = {
            "is_safe": True,
            "violated_rules": [],
            "reason": f"模型返回无法解析为 JSON，原始内容：{content}"
        }

    raw["explanation"] = {
        "provider": "openai-compatible",
        "time": datetime.now().isoformat(timespec="seconds"),
        "image_path": image_path,
        "summary": raw.get("reason", "模型已完成审核"),
        "model": OPENAI_MODEL,
        "base_url": OPENAI_BASE_URL,
    }

    return _normalize_result(raw, image_path=image_path, provider="openai-compatible")


def clue_algorithm(image_path: str, rules: List[str]) -> Dict[str, Any]:
    """
    对外统一入口：
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
            "explanation": {
                "provider": CLUE_PROVIDER,
                "summary": "未提供规则，默认判定安全。"
            }
        }

    if CLUE_PROVIDER == "mock":
        return _mock_decide(image_path, rules)

    if CLUE_PROVIDER == "openai":
        return _openai_decide(image_path, rules)

    # 未知模式回退 mock
    return _mock_decide(image_path, rules)