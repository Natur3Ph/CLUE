from backend.models import Base, engine


def create_tables():
    print("正在连接 MySQL 数据库...")

    # 自动检测 models.py 中的所有 ORM 模型并创建表
    Base.metadata.create_all(bind=engine)

    print("✅ 恭喜！数据库表结构初始化成功！请前往 HeidiSQL 刷新查看。")


if __name__ == "__main__":
    create_tables()