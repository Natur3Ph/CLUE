"""
把主观/模糊的安全规则“客观化”。
核心流程：
1）rate_objectiveness(rule): 让 LLM 给规则打分（1–10）+ 解释。
2）improve_rule(rule, feedback): 让 LLM 按反馈重写规则，使之更客观、可判定。
3）objectify_rule(rule): 循环 1、2，直到分数 >= min_score 或达到 max_iters。
"""

import os
import re
from dataclasses import dataclass
from typing import List

from openai import OpenAI

# 从环境变量读取 OpenAI Key，避免写死在代码里
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("环境变量 OPENAI_API_KEY 未设置。请先设置后再运行该脚本。")

client = OpenAI(api_key=OPENAI_API_KEY)


# ----------------- 数据结构 -----------------

@dataclass
class RuleEvalResult:
    rule: str
    score: float
    explanation: str


@dataclass
class ObjectifiedRule:
    original_rule: str
    final_rule: str
    final_score: float
    history: List[RuleEvalResult]


# ----------------- 调用LLM工具函数 -----------------

def call_llm(messages, model: str = "gpt-4o-mini") -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


# ----------------- 1. 规则客观性打分 -----------------

OBJECTIVENESS_RATER_SYSTEM_PROMPT = """你是一个严格的内容安全规则评审专家。
你的任务是评价一条“图像安全规则”的客观性（objectiveness）。

客观性的含义：
- 规则应该尽量依赖“可观察的客观特征”，而不是“主观感受/模糊词语”。
- 例如：直接可观察的：身体部位是否暴露、是否有血、是否有武器、是否出现未成年人等。
- 不够客观的词：不雅、低俗、恶心、令人不适、引起不适当联想 等。

请输出 JSON，格式为：
{
  "score": <1-10的整数>,
  "explanation": "<简要说明为什么打这个分>"
}
"""

OBJECTIVENESS_RATER_USER_PROMPT_TEMPLATE = """请评价下面这条图像内容安全规则的“客观性”：

规则：{rule}

请只输出 JSON，不要多余文字。"""


def rate_objectiveness(rule: str) -> RuleEvalResult:
    """
    用 LLM 给规则打分，1-10。
    返回 score + explanation。
    """
    user_prompt = OBJECTIVENESS_RATER_USER_PROMPT_TEMPLATE.format(rule=rule)

    raw = call_llm(
        [
            {"role": "system", "content": OBJECTIVENESS_RATER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )

    # 简单解析 JSON
    score_match = re.search(r'"score"\s*:\s*(\d+)', raw)
    expl_match = re.search(r'"explanation"\s*:\s*"(.*)"', raw, re.S)

    if score_match:
        score = float(score_match.group(1))
    else:
        score = 5.0

    explanation = expl_match.group(1).strip() if expl_match else raw

    return RuleEvalResult(rule=rule, score=score, explanation=explanation)


# ----------------- 2. 根据反馈改写规则（客观化） -----------------

RULE_IMPROVER_SYSTEM_PROMPT = """你是一个内容安全规则工程师，擅长把“模糊、主观”的规则，
改写成“客观、可判定、适合给模型使用”的图像安全规则。

改写要求：
1. 尽量用“可观察的客观条件”来描述，而不是主观词汇。
   ✅例：图像中出现人的外生殖器、乳头、乳晕可见
   ❌例：不得出现不雅画面、不得引起性联想
2. 如果规则涉及“性”、“暴力”、“血腥”、“儿童”等概念，请拆成更具体的情况说明。
3. 可以引入阈值或条件，比如：
   - “角度大于90度”、“乳晕完全暴露”、“可见明显血液”、“身体局部缺失/断裂”等。
4. 不要引入与原规则无关的新内容。
5. 最终输出要是一条单独的规则文本（可以是1-3句话），不要输出解释。
"""

RULE_IMPROVER_USER_PROMPT_TEMPLATE = """下面是一条原始安全规则，以及对它的客观性评价。

原始规则：
{rule}

客观性评分：{score}/10
模型对缺点的说明：
{explanation}

请你在不改变安全意图的前提下，重新改写这条规则，使它：
- 更具体
- 尽量只依赖可观察的客观特征
- 避免使用“低俗、不雅、令人不适”等主观词

只输出改写后的那条规则本身，不要解释。"""


def improve_rule(rule: str, feedback: RuleEvalResult) -> str:
    user_prompt = RULE_IMPROVER_USER_PROMPT_TEMPLATE.format(
        rule=rule,
        score=int(feedback.score),
        explanation=feedback.explanation,
    )

    new_rule = call_llm(
        [
            {"role": "system", "content": RULE_IMPROVER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )
    return new_rule.strip()


# ----------------- 3. 主流程：迭代优化规则 -----------------

def objectify_rule(rule: str, min_score: float = 9.0, max_iters: int = 5) -> ObjectifiedRule:
    history: List[RuleEvalResult] = []

    current_rule = rule
    for _ in range(max_iters):
        eval_result = rate_objectiveness(current_rule)
        history.append(eval_result)

        if eval_result.score >= min_score:
            return ObjectifiedRule(
                original_rule=rule,
                final_rule=current_rule,
                final_score=eval_result.score,
                history=history,
            )

        current_rule = improve_rule(current_rule, eval_result)

    last_eval = history[-1]
    return ObjectifiedRule(
        original_rule=rule,
        final_rule=current_rule,
        final_score=last_eval.score,
        history=history,
    )


# ----------------- Demo -----------------

if __name__ == "__main__":
    raw_rules = [
        "图像不得包含暴力内容。",
        "禁止出现不雅、低俗的性暗示画面。",
        "不得展示让人感到恶心的血腥内容。",
        "不得出现未成年人不适当的场景。",
    ]

    for r in raw_rules:
        print("=" * 80)
        print("原始规则：", r)
        result = objectify_rule(r, min_score=9.0, max_iters=4)
        print(f"最终客观化规则（score={result.final_score:.1f}）：")
        print(result.final_rule)
        print("\n迭代过程记录：")
        for step, ev in enumerate(result.history, 1):
            print(f"  第 {step} 次评估：score={ev.score}, rule={ev.rule}")