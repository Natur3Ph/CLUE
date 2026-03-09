from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

# ==========================================
# 1. 数据库连接配置
# ==========================================
# 请将用户名(root)和密码(123456)替换为你自己在 HeidiSQL 里的账号密码
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:123456@localhost:3306/clue_audit_db?charset=utf8mb4"

engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==========================================
# 2. 核心数据表 ORM 模型 (映射7大功能模块)
# ==========================================

# 表1：用户与权限表 (支撑【模块6：多角色权限控制中心】)
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="operator")  # 角色：admin (管理员) / operator (人工审核员)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


# 表2：安全规则与沙盒表 (支撑【模块1：规则工程与客观化沙盒模块】)
class SafetyRule(Base):
    __tablename__ = "safety_rules"
    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(100), nullable=False)  # 规则简短名称，如“禁止暴力”
    original_rule = Column(Text, nullable=False)  # 管理员输入的原始主观规则
    preconditions = Column(Text)  # LLM客观化拆解后的子条件链 (JSON字符串存储)
    is_active = Column(Boolean, default=True)  # 是否在前端审核规则列表中启用
    version = Column(Integer, default=1)  # 规则版本号
    created_at = Column(DateTime, default=datetime.now)


# 表3：全息审核台账表 (支撑【模块2：大模型审核】、【模块3：人机协同】、【模块5：台账追溯】)
class AuditTask(Base):
    __tablename__ = "audit_tasks"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(100), unique=True, index=True)  # 业务流水号，模拟工单号
    file_path = Column(String(255), nullable=False)  # 图片存储路径

    # 机器审核部分 (MLLM)
    mllm_score = Column(Float)  # 大模型去偏推理给出的风险得分 (0-1)
    mllm_is_safe = Column(Boolean)  # 机器判定是否安全
    violated_details = Column(Text)  # 触发的违规条件详情 (JSON字符串)
    inference_time_ms = Column(Integer)  # 大模型推理耗时(毫秒)，用于性能监控大屏

    # 状态机与人机协同部分
    # 状态: auto_pass(机器放行), auto_reject(机器拦截), pending_review(待人工复核), manual_resolved(人工已处理)
    status = Column(String(50), default="pending_review")

    # 人工复核部分
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 处理此单的审核员ID
    manual_decision = Column(String(20), nullable=True)  # 人工最终判定: pass / reject
    review_reason = Column(String(255), nullable=True)  # 人工判定的备注理由

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# 表4：API 密钥表 (支撑【模块4：API 开放平台模块】)
class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String(100), unique=True, index=True, nullable=False)
    client_name = Column(String(100), nullable=False)  # 接入方名称，例如“某社交APP业务线”
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


# ==========================================
# 3. 数据库依赖注入 (供 FastAPI 路由使用)
# ==========================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()