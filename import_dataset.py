import os
import requests
from collections import defaultdict

BASE_URL = "http://127.0.0.1:8000"
DATASET_ID = 6
ROOT_DIR = "test_images"
SPLIT_TYPE = "test"

# 文件夹名 -> (ground_truth_is_safe, ground_truth_rule)
CATEGORY_RULE = {
    "safe": (True, ""),
    "blood": (False, "暴力血腥"),
    "violence": (False, "暴力血腥"),
    "weapon": (False, "违禁品"),
    "drugs": (False, "违禁品"),
    "religion": (False, "敏感内容"),
}

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}

stats = defaultdict(int)
failed_files = []


def is_image_file(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def upload_one_file(file_path: str, category: str, is_safe: bool, rule: str) -> bool:
    filename = os.path.basename(file_path)

    with open(file_path, "rb") as f:
        files = {
            "files": (filename, f, "application/octet-stream")
        }
        data = {
            "ground_truth_is_safe": str(is_safe).lower(),
            "ground_truth_rule": rule,
            "split_type": SPLIT_TYPE,
        }

        try:
            resp = requests.post(
                f"{BASE_URL}/api/datasets/{DATASET_ID}/items/upload",
                files=files,
                data=data,
                timeout=120,
            )
        except Exception as e:
            print(f"[FAIL] {category:<10} {filename} -> 请求异常: {e}")
            failed_files.append({
                "category": category,
                "filename": filename,
                "status_code": "REQUEST_ERROR",
                "response": str(e),
            })
            return False

    if resp.status_code == 200:
        print(f"[OK]   {category:<10} {filename}")
        return True
    else:
        print(f"[FAIL] {category:<10} {filename} -> {resp.status_code} {resp.text}")
        failed_files.append({
            "category": category,
            "filename": filename,
            "status_code": resp.status_code,
            "response": resp.text,
        })
        return False


def main():
    if not os.path.exists(ROOT_DIR):
        print(f"目录不存在：{ROOT_DIR}")
        return

    total_files = 0
    uploaded_ok = 0
    skipped_non_image = 0
    skipped_unmapped_dir = 0

    print("=" * 80)
    print("开始导入测试集")
    print(f"BASE_URL    : {BASE_URL}")
    print(f"DATASET_ID  : {DATASET_ID}")
    print(f"ROOT_DIR    : {ROOT_DIR}")
    print(f"SPLIT_TYPE  : {SPLIT_TYPE}")
    print("=" * 80)

    for category in sorted(os.listdir(ROOT_DIR)):
        folder = os.path.join(ROOT_DIR, category)

        if not os.path.isdir(folder):
            continue

        if category not in CATEGORY_RULE:
            print(f"[SKIP] 未配置类别映射，跳过文件夹：{category}")
            skipped_unmapped_dir += 1
            continue

        is_safe, rule = CATEGORY_RULE[category]
        category_total = 0
        category_success = 0

        print(f"\n>>> 处理类别：{category} | is_safe={is_safe} | rule={rule if rule else '无'}")

        for filename in sorted(os.listdir(folder)):
            file_path = os.path.join(folder, filename)

            if not os.path.isfile(file_path):
                continue

            if not is_image_file(filename):
                print(f"[SKIP] 非图片文件：{filename}")
                skipped_non_image += 1
                continue

            total_files += 1
            category_total += 1

            ok = upload_one_file(
                file_path=file_path,
                category=category,
                is_safe=is_safe,
                rule=rule,
            )

            if ok:
                uploaded_ok += 1
                category_success += 1
                stats[category] += 1

        print(f"--- 类别完成：{category}，成功 {category_success}/{category_total}")

    print("\n" + "=" * 80)
    print("导入完成")
    print("=" * 80)
    print(f"总图片数            : {total_files}")
    print(f"成功上传数          : {uploaded_ok}")
    print(f"失败上传数          : {len(failed_files)}")
    print(f"跳过非图片文件数    : {skipped_non_image}")
    print(f"跳过未映射文件夹数  : {skipped_unmapped_dir}")
    print("-" * 80)
    print("分类统计：")

    total_safe = 0
    total_unsafe = 0

    for category in sorted(CATEGORY_RULE.keys()):
        count = stats.get(category, 0)
        print(f"  {category:<10} : {count}")

        is_safe, _ = CATEGORY_RULE[category]
        if is_safe:
            total_safe += count
        else:
            total_unsafe += count

    print("-" * 80)
    print(f"  {'safe':<10} : {total_safe}")
    print(f"  {'unsafe':<10} : {total_unsafe}")
    print(f"  {'total':<10} : {total_safe + total_unsafe}")

    if failed_files:
        print("\n失败文件列表：")
        for item in failed_files:
            print(f"  - [{item['category']}] {item['filename']} -> {item['status_code']}")
    else:
        print("\n全部上传成功。")

    print("=" * 80)


if __name__ == "__main__":
    main()