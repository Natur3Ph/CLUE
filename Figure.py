from graphviz import Digraph

# 改 format="pdf" 或 "svg" 可导出更适合论文的格式
dot = Digraph("figure_3_4_er_optimized", format="png")
dot.attr(rankdir="TB", splines="ortho", nodesep="0.45", ranksep="0.65", dpi="300")
dot.attr(fontname="Microsoft YaHei")
dot.attr(bgcolor="white")

# 全局边样式
dot.attr(
    "edge",
    color="#666666",
    penwidth="1.1",
    arrowsize="0.75",
    fontname="Microsoft YaHei",
    fontsize="10"
)

# ========== 不同类别节点样式 ==========
audit_style = {
    "shape": "record",
    "style": "rounded,filled",
    "fontname": "Microsoft YaHei",
    "fontsize": "11",
    "color": "#4F81BD",
    "penwidth": "1.2",
    "fillcolor": "#EAF2FF",
}

dataset_style = {
    "shape": "record",
    "style": "rounded,filled",
    "fontname": "Microsoft YaHei",
    "fontsize": "11",
    "color": "#70AD47",
    "penwidth": "1.2",
    "fillcolor": "#EDF7E8",
}

config_style = {
    "shape": "record",
    "style": "rounded,filled",
    "fontname": "Microsoft YaHei",
    "fontsize": "11",
    "color": "#C55A11",
    "penwidth": "1.2",
    "fillcolor": "#FFF1E8",
}

# ========== 节点 ==========
# 审核业务相关
dot.node(
    "users",
    "{用户表 users|"
    "id : Integer (PK)\\l"
    "username : String\\l"
    "hashed_password : String\\l"
    "role : String\\l"
    "is_active : Boolean\\l"
    "created_at : DateTime\\l}",
    **audit_style
)

dot.node(
    "safety_rules",
    "{安全规则表 safety_rules|"
    "id : Integer (PK)\\l"
    "rule_name : String\\l"
    "original_rule : Text\\l"
    "objectified_rule : Text\\l"
    "preconditions : Text\\l"
    "objectiveness_score : Float\\l"
    "is_active : Boolean\\l"
    "version : Integer\\l"
    "created_at : DateTime\\l"
    "updated_at : DateTime\\l}",
    **audit_style
)

dot.node(
    "audit_tasks",
    "{审核任务表 audit_tasks|"
    "id : Integer (PK)\\l"
    "task_id : String\\l"
    "file_path : String\\l"
    "mllm_is_safe : Boolean\\l"
    "violated_details : Text\\l"
    "inference_time_ms : Integer\\l"
    "status : String\\l"
    "reviewer_id : Integer (FK)\\l"
    "manual_decision : String\\l"
    "review_reason : String\\l"
    "created_at : DateTime\\l"
    "updated_at : DateTime\\l}",
    **audit_style
)

# 配置相关
dot.node(
    "api_keys",
    "{接口密钥表 api_keys|"
    "id : Integer (PK)\\l"
    "api_key : String\\l"
    "client_name : String\\l"
    "is_active : Boolean\\l"
    "created_at : DateTime\\l}",
    **config_style
)

# 数据集与 Benchmark 相关
dot.node(
    "datasets",
    "{数据集表 datasets|"
    "id : Integer (PK)\\l"
    "dataset_name : String\\l"
    "description : Text\\l"
    "total_count : Integer\\l"
    "created_at : DateTime\\l"
    "updated_at : DateTime\\l}",
    **dataset_style
)

dot.node(
    "dataset_items",
    "{数据集图像表 dataset_items|"
    "id : Integer (PK)\\l"
    "dataset_id : Integer (FK)\\l"
    "file_path : String\\l"
    "filename : String\\l"
    "ground_truth_is_safe : Boolean\\l"
    "ground_truth_rule : String\\l"
    "split_type : String\\l"
    "created_at : DateTime\\l}",
    **dataset_style
)

dot.node(
    "benchmark_runs",
    "{Benchmark测试表 benchmark_runs|"
    "id : Integer (PK)\\l"
    "run_name : String\\l"
    "dataset_id : Integer (FK)\\l"
    "provider : String\\l"
    "total_count : Integer\\l"
    "tp / tn / fp / fn : Integer\\l"
    "accuracy : Float\\l"
    "precision : Float\\l"
    "recall : Float\\l"
    "f1_score : Float\\l"
    "avg_inference_time_ms : Float\\l"
    "created_at : DateTime\\l}",
    **dataset_style
)

dot.node(
    "benchmark_run_items",
    "{Benchmark结果表 benchmark_run_items|"
    "id : Integer (PK)\\l"
    "run_id : Integer (FK)\\l"
    "dataset_item_id : Integer (FK)\\l"
    "predicted_is_safe : Boolean\\l"
    "predicted_rules : Text\\l"
    "hit : Boolean\\l"
    "inference_time_ms : Integer\\l"
    "raw_explanation : Text\\l"
    "created_at : DateTime\\l}",
    **dataset_style
)

# ========== 关系 ==========
# 审核业务
dot.edge("users", "audit_tasks", label="1 : N", arrowhead="normal")

# 数据集与测试
dot.edge("datasets", "dataset_items", label="1 : N", arrowhead="normal")
dot.edge("datasets", "benchmark_runs", label="1 : N", arrowhead="normal")
dot.edge("benchmark_runs", "benchmark_run_items", label="1 : N", arrowhead="normal")
dot.edge("dataset_items", "benchmark_run_items", label="1 : N", arrowhead="normal")

# ========== 对齐布局 ==========
# 第一层
with dot.subgraph() as s:
    s.attr(rank="same")
    s.node("users")
    s.node("safety_rules")
    s.node("api_keys")

# 第二层
with dot.subgraph() as s:
    s.attr(rank="same")
    s.node("audit_tasks")
    s.node("datasets")

# 第三层
with dot.subgraph() as s:
    s.attr(rank="same")
    s.node("dataset_items")
    s.node("benchmark_runs")

# 第四层
with dot.subgraph() as s:
    s.attr(rank="same")
    s.node("benchmark_run_items")

# 输出
dot.render("figure_3_4_er_optimized", cleanup=True)
print("已生成：figure_3_4_er_optimized.png")