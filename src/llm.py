"""DeepSeek API — 精筛、分类、中文摘要、打分"""
import json
import requests
from src.config import get_env

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"


def summarize(items: list[dict], batch_size: int = 10) -> list[dict]:
    """
    批量调用 DeepSeek 对抓取结果进行分类、打分、中文摘要。
    返回增强后的 items，增加: cn_summary, relevance_score, creativity_score, is_highlight
    """
    api_key = get_env("DEEPSEEK_API_KEY")
    if not api_key:
        # 无 API Key 时降级为原始输出
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
[{{"id": <原id>, "cn_summary": "<30字中文摘要>", "relevance_score": 1-10, "creativity_score": 1-10, "is_highlight": true/false, "category": "<ai|game|android|internet>"}}]

评分标准：
- relevance_score: 技术价值 + 热度 + 实用性
- creativity_score: 创意新颖度（游戏项目重点看这个，全新玩法/机制得高分）
- is_highlight: 属于"开源游戏创新创意"或"多智能体协同办公"领域时标记 true
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
        item["creativity_score"] = s.get("creativity_score", 5)
        item["is_highlight"] = s.get("is_highlight", False)
        if s.get("category"):
            item["primary_category"] = s["category"]

    return items


def _fallback_summary(items: list[dict]) -> list[dict]:
    """无 API Key 时的降级处理"""
    for item in items:
        item["cn_summary"] = item.get("description", "")[:30] or item["title"]
        item["relevance_score"] = 5
        item["creativity_score"] = 5
        item["is_highlight"] = False
        item["primary_category"] = (item.get("categories") or ["internet"])[0]
    return items
