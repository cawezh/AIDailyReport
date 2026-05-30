"""DeepSeek API — 精筛、分类、中文摘要、打分、整体概览"""
import json
import requests
from src.config import get_env

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"


def summarize(items: list[dict], batch_size: int = 10) -> list[dict]:
    """
    批量调用 DeepSeek 对抓取结果进行分类、打分、中文摘要。
    返回增强后的 items，增加: cn_summary, relevance_score, innovation_score, value_score, is_highlight, is_novel
    """
    api_key = get_env("DEEPSEEK_API_KEY")
    if not api_key:
        return _fallback_summary(items)

    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        try:
            batch_results = _summarize_batch(batch, api_key)
            results.extend(batch_results)
        except Exception:
            results.extend(_fallback_summary(batch))

    return results


def _summarize_batch(items: list[dict], api_key: str) -> list[dict]:
    items_json = json.dumps([
        {
            "id": idx,
            "title": item["title"],
            "description": item.get("description", "")[:300],
            "source": item.get("source", ""),
            "stars": item.get("stars", 0) or item.get("points", 0) or item.get("score", 0),
            "language": item.get("language", ""),
            "categories": item.get("categories", []),
        }
        for idx, item in enumerate(items)
    ], ensure_ascii=False)

    prompt = f"""你是技术日报编辑。分析以下项目列表，用中文给出摘要和评分。

返回 JSON 数组（只返回 JSON，不要任何其他文本）：
[{{"id": <原id>, "cn_summary": "<30字中文摘要>", "relevance_score": 1-10, "innovation_score": 1-10, "value_score": 1-10, "is_highlight": true/false, "is_novel": true/false, "category": "<ai|game|android|internet>"}}]

评分标准：
- relevance_score: 技术价值 + 热度 + 实用性
- innovation_score: 创新新颖度，按类型各有侧重：
  * 论文：方法论/思路的原创性
  * 游戏：玩法机制/交互方式的新意
  * 产品：产品概念/商业模式的独特性
  * 工具/框架：技术方案/架构的新颖程度
- value_score: 实用落地价值，按类型各有侧重：
  * 论文：学术影响力/引用潜力
  * 游戏：可玩性/完成度/社区关注
  * 产品：解决实际问题的程度/市场潜力
  * 工具/框架：对开发效率的提升/生态价值
- is_highlight: 属于"开源游戏创新创意"或"多智能体协同办公"领域时标记 true
- is_novel: 是否属于"潜力股/新兴项目"。如果该项目已经非常知名（如 LangChain、AutoGPT、Flutter、Godot Engine 等成熟项目），则标记 false。如果是新兴的、少见的、有潜力的项目，则标记 true。目的是帮读者发现值得关注的新技术。
- category: 选择最匹配的一个分类

项目列表：
{items_json}"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 4000,
    }
    resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]

    # 解析 JSON 响应
    scores = json.loads(content)
    score_map = {s["id"]: s for s in scores}

    for idx, item in enumerate(items):
        s = score_map.get(idx, {})
        item["cn_summary"] = s.get("cn_summary", item.get("description", "")[:30])
        item["relevance_score"] = s.get("relevance_score", 5)
        item["innovation_score"] = s.get("innovation_score", 5)
        item["value_score"] = s.get("value_score", 5)
        item["is_highlight"] = s.get("is_highlight", False)
        item["is_novel"] = s.get("is_novel", False)
        if s.get("category"):
            item["primary_category"] = s["category"]

    return items


def generate_overview(items: list[dict]) -> dict:
    """
    在所有 item 摘要完成后，再调用一次 DeepSeek，生成 2-3 句"今日技术趋势概述"。

    返回: {"overview": "...", "hot_trends": ["...", "..."]}
    """
    api_key = get_env("DEEPSEEK_API_KEY")
    if not api_key or not items:
        return {"overview": "", "hot_trends": []}

    # 取 top 20 个项目作为概览素材
    top_items = sorted(items, key=lambda x: x.get("relevance_score", 0), reverse=True)[:20]
    items_json = json.dumps([
        {
            "title": it["title"],
            "cn_summary": it.get("cn_summary", ""),
            "source": it.get("source", ""),
            "is_novel": it.get("is_novel", False),
        }
        for it in top_items
    ], ensure_ascii=False)

    prompt = f"""你是技术日报主编。基于今天收录的以下项目，生成一份简短的"今日技术趋势概述"。

返回 JSON（只返回 JSON，不要任何其他文本）：
{{"overview": "<2-3句话的中文概述，总结今天的技术热点和趋势>", "hot_trends": ["<趋势1>", "<趋势2>", "<趋势3>"]}}

今日项目：
{items_json}"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 1000,
    }

    try:
        resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
        print(f"[llm] Overview generated: {result.get('overview', '')[:60]}...")
        return result
    except Exception as e:
        print(f"[llm] Overview generation failed: {e}")
        return {"overview": "", "hot_trends": []}


def _fallback_summary(items: list[dict]) -> list[dict]:
    """无 API Key 时的降级处理"""
    for item in items:
        item["cn_summary"] = item.get("description", "")[:30] or item["title"]
        item["relevance_score"] = 5
        item["innovation_score"] = 5
        item["value_score"] = 5
        item["is_highlight"] = False
        item["is_novel"] = False
        item["primary_category"] = (item.get("categories") or ["internet"])[0]
    return items
