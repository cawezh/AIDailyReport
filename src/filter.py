"""关键词预筛选 — 对抓取结果进行快速关键词匹配"""
import re


def pre_filter(items: list[dict], keywords_map: dict[str, list[str]]) -> list[dict]:
    """
    遍历 items，匹配关键词，返回带 category 和 matched_keywords 的结果。
    一个 item 可以匹配多个 category。
    keywords_map: {"ai": ["llm", "agent", ...], "game": ["godot", ...], ...}
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
