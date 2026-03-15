from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from pathlib import Path
import shutil
import os
import json
import uuid
from datetime import datetime
from typing import List, Optional, Any

from backend.models import (
    get_db,
    SafetyRule,
    AuditTask,
    ApiKey,
    Dataset,
    DatasetItem,
    BenchmarkRun,
    BenchmarkRunItem,
)
import backend.clue_algorithm as clue_runtime
from backend.clue_algorithm import clue_algorithm, objectify_rule_algorithm
from backend.user_api import router as user_router

app = FastAPI(title="CLUE 图像安全自动化审核系统 API", version="1.0")
app.include_router(user_router)

# =============================
# 路径配置（适配 backend 目录）
# =============================
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
SETTINGS_FILE = BASE_DIR / "settings.json"

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
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# ============================================================
# 系统设置：/api/settings 读写 settings.json
# ============================================================
DEFAULT_SETTINGS = {
    "clue_provider": "mock",
    "mock_hit_rate": 0.75,
    "mock_random_hit_rate": 0.20,

    # 新增：真正控制 openai-compatible 调用
    "openai_base_url": "https://api.openai.com/v1",
    "openai_model": "gpt-4o-mini",
    "openai_objectify_model": "gpt-4o-mini",

    "keyword_triggers": {
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
    if not SETTINGS_FILE.exists():
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

def _apply_runtime_settings(db: Session = None):
    """
    把 settings.json + 环境变量 + 数据库 ApiKey 同步到 clue_algorithm 运行时。

    优先级：
    1. settings.json 决定 provider / base_url / model
    2. 环境变量 OPENAI_API_KEY
    3. 数据库 api_keys 表中的最后一条启用 key（环境变量为空时兜底）
    """
    s = load_settings()

    provider = str(s.get("clue_provider", "mock")).strip().lower()
    if provider not in ("mock", "openai"):
        provider = "mock"

    openai_base_url = str(
        s.get("openai_base_url", "https://api.openai.com/v1")
    ).strip().rstrip("/")

    openai_model = str(
        s.get("openai_model", "gpt-4o-mini")
    ).strip()

    openai_objectify_model = str(
        s.get("openai_objectify_model", openai_model)
    ).strip()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if (not api_key) and db is not None:
        active_key = (
            db.query(ApiKey)
            .filter(ApiKey.is_active == True)
            .order_by(ApiKey.id.desc())
            .first()
        )
        if active_key:
            api_key = (active_key.api_key or "").strip()

    # 真正把值写到 clue_algorithm 模块运行时
    clue_runtime.CLUE_PROVIDER = provider
    clue_runtime.OPENAI_API_KEY = api_key
    clue_runtime.OPENAI_BASE_URL = openai_base_url
    clue_runtime.OPENAI_MODEL = openai_model
    clue_runtime.OPENAI_OBJECTIFY_MODEL = openai_objectify_model

    return {
        "provider": provider,
        "openai_base_url": openai_base_url,
        "openai_model": openai_model,
        "openai_objectify_model": openai_objectify_model,
        "api_key_configured": bool(api_key),
    }

class SettingsIn(BaseModel):
    clue_provider: str = Field(default="mock")
    mock_hit_rate: float = Field(default=0.75, ge=0.0, le=1.0)
    mock_random_hit_rate: float = Field(default=0.20, ge=0.0, le=1.0)

    # 新增
    openai_base_url: str = Field(default="https://api.openai.com/v1")
    openai_model: str = Field(default="gpt-4o-mini")
    openai_objectify_model: str = Field(default="gpt-4o-mini")

    keyword_triggers: dict = Field(default_factory=dict)


@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    s = load_settings()
    runtime_info = _apply_runtime_settings(db)

    return {
        "status": "success",
        "data": {
            **s,
            "runtime_provider": runtime_info["provider"],
            "runtime_openai_base_url": runtime_info["openai_base_url"],
            "runtime_openai_model": runtime_info["openai_model"],
            "runtime_openai_objectify_model": runtime_info["openai_objectify_model"],
            "api_key_configured": runtime_info["api_key_configured"],
        }
    }


@app.put("/api/settings")
def update_settings(payload: SettingsIn):
    s = load_settings()

    provider = (payload.clue_provider or "mock").strip().lower()
    if provider not in ("mock", "openai"):
        raise HTTPException(status_code=400, detail="clue_provider 仅支持 mock/openai")

    s["clue_provider"] = provider
    s["mock_hit_rate"] = float(payload.mock_hit_rate)
    s["mock_random_hit_rate"] = float(payload.mock_random_hit_rate)

    s["openai_base_url"] = (payload.openai_base_url or "https://api.openai.com/v1").strip().rstrip("/")
    s["openai_model"] = (payload.openai_model or "gpt-4o-mini").strip()
    s["openai_objectify_model"] = (
        payload.openai_objectify_model or s["openai_model"]
    ).strip()

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
    runtime_info = _apply_runtime_settings()

    return {
        "status": "success",
        "data": {
            **s,
            "runtime_provider": runtime_info["provider"],
            "runtime_openai_base_url": runtime_info["openai_base_url"],
            "runtime_openai_model": runtime_info["openai_model"],
            "runtime_openai_objectify_model": runtime_info["openai_objectify_model"],
            "api_key_configured": runtime_info["api_key_configured"],
        }
    }


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
    B) 逗号/中文逗号/换行/分号 分隔的普通字符串：a,b 或 a，b 或 a\nb
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
        "objectified_rule": r.objectified_rule or "",
        "preconditions": _safe_json_loads(r.preconditions, []),
        "subjective_spans": _safe_json_loads(r.subjective_spans, []),
        "observable_signals": _safe_json_loads(r.observable_signals, []),
        "objectiveness_score": float(r.objectiveness_score or 0.0),
        "objectify_provider": r.objectify_provider or "",
        "is_active": bool(r.is_active),
        "version": r.version,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if getattr(r, "updated_at", None) else None,
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
        objectified_rule="",
        preconditions=json.dumps(pre, ensure_ascii=False),
        subjective_spans=json.dumps([], ensure_ascii=False),
        observable_signals=json.dumps([], ensure_ascii=False),
        objectiveness_score=0.0,
        objectify_provider="",
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
            rule.objectified_rule = ""
            rule.preconditions = json.dumps([], ensure_ascii=False)
            rule.subjective_spans = json.dumps([], ensure_ascii=False)
            rule.observable_signals = json.dumps([], ensure_ascii=False)
            rule.objectiveness_score = 0.0
            rule.objectify_provider = ""
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
# 规则客观化 / 预条件链生成
# ============================================================
def _load_keyword_triggers_from_settings() -> dict:
    default_triggers = {
        "生殖器": ["生殖器", "裸露", "下体", "阴部", "性器官", "乳头", "臀部"],
        "暴力血腥": ["流血", "血腥", "残肢", "尸体", "濒死", "死亡", "严重受伤", "开放性伤口"],
        "涉政": ["国旗", "领导人", "政治", "抗议", "游行", "集会", "标语"],
        "违禁品": ["毒品", "枪", "弹药", "炸弹", "爆炸物"],
    }

    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
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


@app.post("/api/rules/{rule_id}/objectify")
def objectify_rule(rule_id: int, db: Session = Depends(get_db)):
    _apply_runtime_settings(db)

    rule = db.query(SafetyRule).filter(SafetyRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    original = (rule.original_rule or "").strip()
    if not original:
        raise HTTPException(status_code=400, detail="原始规则为空，无法客观化")

    keyword_triggers = _load_keyword_triggers_from_settings()

    result = objectify_rule_algorithm(
        original_rule=original,
        keyword_triggers=keyword_triggers,
        provider=None,
        max_iters=2
    )

    rule.objectified_rule = result.get("objectified_rule", "")
    rule.preconditions = json.dumps(result.get("preconditions", []), ensure_ascii=False)
    rule.subjective_spans = json.dumps(result.get("subjective_spans", []), ensure_ascii=False)
    rule.observable_signals = json.dumps(result.get("observable_signals", []), ensure_ascii=False)
    rule.objectiveness_score = float(result.get("objectiveness_score", 0.0))
    rule.objectify_provider = result.get("provider", "")
    rule.version = (rule.version or 1) + 1

    db.add(rule)
    db.commit()
    db.refresh(rule)

    data = _rule_to_dict(rule)
    data["issues"] = result.get("issues", [])
    return {"status": "success", "data": data}


def _resolve_rules_for_audit(rule_list: List[str], db: Session) -> List[dict]:
    """
    把前端传来的规则字符串，解析成完整规则对象：
    - 若数据库已有该规则，则带上 objectified_rule / preconditions / score
    - 若数据库没有，则现场客观化一次
    """
    keyword_triggers = _load_keyword_triggers_from_settings()
    resolved = []

    for text in rule_list:
        rule_text = str(text).strip()
        if not rule_text:
            continue

        db_rule = db.query(SafetyRule).filter(SafetyRule.original_rule == rule_text).first()
        if db_rule:
            resolved.append({
                "rule_name": db_rule.rule_name,
                "original_rule": db_rule.original_rule,
                "objectified_rule": db_rule.objectified_rule or "",
                "preconditions": _safe_json_loads(db_rule.preconditions, []),
                "subjective_spans": _safe_json_loads(db_rule.subjective_spans, []),
                "observable_signals": _safe_json_loads(db_rule.observable_signals, []),
                "objectiveness_score": float(db_rule.objectiveness_score or 0.0),
            })
            continue

        obj = objectify_rule_algorithm(
            original_rule=rule_text,
            keyword_triggers=keyword_triggers,
            provider=None,
            max_iters=2
        )
        resolved.append({
            "rule_name": rule_text[:20],
            "original_rule": rule_text,
            "objectified_rule": obj.get("objectified_rule", ""),
            "preconditions": obj.get("preconditions", []),
            "subjective_spans": obj.get("subjective_spans", []),
            "observable_signals": obj.get("observable_signals", []),
            "objectiveness_score": float(obj.get("objectiveness_score", 0.0)),
        })

    return resolved


# ============================================================
# 2) 核心审核
# ============================================================
@app.post("/api/moderate")
async def moderate_image(
    file: UploadFile = File(...),
    rules: str = Form(...),
    db: Session = Depends(get_db),
):
    _apply_runtime_settings(db)

    rule_list = parse_rules_input(rules)
    if not rule_list:
        raise HTTPException(status_code=400, detail="规则列表为空，无法执行审核")

    file_ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{file_ext}"
    file_path = UPLOAD_DIR / filename

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    resolved_rules = _resolve_rules_for_audit(rule_list, db)

    start_time = datetime.now()
    try:
        audit_result = clue_algorithm(image_path=str(file_path), rules=resolved_rules)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"审核引擎执行失败: {str(e)}")

    inference_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    task_status = "auto_pass" if audit_result.get("is_safe", True) else "auto_reject"

    task = AuditTask(
        task_id=f"TASK_{uuid.uuid4().hex[:8].upper()}",
        file_path=str(file_path),
        mllm_score=None,
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
            "explanation": audit_result.get("explanation", {}),
        },
    }


@app.post("/api/moderate/batch")
async def moderate_images_batch(
    files: List[UploadFile] = File(...),
    rules: str = Form(...),
    db: Session = Depends(get_db),
):
    _apply_runtime_settings(db)

    rule_list = parse_rules_input(rules)
    if not rule_list:
        raise HTTPException(status_code=400, detail="规则列表为空，无法执行批量审核")

    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="未上传任何图片")

    results = []
    success_count = 0
    fail_count = 0

    for file in files:
        try:
            content_type = (file.content_type or "").lower()
            filename_lower = (file.filename or "").lower()
            if not (
                content_type.startswith("image/")
                or filename_lower.endswith(".jpg")
                or filename_lower.endswith(".jpeg")
                or filename_lower.endswith(".png")
                or filename_lower.endswith(".webp")
                or filename_lower.endswith(".gif")
                or filename_lower.endswith(".bmp")
            ):
                fail_count += 1
                results.append({
                    "filename": file.filename,
                    "status": "failed",
                    "detail": "不是受支持的图片文件"
                })
                continue

            file_ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
            saved_name = f"{uuid.uuid4().hex}.{file_ext}"
            file_path = UPLOAD_DIR / saved_name

            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)

            resolved_rules = _resolve_rules_for_audit(rule_list, db)

            start_time = datetime.now()
            audit_result = clue_algorithm(image_path=str(file_path), rules=resolved_rules)
            inference_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            task_status = "auto_pass" if audit_result.get("is_safe", True) else "auto_reject"

            task = AuditTask(
                task_id=f"TASK_{uuid.uuid4().hex[:8].upper()}",
                file_path=str(file_path),
                mllm_is_safe=bool(audit_result.get("is_safe", True)),
                violated_details=json.dumps(audit_result.get("violated_rules", []), ensure_ascii=False),
                inference_time_ms=inference_time_ms,
                status=task_status,
            )
            db.add(task)
            db.commit()
            db.refresh(task)

            success_count += 1
            results.append({
                "filename": file.filename,
                "task_id": task.task_id,
                "image_url": f"http://127.0.0.1:8000/uploads/{saved_name}",
                "is_safe": bool(audit_result.get("is_safe", True)),
                "violated_rules": audit_result.get("violated_rules", []),
                "inference_time_ms": inference_time_ms,
                "status": task_status,
            })

        except Exception as e:
            fail_count += 1
            results.append({
                "filename": file.filename,
                "status": "failed",
                "detail": str(e)
            })

    return {
        "status": "success",
        "data": {
            "total": len(files),
            "success_count": success_count,
            "fail_count": fail_count,
            "items": results
        }
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


@app.delete("/api/audit-tasks/{task_id}")
def delete_audit_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(AuditTask).filter(AuditTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="审核任务不存在")

    try:
        if task.file_path and os.path.exists(task.file_path):
            os.remove(task.file_path)
    except Exception:
        pass

    db.delete(task)
    db.commit()

    return {
        "status": "success",
        "data": {
            "deleted": task_id
        }
    }

# ============================================================
# 4) 数据集测试系统：Dataset API（新增）
# ============================================================
from backend.models import Dataset, DatasetItem, BenchmarkRun, BenchmarkRunItem


class DatasetCreateIn(BaseModel):
    dataset_name: str = Field(..., min_length=1, description="数据集名称")
    description: Optional[str] = Field(default="", description="数据集描述")


def _dataset_to_dict(d: Dataset):
    return {
        "id": d.id,
        "dataset_name": d.dataset_name,
        "description": d.description or "",
        "total_count": d.total_count or 0,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if getattr(d, "updated_at", None) else None,
    }


def _dataset_item_to_dict(item: DatasetItem):
    basename = os.path.basename(item.file_path) if item.file_path else item.filename
    return {
        "id": item.id,
        "dataset_id": item.dataset_id,
        "filename": item.filename,
        "file_path": item.file_path,
        "image_url": f"http://127.0.0.1:8000/uploads/{basename}" if basename else None,
        "ground_truth_is_safe": bool(item.ground_truth_is_safe),
        "ground_truth_rule": item.ground_truth_rule or "",
        "split_type": item.split_type or "test",
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@app.post("/api/datasets")
def create_dataset(payload: DatasetCreateIn, db: Session = Depends(get_db)):
    name = (payload.dataset_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="数据集名称不能为空")

    exists = db.query(Dataset).filter(Dataset.dataset_name == name).first()
    if exists:
        raise HTTPException(status_code=400, detail="数据集名称已存在")

    dataset = Dataset(
        dataset_name=name,
        description=(payload.description or "").strip(),
        total_count=0,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return {"status": "success", "data": _dataset_to_dict(dataset)}


@app.get("/api/datasets")
def list_datasets(db: Session = Depends(get_db)):
    datasets = db.query(Dataset).order_by(Dataset.id.desc()).all()
    return {"status": "success", "data": [_dataset_to_dict(d) for d in datasets]}


@app.get("/api/datasets/{dataset_id}")
def get_dataset_detail(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")

    items = (
        db.query(DatasetItem)
        .filter(DatasetItem.dataset_id == dataset_id)
        .order_by(DatasetItem.id.desc())
        .all()
    )

    return {
        "status": "success",
        "data": {
            **_dataset_to_dict(dataset),
            "items": [_dataset_item_to_dict(x) for x in items]
        }
    }


@app.delete("/api/datasets/{dataset_id}")
def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")

    items = db.query(DatasetItem).filter(DatasetItem.dataset_id == dataset_id).all()

    # 删除对应图片文件
    for item in items:
        try:
            if item.file_path and os.path.exists(item.file_path):
                os.remove(item.file_path)
        except Exception:
            pass

    db.delete(dataset)
    db.commit()

    return {"status": "success", "data": {"deleted": dataset_id}}


@app.post("/api/datasets/{dataset_id}/items/upload")
async def upload_dataset_items(
    dataset_id: int,
    files: List[UploadFile] = File(...),
    ground_truth_is_safe: bool = Form(...),
    ground_truth_rule: str = Form(""),
    split_type: str = Form("test"),
    db: Session = Depends(get_db),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")

    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="未上传任何文件")

    saved_items = []

    for file in files:
        content_type = (file.content_type or "").lower()
        filename_lower = (file.filename or "").lower()

        if not (
            content_type.startswith("image/")
            or filename_lower.endswith(".jpg")
            or filename_lower.endswith(".jpeg")
            or filename_lower.endswith(".png")
            or filename_lower.endswith(".webp")
            or filename_lower.endswith(".gif")
            or filename_lower.endswith(".bmp")
        ):
            continue

        file_ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
        saved_name = f"dataset_{uuid.uuid4().hex}.{file_ext}"
        file_path = UPLOAD_DIR / saved_name

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        item = DatasetItem(
            dataset_id=dataset.id,
            file_path=str(file_path),
            filename=file.filename or saved_name,
            ground_truth_is_safe=bool(ground_truth_is_safe),
            ground_truth_rule=(ground_truth_rule or "").strip(),
            split_type=(split_type or "test").strip() or "test",
        )
        db.add(item)
        db.flush()
        saved_items.append(item)

    dataset.total_count = db.query(DatasetItem).filter(DatasetItem.dataset_id == dataset.id).count()

    db.commit()

    return {
        "status": "success",
        "data": {
            "dataset": _dataset_to_dict(dataset),
            "uploaded_count": len(saved_items),
            "items": [_dataset_item_to_dict(x) for x in saved_items]
        }
    }

# ============================================================
# 5) 数据集测试系统：Benchmark API（新增）
# ============================================================
class BenchmarkRunIn(BaseModel):
    dataset_id: int
    run_name: str = Field(..., min_length=1, description="评测名称")


def _safe_div(a: float, b: float) -> float:
    if b == 0:
        return 0.0
    return round(a / b, 4)


def _benchmark_run_to_dict(run: BenchmarkRun):
    return {
        "id": run.id,
        "run_name": run.run_name,
        "dataset_id": run.dataset_id,
        "provider": run.provider or "mock",
        "total_count": run.total_count or 0,
        "safe_count": run.safe_count or 0,
        "unsafe_count": run.unsafe_count or 0,
        "tp": run.tp or 0,
        "tn": run.tn or 0,
        "fp": run.fp or 0,
        "fn": run.fn or 0,
        "accuracy": float(run.accuracy or 0.0),
        "precision": float(run.precision or 0.0),
        "recall": float(run.recall or 0.0),
        "f1_score": float(run.f1_score or 0.0),
        "avg_inference_time_ms": float(run.avg_inference_time_ms or 0.0),
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


def _benchmark_item_to_dict(item: BenchmarkRunItem):
    dataset_item = item.dataset_item
    basename = os.path.basename(dataset_item.file_path) if dataset_item and dataset_item.file_path else ""
    return {
        "id": item.id,
        "run_id": item.run_id,
        "dataset_item_id": item.dataset_item_id,
        "filename": dataset_item.filename if dataset_item else "",
        "image_url": f"http://127.0.0.1:8000/uploads/{basename}" if basename else None,
        "ground_truth_is_safe": bool(dataset_item.ground_truth_is_safe) if dataset_item else None,
        "ground_truth_rule": dataset_item.ground_truth_rule if dataset_item else "",
        "predicted_is_safe": bool(item.predicted_is_safe),
        "predicted_rules": _safe_json_loads(item.predicted_rules, []),
        "hit": bool(item.hit),
        "inference_time_ms": item.inference_time_ms or 0,
        "raw_explanation": _safe_json_loads(item.raw_explanation, {}),
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@app.post("/api/benchmarks/run")
def run_benchmark(payload: BenchmarkRunIn, db: Session = Depends(get_db)):
    runtime_info = _apply_runtime_settings(db)

    dataset = db.query(Dataset).filter(Dataset.id == payload.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")

    dataset_items = (
        db.query(DatasetItem)
        .filter(DatasetItem.dataset_id == dataset.id)
        .order_by(DatasetItem.id.asc())
        .all()
    )
    if not dataset_items:
        raise HTTPException(status_code=400, detail="该数据集下没有样本，无法运行评测")

    active_rules = (
        db.query(SafetyRule)
        .filter(SafetyRule.is_active == True)
        .order_by(SafetyRule.id.asc())
        .all()
    )
    if not active_rules:
        raise HTTPException(status_code=400, detail="当前没有启用中的规则，无法运行评测")

    resolved_rules = []
    for r in active_rules:
        resolved_rules.append({
            "rule_name": r.rule_name,
            "original_rule": r.original_rule,
            "objectified_rule": r.objectified_rule or "",
            "preconditions": _safe_json_loads(r.preconditions, []),
            "subjective_spans": _safe_json_loads(r.subjective_spans, []),
            "observable_signals": _safe_json_loads(r.observable_signals, []),
            "objectiveness_score": float(r.objectiveness_score or 0.0),
        })

    provider = runtime_info["provider"]

    run = BenchmarkRun(
        run_name=(payload.run_name or "").strip(),
        dataset_id=dataset.id,
        provider=provider,
        total_count=0,
        safe_count=0,
        unsafe_count=0,
        tp=0,
        tn=0,
        fp=0,
        fn=0,
        accuracy=0.0,
        precision=0.0,
        recall=0.0,
        f1_score=0.0,
        avg_inference_time_ms=0.0,
    )
    db.add(run)
    db.flush()

    total = len(dataset_items)
    safe_count = 0
    unsafe_count = 0
    tp = tn = fp = fn = 0
    total_inference_time = 0

    for item in dataset_items:
        start_time = datetime.now()
        try:
            audit_result = clue_algorithm(image_path=item.file_path, rules=resolved_rules)
        except Exception as e:
            audit_result = {
                "is_safe": True,
                "violated_rules": [],
                "explanation": {"error": str(e)}
            }

        inference_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        total_inference_time += inference_time_ms

        predicted_is_safe = bool(audit_result.get("is_safe", True))
        predicted_rules = audit_result.get("violated_rules", [])
        ground_truth_is_safe = bool(item.ground_truth_is_safe)

        hit = predicted_is_safe == ground_truth_is_safe

        if ground_truth_is_safe:
            safe_count += 1
            if predicted_is_safe:
                tn += 1
            else:
                fp += 1
        else:
            unsafe_count += 1
            if predicted_is_safe:
                fn += 1
            else:
                tp += 1

        run_item = BenchmarkRunItem(
            run_id=run.id,
            dataset_item_id=item.id,
            predicted_is_safe=predicted_is_safe,
            predicted_rules=json.dumps(predicted_rules, ensure_ascii=False),
            hit=hit,
            inference_time_ms=inference_time_ms,
            raw_explanation=json.dumps(audit_result.get("explanation", {}), ensure_ascii=False),
        )
        db.add(run_item)

    accuracy = _safe_div(tp + tn, total)
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1_score = 0.0 if (precision + recall) == 0 else round(2 * precision * recall / (precision + recall), 4)
    avg_inference_time_ms = round(total_inference_time / total, 2) if total > 0 else 0.0

    run.total_count = total
    run.safe_count = safe_count
    run.unsafe_count = unsafe_count
    run.tp = tp
    run.tn = tn
    run.fp = fp
    run.fn = fn
    run.accuracy = accuracy
    run.precision = precision
    run.recall = recall
    run.f1_score = f1_score
    run.avg_inference_time_ms = avg_inference_time_ms

    db.commit()
    db.refresh(run)

    return {"status": "success", "data": _benchmark_run_to_dict(run)}


@app.get("/api/benchmarks/runs")
def list_benchmark_runs(db: Session = Depends(get_db)):
    runs = db.query(BenchmarkRun).order_by(BenchmarkRun.id.desc()).all()
    return {"status": "success", "data": [_benchmark_run_to_dict(x) for x in runs]}


@app.get("/api/benchmarks/runs/{run_id}")
def get_benchmark_run_detail(run_id: int, db: Session = Depends(get_db)):
    run = db.query(BenchmarkRun).filter(BenchmarkRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="评测记录不存在")

    items = (
        db.query(BenchmarkRunItem)
        .filter(BenchmarkRunItem.run_id == run_id)
        .order_by(BenchmarkRunItem.id.asc())
        .all()
    )

    wrong_items = [x for x in items if not x.hit]

    return {
        "status": "success",
        "data": {
            **_benchmark_run_to_dict(run),
            "items": [_benchmark_item_to_dict(x) for x in items],
            "wrong_items": [_benchmark_item_to_dict(x) for x in wrong_items],
        }
    }