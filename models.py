from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

# ==========================================
# 1. 数据库连接配置
# ==========================================
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:123456@localhost:3306/clue_audit_db?charset=utf8mb4"

engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==========================================
# 2. 核心数据表 ORM 模型
# ==========================================

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="operator")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class SafetyRule(Base):
    __tablename__ = "safety_rules"
    id = Column(Integer, primary_key=True, index=True)

    # 原始规则
    rule_name = Column(String(100), nullable=False)
    original_rule = Column(Text, nullable=False)

    # 客观化结果
    objectified_rule = Column(Text, nullable=True)          # 客观化后的规则总述
    preconditions = Column(Text, nullable=True)             # JSON字符串：客观化前提链
    subjective_spans = Column(Text, nullable=True)          # JSON字符串：识别出的主观词片段
    observable_signals = Column(Text, nullable=True)        # JSON字符串：可观察信号
    objectiveness_score = Column(Float, nullable=True)      # 客观性评分 0~1
    objectify_provider = Column(String(50), nullable=True)  # mock-objectify / openai-objectify

    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AuditTask(Base):
    __tablename__ = "audit_tasks"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(100), unique=True, index=True)
    file_path = Column(String(255), nullable=False)

    # 机器审核
    mllm_score = Column(Float)
    mllm_is_safe = Column(Boolean)
    violated_details = Column(Text)
    inference_time_ms = Column(Integer)

    # 状态
    status = Column(String(50), default="pending_review")

    # 人工复核
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    manual_decision = Column(String(20), nullable=True)
    review_reason = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String(100), unique=True, index=True, nullable=False)
    client_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


# ==========================================
# 3. 数据库依赖注入
# ==========================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()