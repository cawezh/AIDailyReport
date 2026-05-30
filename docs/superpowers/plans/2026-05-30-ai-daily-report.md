# AI 技术日报系统 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 GitHub Actions 驱动的每日技术日报系统，抓取 10+ 数据源，通过 DeepSeek v4 智能筛选总结 AI/游戏(GODOT)/Android/互联网内容，输出 Markdown 日报 + Web Dashboard + 飞书/公众号推送。

**Architecture:** Python 脚本流水线：并行抓取 → 关键词预筛 → DeepSeek 精筛 → 生成报告 + Dashboard + 推送。GitHub Actions 每日定时触发，产物 git commit 回仓库，GitHub Pages 托管前端。

**Tech Stack:** Python 3.11+, requests, BeautifulSoup4, Jinja2, PyYAML, DeepSeek API

---

## 文件结构总览

```
ai-daily-report/
├── .github/workflows/daily.yml          # GitHub Actions 定时触发
├── src/
│   ├── main.py                           # 入口，编排全流程
│   ├── config.py                         # 加载 YAML 配置 + 环境变量
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── github_trending.py            # GitHub Trending HTML 解析
│   │   ├── github_search.py             # GitHub Search API
│   │   ├── hackernews.py                # HN API
│   │   ├── reddit.py                    # Reddit API
│   │   ├── producthunt.py               # ProductHunt HTML 解析
│   │   ├── huggingface.py               # HF Trending HTML 解析
│   │   └── indie_games.py               # itch.io HTML 解析
│   ├── filter.py                         # 关键词预筛选
│   ├── llm.py                            # DeepSeek API 调用
│   ├── reporter.py                       # Markdown 报告生成
│   ├── dashboard.py                      # HTML Dashboard 生成
│   ├── feishu.py                         # 飞书 Webhook 推送
│   └── wechat.py                         # 微信公众号模板消息推送
├── config/
│   ├── keywords.yaml                     # 四类筛选关键词
│   └── sources.yaml                      # 数据源开关 + 抓取数量
├── templates/
│   ├── report.md.j2                      # Markdown 日报模板
│   ├── dashboard.html.j2                 # Dashboard HTML 模板
│   └── feishu_card.json.j2              # 飞书卡片消息模板
├── reports/                              # 生成的 .md 日报
├── docs/                                 # GitHub Pages 站点根目录
│   ├── index.html                        # 生成的 Dashboard
│   └── reports/                          # 历史报告 HTML 归档
├── requirements.txt
└── README.md
```

---

### Task 1: 项目脚手架 + 依赖配置

**Files:**
- Create: `requirements.txt`
- Create: `config/keywords.yaml`
- Create: `config/sources.yaml`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `src/fetchers/__init__.py`

- [ ] **Step 1: 创建 requirements.txt**

```python
requests>=2.31.0
beautifulsoup4>=4.12.0
pyyaml>=6.0
jinja2>=3.1.0
```

- [ ] **Step 2: 创建 config/keywords.yaml**

```yaml
# 关键词预筛规则 — 四类分类
categories:
  ai:
    - llm
    - agent
    - rag
    - multimodal
    - fine-tune
    - inference
    - transformer
    - embedding
    - vector-db
    - prompt-engineering
    - chain-of-thought
    - openai
    - claude
    - deepseek
    - ollama
    - langchain
    - llama-index
    - sora
    - stable-diffusion
    - diffusion
    - text-to-image
    - text-to-video
    - speech-to-text
    - tts

  game:
    - godot
    - godot-engine
    - godot-plugin
    - godot-game
    - gdscript
    - godot-shader
    - godot-tool
    - game-engine
    - open-source-game
    - indie-game
    - bevy
    - roguelike
    - sandbox
    - procedural-generation
    - game-ai
    - multiplayer
    - pixel-art
    - voxel
    - game-jam

  android:
    - android
    - jetpack-compose
    - kotlin
    - flutter
    - react-native
    - performance-optimization
    - reverse-engineering
    - android-security
    - gradle
    - kotlin-multiplatform

  internet:
    - distributed-system
    - protocol
    - devops
    - kubernetes
    - docker
    - rust
    - golang
    - database
    - streaming
    - edge-computing
    - webassembly
    - wasm
    - serverless
    - microservices
```

- [ ] **Step 3: 创建 config/sources.yaml**

```yaml
sources:
  github_trending:
    enabled: true
    max_items: 25
  github_search:
    enabled: true
    queries:
      - "godot"
      - "godot-engine"
      - "godot-plugin"
      - "godot-game"
      - "multi-agent"
      - "agent-framework"
      - "open-source-game"
      - "llm"
      - "rag"
      - "android"
      - "game-engine"
    per_query: 10
  hackernews:
    enabled: true
    max_items: 100
  reddit:
    enabled: true
    subreddits:
      - gamedev
      - MachineLearning
      - androiddev
      - programming
      - indiegames
      - godot
    per_subreddit: 25
  producthunt:
    enabled: true
    max_items: 30
  huggingface:
    enabled: true
    max_items: 20
  indie_games:
    enabled: true
    max_items: 20

llm:
  model: "deepseek-chat"
  max_tokens_per_batch: 4000
  temperature: 0.3

report:
  top_n: 10           # Top 10 总榜
  per_category: 8     # 每类最多显示数

output:
  reports_dir: "reports"
  docs_dir: "docs"
```

- [ ] **Step 4: 创建 src/config.py**

```python
import os
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"


def load_yaml(name: str) -> dict:
    path = CONFIG_DIR / f"{name}.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def get_keywords() -> dict[str, list[str]]:
    cfg = load_yaml("keywords")
    return cfg["categories"]


def get_sources() -> dict:
    return load_yaml("sources")


def get_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)
```

- [ ] **Step 5: 创建 src/fetchers/__init__.py**

```python
from .github_trending import fetch_github_trending
from .github_search import fetch_github_search
from .hackernews import fetch_hackernews
from .reddit import fetch_reddit
from .producthunt import fetch_producthunt
from .huggingface import fetch_huggingface
from .indie_games import fetch_indie_games
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: project scaffold with config and dependencies"
```

---

### Task 2: GitHub Trending 抓取器

**Files:**
- Create: `src/fetchers/github_trending.py`

- [ ] **Step 1: 实现抓取器**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add src/fetchers/github_trending.py
git commit -m "feat: add GitHub Trending fetcher"
```

---

### Task 3: GitHub Search API 抓取器

**Files:**
- Create: `src/fetchers/github_search.py`

- [ ] **Step 1: 实现抓取器**

```python
"""GitHub Search API"""
import requests
from datetime import datetime, timedelta

SEARCH_URL = "https://api.github.com/search/repositories"


def fetch_github_search(queries: list[str], per_query: int = 10) -> list[dict]:
    """
    对每个查询词搜索仓库，按 star 排序。
    返回: [{"title": "owner/repo", "url": "...", "description": "...", "stars": 0, "language": "...", "source": "github_search", "query": "..."}, ...]
    """
    headers = {"Accept": "application/vnd.github.v3+json"}
    results = []

    # 搜索最近 7 天更新的仓库
    since = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")

    for query in queries:
        params = {
            "q": f"{query} pushed:>={since}",
            "sort": "stars",
            "order": "desc",
            "per_page": per_query,
        }
        try:
            resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", []):
                results.append({
                    "title": item["full_name"],
                    "url": item["html_url"],
                    "description": item.get("description") or "",
                    "stars": item.get("stargazers_count", 0),
                    "language": item.get("language") or "",
                    "source": "github_search",
                    "query": query,
                    "topics": item.get("topics", []),
                    "updated_at": item.get("updated_at", ""),
                })
        except requests.RequestException:
            continue  # 单个查询失败不影响整体

    return _deduplicate(results)


def _deduplicate(items: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for item in items:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)
    return unique
```

- [ ] **Step 2: Commit**

```bash
git add src/fetchers/github_search.py
git commit -m "feat: add GitHub Search API fetcher"
```

---

### Task 4: Hacker News API 抓取器

**Files:**
- Create: `src/fetchers/hackernews.py`

- [ ] **Step 1: 实现抓取器**

```python
"""Hacker News API"""
import requests

TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"


def fetch_hackernews(max_items: int = 100) -> list[dict]:
    """
    获取 HN 首页前 N 条。
    返回: [{"title": "...", "url": "...", "description": "", "points": 0, "comments": 0, "source": "hackernews"}, ...]
    """
    headers = {"Accept": "application/json"}
    resp = requests.get(TOP_STORIES_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    story_ids = resp.json()[:max_items]

    results = []
    for sid in story_ids:
        try:
            r = requests.get(ITEM_URL.format(sid), headers=headers, timeout=10)
            r.raise_for_status()
            item = r.json()
            if item and item.get("type") == "story":
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url") or f"https://news.ycombinator.com/item?id={sid}",
                    "description": "",
                    "points": item.get("score", 0),
                    "comments": item.get("descendants", 0),
                    "source": "hackernews",
                })
        except requests.RequestException:
            continue

    return results
```

- [ ] **Step 2: Commit**

```bash
git add src/fetchers/hackernews.py
git commit -m "feat: add Hacker News fetcher"
```

---

### Task 5: Reddit API 抓取器

**Files:**
- Create: `src/fetchers/reddit.py`

- [ ] **Step 1: 实现抓取器**

```python
"""Reddit API — 无需认证即可读取 .json 端点"""
import requests


def fetch_reddit(subreddits: list[str], per_subreddit: int = 25) -> list[dict]:
    """
    获取指定 subreddit 的热门帖子。
    返回: [{"title": "...", "url": "...", "description": "...", "score": 0, "comments": 0, "source": "reddit", "subreddit": "..."}, ...]
    """
    headers = {"User-Agent": "ai-daily-report-bot/1.0"}
    results = []

    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/hot.json"
        params = {"limit": per_subreddit}
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for child in data.get("data", {}).get("children", []):
                post = child["data"]
                if post.get("stickied"):
                    continue
                results.append({
                    "title": post.get("title", ""),
                    "url": post.get("url", ""),
                    "description": post.get("selftext", "")[:300],
                    "score": post.get("score", 0),
                    "comments": post.get("num_comments", 0),
                    "source": "reddit",
                    "subreddit": sub,
                })
        except requests.RequestException:
            continue

    return results
```

- [ ] **Step 2: Commit**

```bash
git add src/fetchers/reddit.py
git commit -m "feat: add Reddit fetcher"
```

---

### Task 6: ProductHunt + HuggingFace + 独立游戏抓取器

**Files:**
- Create: `src/fetchers/producthunt.py`
- Create: `src/fetchers/huggingface.py`
- Create: `src/fetchers/indie_games.py`

- [ ] **Step 1: 创建 ProductHunt 抓取器**

```python
"""ProductHunt Trending 页面解析"""
import requests
from bs4 import BeautifulSoup


def fetch_producthunt(max_items: int = 30) -> list[dict]:
    """
    抓取 ProductHunt 首页热门产品。
    返回: [{"title": "...", "url": "...", "description": "...", "votes": 0, "source": "producthunt"}, ...]
    """
    url = "https://www.producthunt.com/"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for item in soup.find_all("div", attrs={"data-test": "post-item"})[:max_items]:
        title_el = item.find("a", attrs={"data-test": "post-name"})
        desc_el = item.find("a", attrs={"data-test": "post-tagline"})
        vote_el = item.find("span", attrs={"data-test": "vote-button"})

        if not title_el:
            continue

        results.append({
            "title": title_el.text.strip(),
            "url": "https://www.producthunt.com" + (title_el.get("href") or ""),
            "description": desc_el.text.strip() if desc_el else "",
            "votes": _parse_votes(vote_el.text if vote_el else "0"),
            "source": "producthunt",
        })

    return results


def _parse_votes(text: str) -> int:
    import re
    nums = re.findall(r"\d+", text)
    return int(nums[0]) if nums else 0
```

- [ ] **Step 2: 创建 HuggingFace 抓取器**

```python
"""HuggingFace Models Trending"""
import requests
from bs4 import BeautifulSoup


def fetch_huggingface(max_items: int = 20) -> list[dict]:
    """
    抓取 HuggingFace Models Trending 页面。
    返回: [{"title": "...", "url": "...", "description": "...", "downloads": 0, "source": "huggingface"}, ...]
    """
    url = "https://huggingface.co/models?sort=trending"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for article in soup.find_all("article")[:max_items]:
        link = article.find("a")
        if not link:
            continue
        title = link.get("href", "").strip("/")
        desc_el = article.find("p")
        description = desc_el.text.strip()[:200] if desc_el else ""

        results.append({
            "title": title,
            "url": f"https://huggingface.co/{title}",
            "description": description,
            "downloads": 0,
            "source": "huggingface",
        })

    return results
```

- [ ] **Step 3: 创建独立游戏抓取器**

```python
"""itch.io 独立游戏 Trending"""
import requests
from bs4 import BeautifulSoup


def fetch_indie_games(max_items: int = 20) -> list[dict]:
    """
    抓取 itch.io 热门独立游戏。
    返回: [{"title": "...", "url": "...", "description": "...", "score": 0, "source": "itch.io"}, ...]
    """
    url = "https://itch.io/games/top-rated"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for cell in soup.find_all("div", class_="game_cell")[:max_items]:
        title_el = cell.find("a", class_="title")
        desc_el = cell.find("div", class_="game_text")
        if not title_el:
            continue

        results.append({
            "title": title_el.text.strip(),
            "url": title_el.get("href", ""),
            "description": desc_el.text.strip()[:200] if desc_el else "",
            "score": 0,
            "source": "itch.io",
        })

    return results
```

- [ ] **Step 4: Commit**

```bash
git add src/fetchers/producthunt.py src/fetchers/huggingface.py src/fetchers/indie_games.py
git commit -m "feat: add ProductHunt, HuggingFace, and indie games fetchers"
```

---

### Task 7: 关键词预筛选模块

**Files:**
- Create: `src/filter.py`

- [ ] **Step 1: 实现关键词预筛**

```python
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
    seen_urls = set()

    for item in items:
        if item["url"] in seen_urls:
            continue
        seen_urls.add(item["url"])

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
```

- [ ] **Step 2: Commit**

```bash
git add src/filter.py
git commit -m "feat: add keyword pre-filter module"
```

---

### Task 8: DeepSeek LLM 精筛 + 摘要模块

**Files:**
- Create: `src/llm.py`

- [ ] **Step 1: 实现 LLM 模块**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add src/llm.py
git commit -m "feat: add DeepSeek LLM summarization module"
```

---

### Task 9: Markdown 报告生成器

**Files:**
- Create: `templates/report.md.j2`
- Create: `src/reporter.py`

- [ ] **Step 1: 创建 Jinja2 模板**

```jinja2
# AI 技术日报 — {{ date }}

## 📊 今日概览

| 指标 | 数值 |
|------|------|
| 收录项目 | {{ total }} |
| AI 相关 | {{ counts.ai }} |
| 游戏相关 | {{ counts.game }} |
| Android 相关 | {{ counts.android }} |
| 互联网/基础设施 | {{ counts.internet }} |
| 重点关注 | {{ highlights|length }} 个（创新游戏/多智能体） |

---

## 🔥 今日 Top 10

| 排名 | 项目 | 来源 | 热度 | 摘要 |
|------|------|------|------|------|
{% for item in top10 %}
| {{ loop.index }} | [{{ item.title }}]({{ item.url }}) | {{ item.source }} | {{ item.stars }} | {{ item.cn_summary }} |
{% endfor %}

---

## 🤖 AI 相关

| 项目 | Stars | 摘要 |
|------|-------|------|
{% for item in ai_items %}
| [{{ item.title }}]({{ item.url }}) | {{ item.stars }} | {{ item.cn_summary }} |
{% endfor %}

---

## 🎮 游戏相关

### 🔧 GODOT 项目（重点关注）

| 项目 | Stars | 摘要 | 创意度 |
|------|-------|------|--------|
{% for item in godot_items %}
| [{{ item.title }}]({{ item.url }}) | {{ item.stars }} | {{ item.cn_summary }} | {{ item.creativity_score }}/10 |
{% else %}
> 今日暂无新的 GODOT 热门项目
{% endfor %}

### 开源游戏

{% for item in game_oss_items %}
- **[{{ item.title }}]({{ item.url }})** — {{ item.cn_summary }} (⭐ {{ item.stars }})
{% else %}
> 今日暂无新的开源游戏项目
{% endfor %}

### 💡 创意新游

{% for item in creative_games %}
- **[{{ item.title }}]({{ item.url }})** ({{ item.source }}) — {{ item.cn_summary }}
{% else %}
> 今日暂无新的创意游戏
{% endfor %}

---

## 📱 Android 相关

| 项目 | Stars | 摘要 |
|------|-------|------|
{% for item in android_items %}
| [{{ item.title }}]({{ item.url }}) | {{ item.stars }} | {{ item.cn_summary }} |
{% endfor %}

---

## 🌐 互联网 / 基础设施

| 项目 | Stars | 摘要 |
|------|-------|------|
{% for item in internet_items %}
| [{{ item.title }}]({{ item.url }}) | {{ item.stars }} | {{ item.cn_summary }} |
{% endfor %}

---

## 📌 多智能体协同（重点关注）

{% for item in multi_agent_items %}
- **[{{ item.title }}]({{ item.url }})** — {{ item.cn_summary }}
{% else %}
> 今日暂无新的多智能体协同项目
{% endfor %}

---

> 自动生成于 {{ date }} | 数据来源: GitHub, HN, Reddit, ProductHunt, HuggingFace, itch.io
```

- [ ] **Step 2: 创建报告生成器**

```python
"""Markdown 日报生成器"""
from datetime import date
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def generate_report(
    items: list[dict],
    output_dir: str = "reports",
) -> Path:
    """
    根据分类好的 items 生成 Markdown 日报。
    返回生成的文件路径。
    """
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("report.md.j2")

    today = date.today().isoformat()

    # 按 primary_category 分类
    ai_items = [it for it in items if it.get("primary_category") == "ai"]
    game_items = [it for it in items if it.get("primary_category") == "game"]
    android_items = [it for it in items if it.get("primary_category") == "android"]
    internet_items = [it for it in items if it.get("primary_category") == "internet"]

    # GODOT 专项
    godot_items = [it for it in game_items if "godot" in it.get("matched_keywords", []) or "godot" in it["title"].lower()]

    # 开源游戏
    game_oss_items = [it for it in game_items if it not in godot_items and "open-source" in it.get("description", "").lower() or "github" in it.get("url", "")]

    # 创意新游（itch.io 来源 + 高创意分）
    creative_games = [it for it in game_items if it.get("source") == "itch.io" or it.get("creativity_score", 0) >= 8]

    # 多智能体
    multi_agent_items = [it for it in items if it.get("is_highlight") and "agent" in it.get("matched_keywords", [])]

    # 高光项目
    highlights = [it for it in items if it.get("is_highlight")]

    # Top 10
    top10 = sorted(items, key=lambda x: (x.get("relevance_score", 0), x.get("stars", 0)), reverse=True)[:10]

    # 热度统一字段
    for it in items:
        it["stars"] = it.get("stars", 0) or it.get("points", 0) or it.get("score", 0)

    content = template.render(
        date=today,
        total=len(items),
        counts={
            "ai": len(ai_items),
            "game": len(game_items),
            "android": len(android_items),
            "internet": len(internet_items),
        },
        top10=top10,
        ai_items=ai_items[:8],
        godot_items=godot_items[:10],
        game_oss_items=game_oss_items[:5],
        creative_games=creative_games[:5],
        android_items=android_items[:8],
        internet_items=internet_items[:8],
        multi_agent_items=multi_agent_items[:5],
        highlights=highlights,
    )

    out_path = Path(output_dir) / f"{today}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")

    return out_path
```

- [ ] **Step 3: Commit**

```bash
git add templates/report.md.j2 src/reporter.py
git commit -m "feat: add Markdown report generator with Jinja2 template"
```

---

### Task 10: HTML Dashboard 生成器

**Files:**
- Create: `templates/dashboard.html.j2`
- Create: `src/dashboard.py`

- [ ] **Step 1: 创建 Dashboard 模板**

```jinja2
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 技术日报 — {{ date }}</title>
<style>
  :root { --bg: #0d1117; --card: #161b22; --border: #30363d; --text: #c9d1d9; --accent: #58a6ff; --green: #3fb950; --orange: #d2991d; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); padding: 20px; }
  header { text-align: center; padding: 40px 0 20px; }
  h1 { font-size: 1.8rem; color: var(--accent); }
  .date-picker { margin: 20px 0; display: flex; justify-content: center; gap: 10px; }
  .date-picker input { background: var(--card); border: 1px solid var(--border); color: var(--text); padding: 8px 16px; border-radius: 6px; font-size: 1rem; }
  .tabs { display: flex; gap: 8px; margin: 20px 0; flex-wrap: wrap; justify-content: center; }
  .tab { padding: 8px 20px; background: var(--card); border: 1px solid var(--border); border-radius: 20px; cursor: pointer; font-size: 0.9rem; }
  .tab.active { background: var(--accent); color: #fff; border-color: var(--accent); }
  .stats { display: flex; gap: 16px; flex-wrap: wrap; justify-content: center; margin: 20px 0; }
  .stat { background: var(--card); padding: 12px 24px; border-radius: 8px; text-align: center; min-width: 100px; }
  .stat .num { font-size: 1.5rem; font-weight: bold; color: var(--accent); }
  .stat .label { font-size: 0.8rem; color: #8b949e; }
  .highlight-section { background: linear-gradient(135deg, #1a2332, #1a1a2e); border: 1px solid var(--orange); border-radius: 12px; padding: 20px; margin: 20px 0; }
  .highlight-section h2 { color: var(--orange); }
  .section { margin: 20px 0; }
  .section h2 { font-size: 1.3rem; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
  .section h2 .emoji { margin-right: 8px; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin: 10px 0; }
  .card .title { font-size: 1rem; font-weight: 600; }
  .card .title a { color: var(--accent); text-decoration: none; }
  .card .meta { font-size: 0.8rem; color: #8b949e; margin-top: 4px; }
  .card .summary { margin-top: 8px; font-size: 0.9rem; line-height: 1.5; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; margin-left: 6px; }
  .badge-star { background: #1f3a23; color: var(--green); }
  .badge-creative { background: #3a2f1f; color: var(--orange); }
  .tab-content { display: none; }
  .tab-content.active { display: block; }
  footer { text-align: center; padding: 40px 0 20px; color: #8b949e; font-size: 0.8rem; }
  .search-box { display: flex; justify-content: center; margin: 16px 0; }
  .search-box input { background: var(--card); border: 1px solid var(--border); color: var(--text); padding: 8px 16px; border-radius: 6px; width: 100%; max-width: 400px; font-size: 1rem; }
  @media (max-width: 600px) { body { padding: 10px; } .stats { gap: 8px; } .stat { padding: 8px 12px; min-width: 70px; } }
</style>
</head>
<body>
<header>
  <h1>AI 技术日报</h1>
  <p style="color:#8b949e;margin-top:8px;">{{ date }}</p>
</header>

<div class="stats">
  <div class="stat"><div class="num">{{ total }}</div><div class="label">收录项目</div></div>
  <div class="stat"><div class="num">{{ counts.ai }}</div><div class="label">AI</div></div>
  <div class="stat"><div class="num">{{ counts.game }}</div><div class="label">游戏</div></div>
  <div class="stat"><div class="num">{{ counts.android }}</div><div class="label">Android</div></div>
  <div class="stat"><div class="num">{{ counts.internet }}</div><div class="label">互联网</div></div>
</div>

<div class="search-box">
  <input type="text" id="search" placeholder="搜索项目..." oninput="filterCards(this.value)">
</div>

<div class="tabs">
  <div class="tab active" onclick="switchTab('all')">全部</div>
  <div class="tab" onclick="switchTab('ai')">AI</div>
  <div class="tab" onclick="switchTab('game')">游戏</div>
  <div class="tab" onclick="switchTab('godot')">GODOT</div>
  <div class="tab" onclick="switchTab('android')">Android</div>
  <div class="tab" onclick="switchTab('internet')">互联网</div>
  <div class="tab" onclick="switchTab('highlight')">重点关注</div>
</div>

{% if highlights %}
<div class="highlight-section" id="tab-highlight">
  <h2>重点关注 — 创新游戏 & 多智能体协同</h2>
  {% for item in highlights %}
  <div class="card" data-category="highlight" data-keywords="{{ item.title }} {{ item.cn_summary }}">
    <div class="title"><a href="{{ item.url }}" target="_blank">{{ item.title }}</a><span class="badge badge-creative">创意 {{ item.creativity_score }}/10</span></div>
    <div class="meta">来源: {{ item.source }} | 热度: {{ item.stars }}</div>
    <div class="summary">{{ item.cn_summary }}</div>
  </div>
  {% endfor %}
</div>
{% endif %}

{% for cat in ['ai', 'game', 'android', 'internet'] %}
<div class="section tab-content {% if cat == 'ai' %}active{% endif %}" id="tab-{{ cat }}">
  <h2>{{ cat_labels[cat] }}</h2>
  {% for item in categorized[cat] %}
  <div class="card" data-category="{{ item.primary_category }}" data-keywords="{{ item.title }} {{ item.cn_summary }}">
    <div class="title"><a href="{{ item.url }}" target="_blank">{{ item.title }}</a>
      {% if item.stars %}<span class="badge badge-star">⭐ {{ item.stars }}</span>{% endif %}
    </div>
    <div class="meta">来源: {{ item.source }}{% if item.language %} | 语言: {{ item.language }}{% endif %}</div>
    <div class="summary">{{ item.cn_summary }}</div>
  </div>
  {% else %}
  <p style="color:#8b949e;">今日暂无收录</p>
  {% endfor %}
</div>
{% endfor %}

<footer>自动生成于 {{ date }} | 数据来源: GitHub, Hacker News, Reddit, ProductHunt, HuggingFace, itch.io</footer>

<script>
function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelector(`.tab:nth-child(${['all','ai','game','godot','android','internet','highlight'].indexOf(tab)+1})`).classList.add('active');
  if (tab === 'all') {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.add('active'));
  } else {
    document.getElementById('tab-' + tab).classList.add('active');
  }
}
function filterCards(query) {
  const q = query.toLowerCase();
  document.querySelectorAll('.card').forEach(card => {
    const kw = card.getAttribute('data-keywords').toLowerCase();
    card.style.display = kw.includes(q) ? '' : 'none';
  });
}
</script>
</body>
</html>
```

- [ ] **Step 2: 创建 Dashboard 生成器**

```python
"""HTML Dashboard 生成器"""
from datetime import date
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def generate_dashboard(
    items: list[dict],
    output_dir: str = "docs",
) -> Path:
    """生成 index.html Dashboard 页面"""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("dashboard.html.j2")

    today = date.today().isoformat()

    categorized = {"ai": [], "game": [], "android": [], "internet": []}
    for it in items:
        cat = it.get("primary_category", "internet")
        if cat in categorized:
            categorized[cat].append(it)

    # 热度统一
    for it in items:
        it["stars"] = it.get("stars", 0) or it.get("points", 0) or it.get("score", 0)

    highlights = [it for it in items if it.get("is_highlight")]

    counts = {cat: len(lst) for cat, lst in categorized.items()}

    content = template.render(
        date=today,
        total=len(items),
        counts=counts,
        categorized=categorized,
        highlights=highlights,
        cat_labels={"ai": "AI 相关", "game": "游戏相关", "android": "Android 相关", "internet": "互联网/基础设施"},
    )

    out_path = Path(output_dir) / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")

    return out_path
```

- [ ] **Step 3: Commit**

```bash
git add templates/dashboard.html.j2 src/dashboard.py
git commit -m "feat: add HTML Dashboard generator with tabbed interface"
```

---

### Task 11: 飞书 + 微信公众号推送模块

**Files:**
- Create: `src/feishu.py`
- Create: `src/wechat.py`

- [ ] **Step 1: 创建飞书推送模块**

```python
"""飞书 Webhook 卡片消息推送"""
import json
import requests
from src.config import get_env


def send_feishu(top5: list[dict], dashboard_url: str) -> bool:
    """
    通过飞书 Webhook 发送日报卡片消息。
    top5: 前 5 个项目，每个含 title, url, cn_summary
    """
    webhook_url = get_env("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        print("[feishu] FEISHU_WEBHOOK_URL not set, skipping")
        return False

    from datetime import date
    today = date.today().isoformat()

    elements = [
        {"tag": "div", "text": {"tag": "lark_md", "content": f"**AI 技术日报 — {today}**"}},
        {"tag": "hr"},
    ]

    for idx, item in enumerate(top5, 1):
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"{idx}. [{item['title']}]({item['url']}) — {item['cn_summary']}"
            }
        })

    elements.append({"tag": "hr"})
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": f"[查看完整日报]({dashboard_url})"}
    })

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"AI 技术日报 — {today}"},
                "template": "blue",
            },
            "elements": elements,
        },
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=15)
        resp.raise_for_status()
        print("[feishu] sent successfully")
        return True
    except requests.RequestException as e:
        print(f"[feishu] send failed: {e}")
        return False
```

- [ ] **Step 2: 创建公众号推送模块**

```python
"""微信公众号模板消息推送"""
import requests
from src.config import get_env

WECHAT_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
WECHAT_SEND_URL = "https://api.weixin.qq.com/cgi-bin/message/template/send"


def send_wechat(top5: list[dict], dashboard_url: str) -> bool:
    """
    通过公众号模板消息推送日报。
    top5: 取前 5 个项目生成摘要文本
    """
    appid = get_env("WECHAT_APPID")
    secret = get_env("WECHAT_APPSECRET")
    template_id = get_env("WECHAT_TEMPLATE_ID")

    if not all([appid, secret, template_id]):
        print("[wechat] credentials not fully set, skipping")
        return False

    # 1. 获取 access_token
    try:
        resp = requests.get(WECHAT_TOKEN_URL, params={
            "grant_type": "client_credential",
            "appid": appid,
            "secret": secret,
        }, timeout=15)
        resp.raise_for_status()
        access_token = resp.json().get("access_token")
        if not access_token:
            print(f"[wechat] get token failed: {resp.text}")
            return False
    except requests.RequestException as e:
        print(f"[wechat] get token error: {e}")
        return False

    # 2. 获取粉丝列表（发送给所有关注者）
    sent = 0
    try:
        next_openid = ""
        while True:
            user_resp = requests.get(
                "https://api.weixin.qq.com/cgi-bin/user/get",
                params={
                    "access_token": access_token,
                    "next_openid": next_openid,
                },
                timeout=15,
            )
            user_resp.raise_for_status()
            user_data = user_resp.json()
            openids = user_data.get("data", {}).get("openid", [])

            for openid in openids:
                summary = "\n".join(
                    f"{i+1}. {item['title']} — {item['cn_summary'][:30]}"
                    for i, item in enumerate(top5)
                )
                payload = {
                    "touser": openid,
                    "template_id": template_id,
                    "url": dashboard_url,
                    "data": {
                        "first": {"value": "AI 技术日报已更新", "color": "#173177"},
                        "keyword1": {"value": str(len(top5)), "color": "#173177"},
                        "keyword2": {"value": summary, "color": "#173177"},
                        "remark": {"value": "点击查看完整日报", "color": "#173177"},
                    },
                }
                r = requests.post(
                    WECHAT_SEND_URL,
                    params={"access_token": access_token},
                    json=payload,
                    timeout=10,
                )
                if r.json().get("errmsg") == "ok":
                    sent += 1

            total = user_data.get("total", 0)
            count = user_data.get("count", 0)
            if count < 10000:
                break
            next_openid = user_data.get("next_openid", "")

        print(f"[wechat] sent to {sent} users")
        return sent > 0
    except requests.RequestException as e:
        print(f"[wechat] send error: {e}")
        return False
```

- [ ] **Step 3: Commit**

```bash
git add src/feishu.py src/wechat.py
git commit -m "feat: add Feishu webhook and WeChat Official Account push modules"
```

---

### Task 12: 主流程编排 + GitHub Actions 工作流

**Files:**
- Create: `src/main.py`
- Create: `.github/workflows/daily.yml`

- [ ] **Step 1: 创建主入口**

```python
"""主流程 — 编排全部步骤"""
import sys
from datetime import date
from src.config import get_keywords, get_sources, get_env
from src.fetchers import (
    fetch_github_trending,
    fetch_github_search,
    fetch_hackernews,
    fetch_reddit,
    fetch_producthunt,
    fetch_huggingface,
    fetch_indie_games,
)
from src.filter import pre_filter
from src.llm import summarize
from src.reporter import generate_report
from src.dashboard import generate_dashboard
from src.feishu import send_feishu
from src.wechat import send_wechat


def main():
    print("=== AI Daily Report ===")
    cfg = get_sources()
    sources_cfg = cfg["sources"]
    report_cfg = cfg["report"]

    # ---- Fetch ----
    all_items = []

    if sources_cfg.get("github_trending", {}).get("enabled"):
        print("[fetch] GitHub Trending...")
        all_items.extend(fetch_github_trending(max_items=sources_cfg["github_trending"].get("max_items", 25)))

    if sources_cfg.get("github_search", {}).get("enabled"):
        print("[fetch] GitHub Search...")
        all_items.extend(fetch_github_search(
            queries=sources_cfg["github_search"].get("queries", []),
            per_query=sources_cfg["github_search"].get("per_query", 10),
        ))

    if sources_cfg.get("hackernews", {}).get("enabled"):
        print("[fetch] Hacker News...")
        all_items.extend(fetch_hackernews(max_items=sources_cfg["hackernews"].get("max_items", 100)))

    if sources_cfg.get("reddit", {}).get("enabled"):
        print("[fetch] Reddit...")
        all_items.extend(fetch_reddit(
            subreddits=sources_cfg["reddit"].get("subreddits", []),
            per_subreddit=sources_cfg["reddit"].get("per_subreddit", 25),
        ))

    if sources_cfg.get("producthunt", {}).get("enabled"):
        print("[fetch] ProductHunt...")
        all_items.extend(fetch_producthunt(max_items=sources_cfg["producthunt"].get("max_items", 30)))

    if sources_cfg.get("huggingface", {}).get("enabled"):
        print("[fetch] HuggingFace...")
        all_items.extend(fetch_huggingface(max_items=sources_cfg["huggingface"].get("max_items", 20)))

    if sources_cfg.get("indie_games", {}).get("enabled"):
        print("[fetch] itch.io...")
        all_items.extend(fetch_indie_games(max_items=sources_cfg["indie_games"].get("max_items", 20)))

    print(f"[fetch] Total raw items: {len(all_items)}")

    # ---- Filter ----
    keywords = get_keywords()
    filtered = pre_filter(all_items, keywords)
    print(f"[filter] After keyword filter: {len(filtered)}")

    # ---- LLM Summarize ----
    summarized = summarize(filtered)
    print(f"[llm] Summarized: {len(summarized)}")

    # ---- Generate ----
    report_path = generate_report(summarized, output_dir=cfg["output"]["reports_dir"])
    print(f"[report] Saved to {report_path}")

    dashboard_path = generate_dashboard(summarized, output_dir=cfg["output"]["docs_dir"])
    print(f"[dashboard] Saved to {dashboard_path}")

    # ---- Notify ----
    top_n = report_cfg.get("top_n", 10)
    top_items = sorted(summarized, key=lambda x: x.get("relevance_score", 0), reverse=True)[:top_n]
    dashboard_url = get_env("DASHBOARD_URL", "https://<user>.github.io/ai-daily-report/")

    send_feishu(top_items[:5], dashboard_url)
    send_wechat(top_items[:5], dashboard_url)

    print(f"=== Done: {date.today().isoformat()} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 创建 GitHub Actions 工作流**

```yaml
name: Daily AI Report

on:
  schedule:
    - cron: '17 1 * * *'     # UTC 01:17 = CST 09:17, 避开整点高峰
  workflow_dispatch:           # 支持手动触发

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  generate:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Generate daily report
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          FEISHU_WEBHOOK_URL: ${{ secrets.FEISHU_WEBHOOK_URL }}
          WECHAT_APPID: ${{ secrets.WECHAT_APPID }}
          WECHAT_APPSECRET: ${{ secrets.WECHAT_APPSECRET }}
          WECHAT_TEMPLATE_ID: ${{ secrets.WECHAT_TEMPLATE_ID }}
          DASHBOARD_URL: ${{ secrets.DASHBOARD_URL }}
        run: PYTHONPATH=. python src/main.py

      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add reports/ docs/
          if ! git diff --staged --quiet; then
            git commit -m "Daily report $(date +%Y-%m-%d)"
            git push
          else
            echo "No changes to commit"
          fi

      - name: Setup Pages
        uses: actions/configure-pages@v4

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: docs/

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 3: Commit**

```bash
git add src/main.py .github/workflows/daily.yml
git commit -m "feat: add main pipeline and GitHub Actions workflow"
```

---

### Task 13: GitHub Pages 配置 + 仓库初始化

- [ ] **Step 1: 在 GitHub 仓库 Settings → Pages 中，Source 设为 "GitHub Actions"**

（手动操作，不需要代码）

- [ ] **Step 2: 在 GitHub 仓库 Settings → Secrets and variables → Actions 中添加 Secrets：**

  - `DEEPSEEK_API_KEY`: DeepSeek API 密钥
  - `FEISHU_WEBHOOK_URL`: 飞书机器人 Webhook URL
  - `WECHAT_APPID`: 公众号 AppID
  - `WECHAT_APPSECRET`: 公众号 AppSecret
  - `WECHAT_TEMPLATE_ID`: 公众号模板消息 ID
  - `DASHBOARD_URL`: GitHub Pages URL（如 `https://username.github.io/ai-daily-report/`）

- [ ] **Step 3: 手动触发一次测试运行**

在 GitHub Actions 页面 → Daily AI Report → Run workflow，验证全流程正常。

- [ ] **Step 4: 验证产物**

- 检查 `reports/` 目录是否有今日 `.md` 文件
- 检查 `docs/index.html` 是否已生成
- 检查 GitHub Pages URL 是否可以访问 Dashboard
- 检查飞书/公众号是否收到推送

---

## 自检清单

1. **Spec 覆盖**：所有设计文档中的功能点均有对应 Task
2. **无占位符**：每个代码块都是完整实现，无 TBD/TODO
3. **类型一致**：src/main.py 调用的函数签名与各模块定义一致
