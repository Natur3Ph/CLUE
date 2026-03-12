from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import shutil
import os
import json
import uuid
import traceback
from datetime import datetime
from typing import List, Optional, Any

from models import get_db, SafetyRule, AuditTask
from clue_algorithm import clue_algorithm
from user_api import router as user_router

app = FastAPI(title="CLUE 图像安全自动化审核系统 API", version="1.0")
app.include_router(user_router)

# =============================
# CORS
# =============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 开发阶段允许全部
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================
# uploads 静态资源
# =============================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# ============================================================
# ✅ 系统设置（新增）：/api/settings 读写 settings.json
# ============================================================
SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "clue_provider": "mock",         # mock | openai
    "mock_hit_rate": 0.75,           # 命中关键词后的触发概率
    "mock_random_hit_rate": 0.20,    # 若无命中，随机兜底命中一条的概率
    "keyword_triggers": {            # mock 关键词触发器：类别 -> 关键词数组
        "生殖器": ["生殖器", "裸露", "下体", "阴部", "性器官"],
        "暴力血腥": ["流血", "血腥", "残肢", "尸体", "濒死", "死亡", "严重受伤"],
        "涉政": ["国旗", "领导人", "政治", "抗议", "游行"],
        "违禁品": ["毒品", "枪", "弹药", "炸弹"],
    },
}


def save_settings(data: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_settings() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        merged = {**DEFAULT_SETTINGS, **data}
        if "keyword_triggers" not in merged or not isinstance(merged["keyword_triggers"], dict):
            merged["keyword_triggers"] = DEFAULT_SETTINGS["keyword_triggers"]
        return merged
    except Exception:
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS


class SettingsIn(BaseModel):
    clue_provider: str = Field(default="mock")
    mock_hit_rate: float = Field(default=0.75, ge=0.0, le=1.0)
    mock_random_hit_rate: float = Field(default=0.20, ge=0.0, le=1.0)
    keyword_triggers: dict = Field(default_factory=dict)


@app.get("/api/settings")
def get_settings():
    return {"status": "success", "data": load_settings()}


@app.put("/api/settings")
def update_settings(payload: SettingsIn):
    s = load_settings()

    provider = (payload.clue_provider or "mock").strip().lower()
    if provider not in ("mock", "openai"):
        raise HTTPException(status_code=400, detail="clue_provider 仅支持 mock/openai")

    s["clue_provider"] = provider
    s["mock_hit_rate"] = float(payload.mock_hit_rate)
    s["mock_random_hit_rate"] = float(payload.mock_random_hit_rate)

    kt = payload.keyword_triggers or {}
    cleaned = {}
    for k, v in kt.items():
        if not k:
            continue

        if isinstance(v, list):
            cleaned[str(k)] = [str(x) for x in v if str(x).strip()]
        else:
            txt = str(v)
            parts = []
            for sep in [",", "，", "\n", ";", "；"]:
                if sep in txt:
                    parts = [p.strip() for p in txt.split(sep) if p.strip()]
                    break
            if not parts and txt.strip():
                parts = [txt.strip()]
            cleaned[str(k)] = parts

    s["keyword_triggers"] = cleaned if cleaned else DEFAULT_SETTINGS["keyword_triggers"]

    save_settings(s)
    return {"status": "success", "data": s}


# ============================================================
# 工具：规则输入标准化
# ============================================================
def normalize_rules(raw_rules) -> List[str]:
    """
    支持三种情况：
    1) ["规则1", "规则2"]
    2) [{"id":1,"text":"规则1"}]
    3) [{"rule":"规则1"}]
    """
    normalized: List[str] = []
    for r in raw_rules:
        if isinstance(r, str):
            normalized.append(r)
        elif isinstance(r, dict):
            if "text" in r:
                normalized.append(str(r["text"]))
            elif "rule" in r:
                normalized.append(str(r["rule"]))
            else:
                normalized.append(str(r))
        else:
            normalized.append(str(r))
    return list({x.strip() for x in normalized if x and str(x).strip()})


def parse_rules_input(rules: str) -> List[str]:
    """
    兼容两类输入：
    A) JSON 数组字符串：["a","b"] 或 [{"text":"a"}]
    B) 逗号/中文逗号/换行/分号 分隔的普通字符串：a,b 或 a，b 或 a\\n b
    """
    if rules is None:
        return []
    s = rules.strip()
    if not s:
        return []

    try:
        raw = json.loads(s)
        if isinstance(raw, list):
            return normalize_rules(raw)
    except Exception:
        pass

    for sep in [",", "，", "\n", ";", "；"]:
        if sep in s:
            parts = [p.strip() for p in s.split(sep) if p.strip()]
            return normalize_rules(parts)

    return normalize_rules([s])


def _safe_json_loads(s: Optional[str], default: Any):
    if not s:
        return default
    try:
        return json.loads(s)
    except Exception:
        return default


# ============================================================
# Pydantic：规则 CRUD
# ============================================================
class RuleCreateIn(BaseModel):
    rule_name: Optional[str] = Field(default=None, description="规则名称（可空，后端会自动生成）")
    original_rule: str = Field(..., min_length=1, description="规则原文（管理端输入）")
    preconditions: Optional[list] = Field(default=None, description="客观化子条件链（list）")
    is_active: bool = True


class RuleUpdateIn(BaseModel):
    rule_name: Optional[str] = None
    original_rule: Optional[str] = None
    preconditions: Optional[list] = None
    is_active: Optional[bool] = None


class RuleActiveIn(BaseModel):
    is_active: bool


def _rule_to_dict(r: SafetyRule):
    return {
        "id": r.id,
        "rule_name": r.rule_name,
        "original_rule": r.original_rule,
        "preconditions": _safe_json_loads(r.preconditions, []),
        "is_active": bool(r.is_active),
        "version": r.version,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


# ============================================================
# 1) 规则查询（前端：规则管理页/创建任务页都用）
# ============================================================
@app.get("/api/rules")
def list_rules(
    all: bool = Query(default=False, description="true=返回全部规则；false=仅返回启用规则"),
    db: Session = Depends(get_db),
):
    q = db.query(SafetyRule)
    if not all:
        q = q.filter(SafetyRule.is_active == True)
    rules = q.order_by(SafetyRule.id.desc()).all()

    if not rules:
        demo = [
            {"id": 1, "rule_name": "裸露/性内容", "original_rule": "图像中出现了人物的生殖器或臀部未被遮挡",
             "preconditions": [], "is_active": True, "version": 1, "created_at": None},
            {"id": 2, "rule_name": "严重暴力", "original_rule": "包含人物因严重受伤流血而濒临死亡的画面",
             "preconditions": [], "is_active": True, "version": 1, "created_at": None},
        ]
        return {"status": "success", "data": demo}

    return {"status": "success", "data": [_rule_to_dict(r) for r in rules]}


@app.post("/api/rules")
def create_rule(payload: RuleCreateIn, db: Session = Depends(get_db)):
    name = (payload.rule_name or "").strip()
    if not name:
        name = payload.original_rule.strip()[:20]

    pre = payload.preconditions if isinstance(payload.preconditions, list) else []
    rule = SafetyRule(
        rule_name=name,
        original_rule=payload.original_rule.strip(),
        preconditions=json.dumps(pre, ensure_ascii=False),
        is_active=bool(payload.is_active),
        version=1,
        created_at=datetime.now(),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"status": "success", "data": _rule_to_dict(rule)}


@app.put("/api/rules/{rule_id}")
def update_rule(rule_id: int, payload: RuleUpdateIn, db: Session = Depends(get_db)):
    rule = db.query(SafetyRule).filter(SafetyRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    changed = False

    if payload.rule_name is not None:
        rn = payload.rule_name.strip()
        if rn and rn != rule.rule_name:
            rule.rule_name = rn
            changed = True

    if payload.original_rule is not None:
        orr = payload.original_rule.strip()
        if orr and orr != rule.original_rule:
            rule.original_rule = orr
            changed = True

    if payload.preconditions is not None:
        pre = payload.preconditions if isinstance(payload.preconditions, list) else []
        new_pre_s = json.dumps(pre, ensure_ascii=False)
        if new_pre_s != (rule.preconditions or ""):
            rule.preconditions = new_pre_s
            changed = True

    if payload.is_active is not None:
        if bool(payload.is_active) != bool(rule.is_active):
            rule.is_active = bool(payload.is_active)

    if changed:
        rule.version = (rule.version or 1) + 1

    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"status": "success", "data": _rule_to_dict(rule)}


@app.patch("/api/rules/{rule_id}/active")
def set_rule_active(rule_id: int, payload: RuleActiveIn, db: Session = Depends(get_db)):
    rule = db.query(SafetyRule).filter(SafetyRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    rule.is_active = bool(payload.is_active)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"status": "success", "data": _rule_to_dict(rule)}


@app.delete("/api/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(SafetyRule).filter(SafetyRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    db.delete(rule)
    db.commit()
    return {"status": "success", "data": {"deleted": rule_id}}


# ============================================================
# ✅ 规则客观化 / 预条件链生成（新增）
# ============================================================
def _load_keyword_triggers_from_settings() -> dict:
    default_triggers = {
        "生殖器": ["生殖器", "裸露", "下体", "阴部", "性器官"],
        "暴力血腥": ["流血", "血腥", "残肢", "尸体", "濒死", "死亡", "严重受伤"],
        "涉政": ["国旗", "领导人", "政治", "抗议", "游行"],
        "违禁品": ["毒品", "枪", "弹药", "炸弹"],
    }

    try:
        if os.path.exists("settings.json"):
            with open("settings.json", "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            kt = data.get("keyword_triggers")
            if isinstance(kt, dict) and kt:
                cleaned = {}
                for k, v in kt.items():
                    if not k:
                        continue
                    if isinstance(v, list):
                        cleaned[str(k)] = [str(x) for x in v if str(x).strip()]
                    else:
                        cleaned[str(k)] = [str(v).strip()] if str(v).strip() else []
                return cleaned or default_triggers
    except Exception:
        pass

    return default_triggers


def _mock_objectify_rule(original_rule: str, keyword_triggers: dict) -> List[str]:
    text = (original_rule or "").strip()
    if not text:
        return []

    hit_categories = []
    for cat, kws in (keyword_triggers or {}).items():
        if isinstance(kws, list) and any(kw in text for kw in kws):
            hit_categories.append(str(cat))

    templates = {
        "生殖器": [
            "画面中出现人体私密部位（生殖器/阴部/乳头）可见",
            "私密部位未被衣物或遮挡物有效遮挡",
        ],
        "暴力血腥": [
            "画面中出现明显血液/血迹",
            "画面中出现严重创伤（开放性伤口/残肢/尸体）",
        ],
        "涉政": [
            "画面包含政治相关符号/场景（旗帜/标语/集会）",
            "画面包含敏感政治人物或政治性行为场景",
        ],
        "违禁品": [
            "画面中出现违禁物品（毒品/枪支/弹药/爆炸物）",
            "违禁物品具有可识别的外观特征（形状/结构清晰可辨）",
        ],
    }

    pre = []
    for cat in hit_categories:
        for s in templates.get(cat, []):
            pre.append(s)

    if not pre:
        splitters = ["或", "以及", "并且", "且", "并", "、", "，", ","]
        parts = [text]
        for sp in splitters:
            if sp in text:
                parts = [p.strip() for p in text.split(sp) if p.strip()]
                break

        for p in parts[:3]:
            if p.startswith("图像") or p.startswith("图片") or p.startswith("画面"):
                pre.append(p)
            else:
                pre.append(f"画面中可观察到：{p}")

    seen = set()
    out = []
    for x in pre:
        x = str(x).strip()
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)

    return out[:6]


def _openai_objectify_rule(original_rule: str) -> Optional[List[str]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        return None

    rule_text = (original_rule or "").strip()
    if not rule_text:
        return []

    model = os.getenv("OPENAI_RULE_OBJECTIFY_MODEL", "gpt-4o-mini")
    client = OpenAI()

    prompt = f"""
你是“安全审核规则客观化器”。请把下面这条原始规则，转换为 2~6 条“可观察、可判定”的预条件（中文），每条必须是具体可见特征，不要包含模糊词（如“令人不适”“过度”“可能”）。
只输出 JSON 数组（string[]），不要输出其它文字。

原始规则：
{rule_text}
""".strip()

    try:
        resp = client.responses.create(
            model=model,
            input=prompt,
        )
        text_out = getattr(resp, "output_text", None)
        if not text_out:
            text_out = str(resp)

        arr = json.loads(text_out)
        if isinstance(arr, list):
            cleaned = [str(x).strip() for x in arr if str(x).strip()]
            return cleaned[:8]
        return None
    except Exception:
        return None


@app.post("/api/rules/{rule_id}/objectify")
def objectify_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(SafetyRule).filter(SafetyRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    original = (rule.original_rule or "").strip()
    if not original:
        raise HTTPException(status_code=400, detail="原始规则为空，无法客观化")

    keyword_triggers = _load_keyword_triggers_from_settings()

    pre = _openai_objectify_rule(original)

    if pre is None:
        pre = _mock_objectify_rule(original, keyword_triggers)

    rule.preconditions = json.dumps(pre, ensure_ascii=False)
    rule.version = (rule.version or 1) + 1

    db.add(rule)
    db.commit()
    db.refresh(rule)

    return {"status": "success", "data": _rule_to_dict(rule)}


# ============================================================
# 2) 核心审核
# ============================================================
@app.post("/api/moderate")
async def moderate_image(
    file: UploadFile = File(...),
    rules: str = Form(...),
    db: Session = Depends(get_db),
):
    rule_list = parse_rules_input(rules)
    if not rule_list:
        raise HTTPException(status_code=400, detail="规则列表为空，无法执行审核")

    file_ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    start_time = datetime.now()
    try:
        audit_result = clue_algorithm(image_path=file_path, rules=rule_list)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"审核引擎执行失败: {str(e)}")

    inference_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    task_status = "auto_pass" if audit_result.get("is_safe", True) else "auto_reject"

    task = AuditTask(
        task_id=f"TASK_{uuid.uuid4().hex[:8].upper()}",
        file_path=file_path,
        mllm_is_safe=bool(audit_result.get("is_safe", True)),
        violated_details=json.dumps(audit_result.get("violated_rules", []), ensure_ascii=False),
        inference_time_ms=inference_time_ms,
        status=task_status,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "status": "success",
        "data": {
            "task_id": task.task_id,
            "image_url": f"http://127.0.0.1:8000/uploads/{filename}",
            "is_safe": bool(audit_result.get("is_safe", True)),
            "violated_rules": audit_result.get("violated_rules", []),
            "inference_time_ms": inference_time_ms,
        },
    }


# ============================================================
# 3) 审核台账（给前端列表/仪表盘用）
# ============================================================
@app.get("/api/audit-tasks")
def get_audit_tasks(limit: int = 10, db: Session = Depends(get_db)):
    tasks = (
        db.query(AuditTask)
        .order_by(AuditTask.created_at.desc())
        .limit(limit)
        .all()
    )

    data = []
    for t in tasks:
        basename = os.path.basename(t.file_path) if t.file_path else ""
        img_url = f"http://127.0.0.1:8000/uploads/{basename}" if basename else None
        data.append(
            {
                "task_id": t.task_id,
                "image_url": img_url,
                "is_safe": t.mllm_is_safe,
                "violated_details": _safe_json_loads(t.violated_details, []),
                "inference_time_ms": t.inference_time_ms or 0,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
        )

    return {"status": "success", "data": data}