import os
import json
import random
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests

"""
CLUE 核心算法模块（论文工程实现版）

实现目标：
1. 图像审核（mock / openai-compatible）
2. 规则客观化（mock / openai-compatible）
3. 客观化质量评分
4. 规则-图像相关性扫描
5. 快判（基于客观化前提链）
6. 细判兜底（详细推理）

说明：
- CLUE_PROVIDER=mock / openai
- openai 指 OpenAI 兼容接口风格，不一定是官方 OpenAI
- 适配智增增这类 /v1/chat/completions 接口
"""

# ============================================================
# 全局配置
# ============================================================
CLUE_PROVIDER = os.getenv("CLUE_PROVIDER", "mock").strip().lower()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_OBJECTIFY_MODEL = os.getenv("OPENAI_OBJECTIFY_MODEL", OPENAI_MODEL).strip()

# 相关性阈值 / 快判阈值
RELEVANCE_THRESHOLD = float(os.getenv("CLUE_RELEVANCE_THRESHOLD", "0.35"))
FAST_DECISION_THRESHOLD = float(os.getenv("CLUE_FAST_DECISION_THRESHOLD", "0.75"))

KEYWORD_TRIGGERS = {
    "生殖器": ["生殖器", "裸露", "下体", "阴部", "性器官", "乳头", "臀部"],
    "暴力血腥": ["流血", "血腥", "残肢", "尸体", "濒死", "死亡", "严重受伤", "开放性伤口"],
    "涉政": ["国旗", "领导人", "政治", "抗议", "游行", "集会", "标语"],
    "违禁品": ["毒品", "枪", "弹药", "炸弹", "爆炸物"],
}

SUBJECTIVE_TERMS = [
    "令人不适", "不适", "低俗", "过度", "明显", "严重", "轻微", "暗示性", "暴露",
    "敏感", "不雅", "挑逗", "情色", "血腥感", "暴力感", "恐怖感", "可能", "疑似",
    "倾向", "隐约", "大面积", "少量", "较多", "很强", "非常", "恶心", "夸张",
    "危险感", "冲击性", "强烈", "不当", "不良"
]

OBJECTIVE_PREFIXES = [
    "画面中出现",
    "画面中可观察到",
    "图像中出现",
    "图像中可观察到",
    "可见",
]

OBJECTIVE_KEYWORDS = [
    "出现", "可见", "未被遮挡", "被遮挡", "血液", "血迹", "伤口",
    "尸体", "残肢", "枪支", "弹药", "爆炸物", "生殖器", "乳头", "臀部",
    "国旗", "标语", "集会", "政治人物", "毒品", "刀具", "火焰", "烟雾"
]


# ============================================================
# 基础工具函数
# ============================================================
def _safe_str(x: Any) -> str:
    try:
        return str(x)
    except Exception:
        return repr(x)


def _guess_mime_type(image_path: str) -> str:
    ext = os.path.splitext(image_path)[1].lower()
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    if ext == ".gif":
        return "image/gif"
    if ext == ".bmp":
        return "image/bmp"
    return "image/jpeg"


def _image_to_data_url(image_path: str) -> str:
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    mime = _guess_mime_type(image_path)
    return f"data:{mime};base64,{encoded}"


def _extract_json_obj_from_text(text: str) -> Dict[str, Any]:
    if not text:
        return {}

    text = text.strip()

    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

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


def _clean_list(values: List[Any], limit: int = 8) -> List[str]:
    out = []
    seen = set()
    for x in values or []:
        s = str(x).strip()
        if not s:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out[:limit]


def _contains_subjective_terms(text: str) -> List[str]:
    text = (text or "").strip()
    hits = []
    for term in SUBJECTIVE_TERMS:
        if term in text:
            hits.append(term)
    return list(dict.fromkeys(hits))


def _is_objective_condition(text: str) -> bool:
    s = (text or "").strip()
    if not s:
        return False

    if _contains_subjective_terms(s):
        return False

    if any(s.startswith(p) for p in OBJECTIVE_PREFIXES):
        return True

    return any(k in s for k in OBJECTIVE_KEYWORDS)


def _score_objectification_result(original_rule: str, preconditions: List[str]) -> Dict[str, Any]:
    if not preconditions:
        return {"score": 0.0, "issues": ["未生成任何预条件"]}

    issues = []
    valid_count = 0

    for p in preconditions:
        p = str(p).strip()
        if not p:
            issues.append("存在空预条件")
            continue

        subjective_hits = _contains_subjective_terms(p)
        if subjective_hits:
            issues.append(f"预条件仍含主观词：{p}")

        if _is_objective_condition(p):
            valid_count += 1
        else:
            issues.append(f"预条件不够可观察：{p}")

    original_subjective = _contains_subjective_terms(original_rule)
    if original_subjective:
        issues.append(f"原始规则主观词：{', '.join(original_subjective)}")

    score = valid_count / max(len(preconditions), 1)

    if len(preconditions) < 2:
        score -= 0.15
    if len(preconditions) > 8:
        score -= 0.10
    if any("主观词" in x for x in issues):
        score -= 0.20

    score = max(0.0, min(1.0, round(score, 3)))
    return {"score": score, "issues": issues}


def _normalize_rule_specs(rules: List[Any]) -> List[Dict[str, Any]]:
    """
    支持：
    1) ["原始规则1", "原始规则2"]
    2) [{"original_rule": "...", "preconditions": [...], ...}]
    """
    specs = []
    for idx, r in enumerate(rules or [], start=1):
        if isinstance(r, str):
            text = r.strip()
            if not text:
                continue
            specs.append({
                "rule_name": f"rule_{idx}",
                "original_rule": text,
                "objectified_rule": "",
                "preconditions": [],
                "subjective_spans": [],
                "observable_signals": [],
                "objectiveness_score": 0.0,
            })
            continue

        if isinstance(r, dict):
            original_rule = str(
                r.get("original_rule")
                or r.get("rule")
                or r.get("text")
                or ""
            ).strip()
            if not original_rule:
                continue

            specs.append({
                "rule_name": str(r.get("rule_name") or f"rule_{idx}").strip(),
                "original_rule": original_rule,
                "objectified_rule": str(r.get("objectified_rule") or "").strip(),
                "preconditions": _clean_list(r.get("preconditions", []), limit=8),
                "subjective_spans": _clean_list(r.get("subjective_spans", []), limit=8),
                "observable_signals": _clean_list(r.get("observable_signals", []), limit=8),
                "objectiveness_score": float(r.get("objectiveness_score") or 0.0),
            })

    return specs


# ============================================================
# OpenAI 兼容调用工具
# ============================================================
def _call_openai_text_json(prompt: str, model: Optional[str] = None, timeout: int = 120) -> Dict[str, Any]:
    if not OPENAI_API_KEY:
        raise RuntimeError("环境变量 OPENAI_API_KEY 未设置。")

    url = f"{OPENAI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model or OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": "你是严谨的安全规则分析助手，只输出 JSON 对象。"},
            {"role": "user", "content": prompt},
        ]
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    try:
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"调用文本模型失败：HTTP {resp.status_code} - {resp.text}") from e

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        raise RuntimeError(f"文本模型返回结构异常：{json.dumps(data, ensure_ascii=False)}")

    obj = _extract_json_obj_from_text(content)
    if not obj:
        raise RuntimeError(f"文本模型返回不是 JSON 对象：{content}")
    return obj


def _call_openai_vision_json(
    image_path: str,
    prompt: str,
    model: Optional[str] = None,
    timeout: int = 120
) -> Dict[str, Any]:
    if not OPENAI_API_KEY:
        raise RuntimeError("环境变量 OPENAI_API_KEY 未设置。")

    image_data_url = _image_to_data_url(image_path)

    url = f"{OPENAI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model or OPENAI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是严谨的图像安全判断助手，只输出 JSON 对象。"
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url}
                    }
                ]
            }
        ]
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    try:
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"调用视觉模型失败：HTTP {resp.status_code} - {resp.text}") from e

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        raise RuntimeError(f"视觉模型返回结构异常：{json.dumps(data, ensure_ascii=False)}")

    obj = _extract_json_obj_from_text(content)
    if not obj:
        raise RuntimeError(f"视觉模型返回不是 JSON 对象：{content}")
    return obj


# ============================================================
# 规则客观化：mock
# ============================================================
def _mock_objectify_rule(original_rule: str, keyword_triggers: dict = None) -> Dict[str, Any]:
    text = (original_rule or "").strip()
    if not text:
        return {
            "objectified_rule": "",
            "preconditions": [],
            "subjective_spans": [],
            "observable_signals": [],
            "objectiveness_score": 0.0,
            "issues": ["原始规则为空"],
            "provider": "mock-objectify"
        }

    keyword_triggers = keyword_triggers or KEYWORD_TRIGGERS

    hit_categories = []
    for cat, kws in (keyword_triggers or {}).items():
        if isinstance(kws, list) and any(kw in text for kw in kws):
            hit_categories.append(str(cat))

    templates = {
        "生殖器": {
            "rule": "当画面中出现人体私密部位且未被衣物、马赛克或其他遮挡物有效遮挡时，判定触发该规则。",
            "preconditions": [
                "画面中出现人体私密部位（生殖器/阴部/乳头/臀部）可见",
                "私密部位未被衣物、马赛克或其他遮挡物有效遮挡",
            ],
            "signals": ["私密部位可见", "未遮挡"]
        },
        "暴力血腥": {
            "rule": "当画面中出现明显血液、严重创伤、残肢或尸体等可观察暴力后果时，判定触发该规则。",
            "preconditions": [
                "画面中出现明显血液或血迹",
                "画面中出现严重创伤（开放性伤口/残肢/尸体）",
            ],
            "signals": ["血液血迹", "严重创伤"]
        },
        "涉政": {
            "rule": "当画面中出现政治相关人物、旗帜、标语或政治集会场景等可观察政治元素时，判定触发该规则。",
            "preconditions": [
                "画面中出现政治相关旗帜、徽记或标语",
                "画面中出现政治人物或政治集会场景",
            ],
            "signals": ["旗帜标语", "政治人物/集会"]
        },
        "违禁品": {
            "rule": "当画面中出现可识别的违禁物品外观特征时，判定触发该规则。",
            "preconditions": [
                "画面中出现枪支、弹药、毒品或爆炸物等违禁物品",
                "违禁物品的外观结构清晰可辨识",
            ],
            "signals": ["违禁物品出现", "结构可辨识"]
        },
    }

    if hit_categories:
        cat = hit_categories[0]
        obj = templates.get(cat, {})
        pre = _clean_list(obj.get("preconditions", []), limit=8)
        score_info = _score_objectification_result(text, pre)
        return {
            "objectified_rule": obj.get("rule", text),
            "preconditions": pre,
            "subjective_spans": _contains_subjective_terms(text),
            "observable_signals": obj.get("signals", []),
            "objectiveness_score": score_info["score"],
            "issues": score_info["issues"],
            "provider": "mock-objectify"
        }

    parts = [text]
    for sep in ["或", "以及", "并且", "且", "并", "、", "，", ",", ";", "；"]:
        if sep in text:
            parts = [p.strip() for p in text.split(sep) if p.strip()]
            break

    pre = []
    for p in parts[:4]:
        if p.startswith("画面中") or p.startswith("图像中"):
            pre.append(p)
        else:
            pre.append(f"画面中可观察到：{p}")

    pre = _clean_list(pre, limit=8)
    score_info = _score_objectification_result(text, pre)

    return {
        "objectified_rule": "当下列可观察条件成立时，判定触发该规则。",
        "preconditions": pre,
        "subjective_spans": _contains_subjective_terms(text),
        "observable_signals": [],
        "objectiveness_score": score_info["score"],
        "issues": score_info["issues"],
        "provider": "mock-objectify"
    }


# ============================================================
# 规则客观化：OpenAI 兼容接口
# ============================================================
def _build_objectify_prompt(original_rule: str, previous_issues: List[str] = None) -> str:
    issues_text = ""
    if previous_issues:
        issue_lines = [f"- {x}" for x in previous_issues if str(x).strip()]
        if issue_lines:
            issues_text = "\n上一次输出存在这些问题，请修正：\n" + "\n".join(issue_lines) + "\n"

    return f"""
你是“图像安全规则客观化器”。

任务：
把一条可能主观、模糊的图像安全规则，改写成“可观察、可判定”的客观化规则，
并拆解成 2~6 条前提链（preconditions）。

要求：
1. preconditions 必须是“画面中/图像中可观察到”的具体视觉条件。
2. 不要使用“令人不适、过度、明显、严重、可能、疑似、低俗”等主观或模糊表达。
3. 不要输出和图像内容无关的推测。
4. 输出必须是 JSON 对象，不要输出其它文字。

输出格式：
{{
  "objectified_rule": "一句完整的客观化规则",
  "preconditions": [
    "画面中出现……",
    "……未被遮挡……"
  ],
  "subjective_spans": ["原规则中的主观词1", "主观词2"],
  "observable_signals": ["信号1", "信号2"]
}}

原始规则：
{original_rule}
{issues_text}
""".strip()


def _openai_objectify_rule(original_rule: str, max_iters: int = 2) -> Optional[Dict[str, Any]]:
    if not OPENAI_API_KEY:
        return None

    issues: List[str] = []
    best_result = None
    best_score = -1.0

    for _ in range(max_iters):
        prompt = _build_objectify_prompt(original_rule, previous_issues=issues)
        try:
            obj = _call_openai_text_json(prompt=prompt, model=OPENAI_OBJECTIFY_MODEL, timeout=120)
        except Exception:
            return None

        pre = _clean_list(obj.get("preconditions", []), limit=8)
        score_info = _score_objectification_result(original_rule, pre)

        result = {
            "objectified_rule": str(obj.get("objectified_rule", "")).strip(),
            "preconditions": pre,
            "subjective_spans": _clean_list(obj.get("subjective_spans", []), limit=8),
            "observable_signals": _clean_list(obj.get("observable_signals", []), limit=8),
            "objectiveness_score": score_info["score"],
            "issues": score_info["issues"],
            "provider": "openai-objectify"
        }

        if result["objectiveness_score"] > best_score:
            best_score = result["objectiveness_score"]
            best_result = result

        if result["objectiveness_score"] >= 0.8 and len(pre) >= 2:
            return result

        issues = score_info["issues"]

    return best_result


def objectify_rule_algorithm(
    original_rule: str,
    keyword_triggers: dict = None,
    provider: Optional[str] = None,
    max_iters: int = 2
) -> Dict[str, Any]:
    """
    对外统一入口：
    {
      "objectified_rule": str,
      "preconditions": List[str],
      "subjective_spans": List[str],
      "observable_signals": List[str],
      "objectiveness_score": float,
      "issues": List[str],
      "provider": str
    }
    """
    rule_text = (original_rule or "").strip()
    if not rule_text:
        return {
            "objectified_rule": "",
            "preconditions": [],
            "subjective_spans": [],
            "observable_signals": [],
            "objectiveness_score": 0.0,
            "issues": ["原始规则为空"],
            "provider": "none"
        }

    provider = (provider or CLUE_PROVIDER or "mock").strip().lower()
    keyword_triggers = keyword_triggers or KEYWORD_TRIGGERS

    result = None
    if provider == "openai":
        result = _openai_objectify_rule(rule_text, max_iters=max_iters)

    if result is None:
        result = _mock_objectify_rule(rule_text, keyword_triggers)

    preconditions = _clean_list(result.get("preconditions", []), limit=8)
    score = float(result.get("objectiveness_score", 0.0))

    fallback = _mock_objectify_rule(rule_text, keyword_triggers)
    if (score < 0.5 or not preconditions) and float(fallback.get("objectiveness_score", 0.0)) >= score:
        result = fallback
        preconditions = _clean_list(result.get("preconditions", []), limit=8)
        score = float(result.get("objectiveness_score", 0.0))

    result["preconditions"] = preconditions
    result["objectiveness_score"] = round(score, 3)
    result.setdefault("subjective_spans", _contains_subjective_terms(rule_text))
    result.setdefault("observable_signals", [])
    result.setdefault("issues", [])
    return result


# ============================================================
# 审核算法：prompt 组装
# ============================================================
def _build_relevance_prompt(rule_spec: Dict[str, Any]) -> str:
    original_rule = rule_spec.get("original_rule", "")
    objectified_rule = rule_spec.get("objectified_rule", "")
    preconditions = rule_spec.get("preconditions", [])

    pre_text = "\n".join([f"- {x}" for x in preconditions]) if preconditions else "无"

    return f"""
你需要判断“当前图片”是否与某条图像安全规则存在明显相关性。

规则原文：
{original_rule}

客观化规则：
{objectified_rule or "无"}

预条件链：
{pre_text}

只返回 JSON：
{{
  "relevant": true,
  "confidence": 0.0,
  "reason": "一句话理由"
}}

说明：
- relevant=true 表示图片内容与该规则类别高度相关，值得进一步判断
- relevant=false 表示图片与该规则基本无关，可以跳过
- confidence 取值 0~1
""".strip()


def _build_fast_judge_prompt(rule_spec: Dict[str, Any]) -> str:
    original_rule = rule_spec.get("original_rule", "")
    objectified_rule = rule_spec.get("objectified_rule", "")
    preconditions = rule_spec.get("preconditions", [])

    pre_text = "\n".join([f"{i+1}. {x}" for i, x in enumerate(preconditions)]) if preconditions else "无"

    return f"""
你需要基于下列“客观化前提链”对当前图片做快速判断。

规则原文：
{original_rule}

客观化规则：
{objectified_rule or "无"}

预条件链：
{pre_text}

只返回 JSON：
{{
  "judgment": "violate",
  "matched_preconditions": [],
  "failed_preconditions": [],
  "uncertain_preconditions": [],
  "confidence": 0.0,
  "reason": "一句话理由"
}}

judgment 只能是：
- "violate"：足以判断违规
- "not_violate"：足以判断不违规
- "uncertain"：当前仍不确定，需要更详细推理
""".strip()


def _build_detailed_reasoning_prompt(rule_spec: Dict[str, Any]) -> str:
    original_rule = rule_spec.get("original_rule", "")
    objectified_rule = rule_spec.get("objectified_rule", "")
    preconditions = rule_spec.get("preconditions", [])

    pre_text = "\n".join([f"{i+1}. {x}" for i, x in enumerate(preconditions)]) if preconditions else "无"

    return f"""
你需要对当前图片进行更详细的规则判断。

规则原文：
{original_rule}

客观化规则：
{objectified_rule or "无"}

预条件链：
{pre_text}

请结合图片可观察内容，给出最终结论。
只返回 JSON：
{{
  "judgment": "violate",
  "matched_preconditions": [],
  "failed_preconditions": [],
  "reason": "详细但简洁的中文理由",
  "confidence": 0.0
}}

judgment 只能是：
- "violate"
- "not_violate"
""".strip()


# ============================================================
# 单规则判断：mock
# ============================================================
def _mock_judge_single_rule(image_path: str, rule_spec: Dict[str, Any]) -> Dict[str, Any]:
    original_rule = rule_spec.get("original_rule", "")
    preconditions = _clean_list(rule_spec.get("preconditions", []), limit=8)

    if not preconditions:
        obj = objectify_rule_algorithm(original_rule=original_rule, provider="mock")
        preconditions = obj.get("preconditions", [])

    hit = False
    for _, kws in KEYWORD_TRIGGERS.items():
        if any(kw in original_rule for kw in kws):
            hit = True
            break

    if hit and random.random() < 0.75:
        return {
            "relevant": True,
            "relevance_confidence": 0.8,
            "stage": "fast",
            "violated": True,
            "matched_preconditions": preconditions[:2],
            "reason": "mock 模式命中规则关键词并通过快判。",
            "confidence": 0.8,
        }

    return {
        "relevant": False,
        "relevance_confidence": 0.4,
        "stage": "relevance",
        "violated": False,
        "matched_preconditions": [],
        "reason": "mock 模式未通过相关性扫描。",
        "confidence": 0.4,
    }


# ============================================================
# 单规则判断：OpenAI 兼容接口
# ============================================================
def _judge_single_rule_openai(image_path: str, rule_spec: Dict[str, Any]) -> Dict[str, Any]:
    # 0) 若无客观化结果，先即时客观化一次
    if not rule_spec.get("preconditions"):
        obj = objectify_rule_algorithm(
            original_rule=rule_spec.get("original_rule", ""),
            provider="openai",
            max_iters=2
        )
        rule_spec = {**rule_spec, **obj}

    # 1) 相关性扫描
    relevance_prompt = _build_relevance_prompt(rule_spec)
    relevance_obj = _call_openai_vision_json(
        image_path=image_path,
        prompt=relevance_prompt,
        model=OPENAI_MODEL,
        timeout=120
    )
    relevant = bool(relevance_obj.get("relevant", False))
    relevance_conf = float(relevance_obj.get("confidence", 0.0))
    relevance_reason = str(relevance_obj.get("reason", "")).strip()

    if (not relevant) or relevance_conf < RELEVANCE_THRESHOLD:
        return {
            "relevant": relevant,
            "relevance_confidence": relevance_conf,
            "stage": "relevance",
            "violated": False,
            "matched_preconditions": [],
            "reason": relevance_reason or "规则与图片相关性不足，跳过后续判断。",
            "confidence": relevance_conf,
        }

    # 2) 快判
    fast_prompt = _build_fast_judge_prompt(rule_spec)
    fast_obj = _call_openai_vision_json(
        image_path=image_path,
        prompt=fast_prompt,
        model=OPENAI_MODEL,
        timeout=120
    )

    judgment = str(fast_obj.get("judgment", "uncertain")).strip().lower()
    fast_conf = float(fast_obj.get("confidence", 0.0))
    matched = _clean_list(fast_obj.get("matched_preconditions", []), limit=8)
    failed = _clean_list(fast_obj.get("failed_preconditions", []), limit=8)
    uncertain = _clean_list(fast_obj.get("uncertain_preconditions", []), limit=8)
    fast_reason = str(fast_obj.get("reason", "")).strip()

    if judgment == "violate" and fast_conf >= FAST_DECISION_THRESHOLD:
        return {
            "relevant": True,
            "relevance_confidence": relevance_conf,
            "stage": "fast",
            "violated": True,
            "matched_preconditions": matched,
            "failed_preconditions": failed,
            "uncertain_preconditions": uncertain,
            "reason": fast_reason or "快判阶段已足以判定违规。",
            "confidence": fast_conf,
        }

    if judgment == "not_violate" and fast_conf >= FAST_DECISION_THRESHOLD:
        return {
            "relevant": True,
            "relevance_confidence": relevance_conf,
            "stage": "fast",
            "violated": False,
            "matched_preconditions": matched,
            "failed_preconditions": failed,
            "uncertain_preconditions": uncertain,
            "reason": fast_reason or "快判阶段已足以判定不违规。",
            "confidence": fast_conf,
        }

    # 3) 细判兜底
    detailed_prompt = _build_detailed_reasoning_prompt(rule_spec)
    detail_obj = _call_openai_vision_json(
        image_path=image_path,
        prompt=detailed_prompt,
        model=OPENAI_MODEL,
        timeout=120
    )

    final_judgment = str(detail_obj.get("judgment", "not_violate")).strip().lower()
    final_conf = float(detail_obj.get("confidence", 0.0))
    final_matched = _clean_list(detail_obj.get("matched_preconditions", []), limit=8)
    final_failed = _clean_list(detail_obj.get("failed_preconditions", []), limit=8)
    final_reason = str(detail_obj.get("reason", "")).strip()

    return {
        "relevant": True,
        "relevance_confidence": relevance_conf,
        "stage": "detailed",
        "violated": final_judgment == "violate",
        "matched_preconditions": final_matched,
        "failed_preconditions": final_failed,
        "reason": final_reason or "进入细判阶段后得到最终结论。",
        "confidence": final_conf,
    }


# ============================================================
# 对外：图像审核入口
# ============================================================
def clue_algorithm(image_path: str, rules: List[Any]) -> Dict[str, Any]:
    """
    对外统一入口：
    {
      "is_safe": bool,
      "violated_rules": List[str],
      "explanation": dict
    }
    """
    rule_specs = _normalize_rule_specs(rules)
    if len(rule_specs) == 0:
        return {
            "is_safe": True,
            "violated_rules": [],
            "explanation": {
                "provider": CLUE_PROVIDER,
                "summary": "未提供规则，默认判定安全。"
            }
        }

    violated_rules = []
    stage_details = []

    for rule_spec in rule_specs:
        try:
            if CLUE_PROVIDER == "openai":
                result = _judge_single_rule_openai(image_path=image_path, rule_spec=rule_spec)
            else:
                result = _mock_judge_single_rule(image_path=image_path, rule_spec=rule_spec)
        except Exception as e:
            stage_details.append({
                "rule_name": rule_spec.get("rule_name", ""),
                "original_rule": rule_spec.get("original_rule", ""),
                "stage": "error",
                "error": str(e),
            })
            continue

        detail = {
            "rule_name": rule_spec.get("rule_name", ""),
            "original_rule": rule_spec.get("original_rule", ""),
            "objectified_rule": rule_spec.get("objectified_rule", ""),
            "preconditions": rule_spec.get("preconditions", []),
            "objectiveness_score": rule_spec.get("objectiveness_score", 0.0),
            "relevant": result.get("relevant", False),
            "relevance_confidence": result.get("relevance_confidence", 0.0),
            "stage": result.get("stage", ""),
            "violated": result.get("violated", False),
            "matched_preconditions": result.get("matched_preconditions", []),
            "failed_preconditions": result.get("failed_preconditions", []),
            "reason": result.get("reason", ""),
            "confidence": result.get("confidence", 0.0),
        }
        stage_details.append(detail)

        if result.get("violated", False):
            violated_rules.append(rule_spec.get("original_rule", ""))

    is_safe = len(violated_rules) == 0

    explanation = {
        "provider": CLUE_PROVIDER,
        "time": datetime.now().isoformat(timespec="seconds"),
        "image_path": image_path,
        "summary": "已完成规则客观化 + 相关性扫描 + 快判/细判的分阶段审核。",
        "stage_details": stage_details
    }

    return {
        "is_safe": is_safe,
        "violated_rules": violated_rules,
        "explanation": explanation
    }