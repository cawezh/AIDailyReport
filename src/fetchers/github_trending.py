"""GitHub Trending 页面解析"""
import requests
from bs4 import BeautifulSoup


def fetch_github_trending(since: str = "daily", max_items: int = 25) -> list[dict]:
    """
    抓取 GitHub Trending 页面。
    since: "daily" | "weekly" | "monthly"
    返回: [{"title": "...", "url": "...", "description": "...", "stars": 0, "language": "...", "source": "github_trending"}, ...]
    """
    url = f"https://github.com/trending?since={since}"
    headers = {"Accept": "text/html"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    repos = []

    for article in soup.find_all("article", class_="Box-row")[:max_items]:
        h2 = article.find("h2", class_="h3")
        if not h2:
            continue
        link = h2.find("a")
        if not link:
            continue
        # 清理空白字符
        path = link.get("href", "").strip()
        title = path.strip("/")

        desc_el = article.find("p", class_="col-9")
        description = desc_el.text.strip() if desc_el else ""

        # 语言
        lang_el = article.find("span", itemprop="programmingLanguage")
        language = lang_el.text.strip() if lang_el else ""

        # Stars
        stars_el = article.find("span", class_="d-inline-block float-sm-right")
        stars_text = stars_el.text.strip() if stars_el else "0"
        stars = _parse_star_count(stars_text)

        repos.append({
            "title": title,
            "url": f"https://github.com/{title}",
            "description": description,
            "stars": stars,
            "language": language,
            "source": "github_trending",
        })

    return repos


def _parse_star_count(text: str) -> int:
    """解析 '1,234 stars today' 格式为 int"""
    import re
    nums = re.findall(r"[\d,]+", text)
    if nums:
        return int(nums[0].replace(",", ""))
    return 0
