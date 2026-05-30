"""arXiv — 通过 arXiv API 搜索最新论文"""
import xml.etree.ElementTree as ET
import requests

ARXIV_API_URL = "https://export.arxiv.org/api/query"

# 感兴趣的分类
CATEGORIES = [
    "cs.AI", "cs.LG", "cs.CL", "cs.CV",
    "cs.SE", "cs.IR", "cs.MA", "cs.RO",
    "cs.DC", "cs.NE",
]

# 搜索关键词（匹配标题+摘要）
SEARCH_TERMS = [
    "large language model", "LLM", "agent framework", "multi-agent",
    "RAG", "retrieval augmented", "fine-tuning", "instruction tuning",
    "vision language", "multimodal", "diffusion model",
    "code generation", "neural network", "deep learning",
    "reinforcement learning", "RLHF", "prompt engineering",
    "chain-of-thought", "reasoning model", "tool use",
    "edge computing", "distributed system", "compiler",
    "game AI", "procedural generation", "neural rendering",
]


def fetch_arxiv(max_items: int = 20) -> list[dict]:
    """
    通过 arXiv API 搜索最近论文，按关键词匹配标题和摘要。

    返回: [{"title": "...", "url": "...", "description": "...", "source": "arxiv"}, ...]
    """
    # arXiv API 最多一次返回 100 条
    query_parts = []
    for cat in CATEGORIES[:5]:  # 分类太多会超时，取前5个
        query_parts.append(f"cat:{cat}")

    query = "+OR+".join(query_parts)
    # 按更新时间排序，取最新论文
    url = f"{ARXIV_API_URL}?search_query={query}&sortBy=submittedDate&sortOrder=descending&max_results={max_items}"

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[arxiv] API request failed: {e}")
        return []

    # 解析 Atom XML
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(resp.content)

    results = []
    for entry in root.findall("atom:entry", ns):
        title = _clean_text(entry.find("atom:title", ns))
        summary = _clean_text(entry.find("atom:summary", ns))
        entry_id = _clean_text(entry.find("atom:id", ns))

        # 检查是否匹配关键词
        text_to_match = (title + " " + summary).lower()
        matched = any(term.lower() in text_to_match for term in SEARCH_TERMS)
        if not matched:
            continue

        # 提取 arxiv ID 作为稳定的 url
        # id 格式: http://arxiv.org/abs/1234.56789v1
        arxiv_id = entry_id.split("/abs/")[-1].split("v")[0] if "/abs/" in entry_id else entry_id
        arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"

        # 提取分类
        categories = []
        for cat_elem in entry.findall("atom:category", ns):
            term = cat_elem.get("term", "")
            if term.startswith("cs."):
                categories.append(term)

        results.append({
            "title": title.strip(),
            "url": arxiv_url,
            "description": summary.strip()[:500],
            "source": "arxiv",
            "categories": categories,
        })

    print(f"[arxiv] Fetched {len(results)} papers (from {max_items} queried)")
    return results


def _clean_text(elem) -> str:
    """提取元素文本并清理多余空白"""
    if elem is None or elem.text is None:
        return ""
    import re
    return re.sub(r"\s+", " ", elem.text.strip())
