from models import engine, Base

def create_tables():
    print("正在连接 MySQL 数据库...")
    # 这一行会自动检测 models.py 里的所有类，并在数据库中建表
    Base.metadata.create_all(bind=engine)
    print("✅ 恭喜！数据库表结构初始化成功！请前往 HeidiSQL 刷新查看。")

if __name__ == "__main__":
    create_tables()