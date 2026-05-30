"""关键词预筛选 — 对抓取结果进行快速关键词匹配"""
import re

# 信任的数据源：这些源已自带内容过滤，所有项目直接放行
TRUSTED_SOURCES = {"producthunt", "arxiv", "steam"}


def pre_filter(items: list[dict], keywords_map: dict[str, list[str]]) -> list[dict]:
    """
    遍历 items，匹配关键词，返回带 category 和 matched_keywords 的结果。
    一个 item 可以匹配多个 category。
    keywords_map: {"ai": ["llm", "agent", ...], "game": ["godot", ...], ...}

    信任源（producthunt、arxiv）自动放行，无需关键词匹配。
    """
    # 编译关键词正则（忽略大小写）
    compiled = {}
    for cat, words in keywords_map.items():
        pattern = re.compile(
            r"\b(" + "|".join(re.escape(w) for w in words) + r")\b",
            re.IGNORECASE
        )
        compiled[cat] = pattern

    filtered = []

    for item in items:
        source = item.get("source", "")

        # 信任源直接放行，分类为 ai
        if source in TRUSTED_SOURCES:
            item.setdefault("categories", ["ai"])
            item.setdefault("matched_keywords", [f"source:{source}"])
            filtered.append(item)
            continue

        text = f"{item['title']} {item['description']} {item.get('language', '')}"
        matched_categories = []
        matched_keywords = []

        for cat, pattern in compiled.items():
            found = pattern.findall(text)
            if found:
                matched_categories.append(cat)
                matched_keywords.extend(found)

        if matched_categories:
            item["categories"] = list(set(matched_categories))
            item["matched_keywords"] = list(set(k.lower() for k in matched_keywords))
            filtered.append(item)

    return filtered
