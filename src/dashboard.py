"""HTML Dashboard — 二级分类 + 历史日期选择 SPA"""
import json
from datetime import date
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
DATA_DIR = DOCS_DIR / "data"

# ── 二级分类规则 ───────────────────────────────────────────

L1_CATEGORIES = ["游戏", "AI", "互联网", "产品", "科研"]

# 二级分类: (一级, 二级名, 匹配函数)
L2_RULES = [
    # ── 游戏 ──
    ("游戏", "Steam 游戏", lambda it: it.get("source") == "steam"),
    ("游戏", "GODOT 项目", lambda it: "godot" in _kw(it) or "godot" in it.get("title", "").lower()),
    ("游戏", "开源游戏", lambda it: "github" in it.get("url", "") and (
        "open-source" in it.get("description", "").lower() or "game" in _kw(it)
    )),
    ("游戏", "创意新游", lambda it: it.get("source") == "itch.io" or it.get("creativity_score", 0) >= 8),
    ("游戏", "其他游戏", lambda it: True),

    # ── AI ──
    ("AI", "LLM / 智能体", lambda it: _kw_has(it, ["llm", "agent", "multi-agent", "langchain", "ai-agent", "chatbot"])),
    ("AI", "多模态 / Vision", lambda it: _kw_has(it, ["multimodal", "vision", "diffusion", "cv", "text-to-image", "text-to-video", "speech-to-text"])),
    ("AI", "RAG / 检索", lambda it: _kw_has(it, ["rag", "retrieval", "retrieval-augmented", "vector-db", "embedding"])),
    ("AI", "推理 / 优化", lambda it: _kw_has(it, ["inference", "reasoning", "fine-tune", "instruction-tuning", "chain-of-thought"])),
    ("AI", "AI 工具 / 框架", lambda it: _kw_has(it, ["ollama", "openai", "claude", "copilot", "deepseek", "gpt", "chatgpt", "prompt-engineering"])),
    ("AI", "论文研究", lambda it: it.get("source") == "arxiv" and _kw_has(it, ["llm", "agent", "deep-learning", "machine-learning", "neural-network", "nlp"])),
    ("AI", "其他 AI", lambda it: True),

    # ── 互联网 ──
    ("互联网", "基础设施", lambda it: _kw_has(it, ["kubernetes", "docker", "devops", "serverless", "cloud-native", "distributed-system"])),
    ("互联网", "开发者工具", lambda it: _kw_has(it, ["dev-tools", "developer-tools", "cli", "framework", "compiler", "testing", "ci-cd"])),
    ("互联网", "安全 / 认证", lambda it: _kw_has(it, ["security", "authentication"])),
    ("互联网", "数据库 / 存储", lambda it: _kw_has(it, ["database", "postgresql", "redis", "mongodb", "streaming"])),
    ("互联网", "其他基础设施", lambda it: True),

    # ── 产品 ──
    ("产品", "AI 产品", lambda it: _kw_has(it, ["ai", "llm", "agent", "gpt", "chatgpt"]) or
     any(w in (it.get("description", "") + it.get("cn_summary", "")).lower() for w in ["ai", "llm", "agent", "copilot", "智能"])),
    ("产品", "开发者工具", lambda it: any(w in (it.get("description", "") + it.get("cn_summary", "")).lower() for w in ["code", "api", "dev", "sdk", "tool"])),
    ("产品", "其他产品", lambda it: True),

    # ── 科研 ──
    ("科研", "cs.AI", lambda it: _cat_has(it, "cs.AI")),
    ("科研", "cs.LG (机器学习)", lambda it: _cat_has(it, "cs.LG")),
    ("科研", "cs.CL (NLP)", lambda it: _cat_has(it, "cs.CL")),
    ("科研", "cs.CV (视觉)", lambda it: _cat_has(it, "cs.CV")),
    ("科研", "其他 cs.*", lambda it: any(c.startswith("cs.") for c in it.get("categories", []))),
    ("科研", "其他论文", lambda it: True),
]


def _kw(it) -> list:
    return it.get("matched_keywords", [])


def _kw_has(it, words) -> bool:
    kw = [k.lower() for k in _kw(it)]
    return any(w in kw for w in words)


def _cat_has(it, cat) -> bool:
    return cat in it.get("categories", [])


def _pick_l1(item: dict) -> str:
    """确定项目的一级分类"""
    src = item.get("source", "")
    pc = item.get("primary_category", "")

    if src == "steam":
        return "游戏"
    if src == "producthunt":
        return "产品"
    if src == "arxiv":
        return "科研"
    if pc == "game":
        return "游戏"
    if pc == "ai":
        return "AI"
    if pc == "internet":
        return "互联网"
    if pc == "android":
        return "互联网"
    return "互联网"


def classify(items: list[dict]) -> dict:
    """二级分类。

    返回:
    {
      "游戏": {"count": N, "children": [{"name": "Steam 游戏", "count": N, "items": [...]}, ...]},
      "AI": {...}, ...
    }
    """
    # 一级分类桶
    buckets = {l1: [] for l1 in L1_CATEGORIES}
    for it in items:
        l1 = _pick_l1(it)
        buckets[l1].append(it)

    result = {}
    for l1 in L1_CATEGORIES:
        pool = buckets[l1]
        # 按 L2 规则分配
        assigned = set()
        children = []
        for rule_l1, l2_name, fn in L2_RULES:
            if rule_l1 != l1:
                continue
            matched = []
            for i, it in enumerate(pool):
                if i not in assigned and fn(it):
                    matched.append(it)
                    assigned.add(i)
            if matched:
                children.append({"name": l2_name, "count": len(matched), "items": matched})

        result[l1] = {"count": len(pool), "children": children}
    return result


# ── 数据持久化 ─────────────────────────────────────────────

def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_daily_data(items: list[dict], overview: dict = None):
    """保存当天分类数据到 docs/data/{date}.json"""
    _ensure_data_dir()

    # 热度统一
    for it in items:
        it["stars"] = it.get("stars", 0) or it.get("points", 0) or it.get("score", 0) or it.get("votes", 0)

    today = date.today().isoformat()
    categorized = classify(items)

    payload = {
        "date": today,
        "total": len(items),
        "overview": overview or {"overview": "", "hot_trends": []},
        "categories": categorized,
    }
    out = DATA_DIR / f"{today}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False))
    return out


def update_manifest(items: list[dict], overview: dict = None):
    """更新 manifest.json，保持已有记录"""
    _ensure_data_dir()

    today = date.today().isoformat()
    overview = overview or {}

    mf = DATA_DIR / "manifest.json"
    dates = []
    if mf.exists():
        data = json.loads(mf.read_text())
        dates = data.get("dates", [])

    existing_dates = {d["date"] for d in dates}
    if today not in existing_dates:
        import collections
        l1_counts = collections.Counter(_pick_l1(it) for it in items)
        dates.append({
            "date": today,
            "total": len(items),
            "overview": overview.get("overview", "")[:80],
            "counts": dict(l1_counts),
        })
        dates.sort(key=lambda d: d["date"], reverse=True)

    mf.write_text(json.dumps({"dates": dates}, ensure_ascii=False))
    return mf


# ── SPA 首页生成 ───────────────────────────────────────────

def generate_index_html() -> Path:
    """生成自包含 SPA 首页 docs/index.html"""
    _ensure_data_dir()

    import textwrap

    html = textwrap.dedent(f"""\
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 技术日报</title>
    <style>
      :root {{ --bg: #0d1117; --card: #161b22; --border: #30363d; --text: #c9d1d9; --accent: #58a6ff; --green: #3fb950; --orange: #d2991d; --purple: #a371f7; }}
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); padding: 20px; max-width: 960px; margin: 0 auto; }}
      header {{ text-align: center; padding: 30px 0 16px; }}
      h1 {{ font-size: 1.6rem; color: var(--accent); }}
      .date-nav {{ display: flex; align-items: center; justify-content: center; gap: 12px; margin: 12px 0; }}
      .date-nav button {{ background: var(--card); border: 1px solid var(--border); color: var(--text); padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 1rem; }}
      .date-nav button:hover {{ border-color: var(--accent); }}
      .date-nav select {{ background: var(--card); border: 1px solid var(--border); color: var(--text); padding: 6px 12px; border-radius: 6px; font-size: 1rem; cursor: pointer; }}
      .stats {{ display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; margin: 16px 0; }}
      .stat {{ background: var(--card); padding: 10px 18px; border-radius: 8px; text-align: center; min-width: 80px; cursor: pointer; transition: border-color 0.2s; border: 1px solid var(--border); }}
      .stat:hover {{ border-color: var(--accent); }}
      .stat.active {{ border-color: var(--accent); background: #1a2332; }}
      .stat .num {{ font-size: 1.3rem; font-weight: bold; color: var(--accent); }}
      .stat .label {{ font-size: 0.75rem; color: #8b949e; }}
      .overview-box {{ background: linear-gradient(135deg, #1a2332, #16233a); border: 1px solid var(--accent); border-radius: 12px; padding: 16px; margin: 16px auto; display: none; }}
      .overview-box p {{ line-height: 1.6; }}
      .trends {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }}
      .trend {{ background: #1f3a5f; color: var(--accent); padding: 2px 10px; border-radius: 12px; font-size: 0.8rem; }}
      .search-box {{ display: flex; justify-content: center; margin: 12px 0; }}
      .search-box input {{ background: var(--card); border: 1px solid var(--border); color: var(--text); padding: 8px 16px; border-radius: 6px; width: 100%; max-width: 400px; font-size: 1rem; }}
      .search-box input:focus {{ outline: none; border-color: var(--accent); }}
      .l1-section {{ margin: 16px 0; display: none; }}
      .l1-section.active {{ display: block; }}
      .l1-title {{ font-size: 1.2rem; margin: 20px 0 10px; padding-bottom: 6px; border-bottom: 2px solid var(--accent); display: flex; align-items: center; gap: 8px; }}
      .l1-title .count {{ font-size: 0.85rem; color: #8b949e; font-weight: normal; }}
      .l2-group {{ margin: 12px 0; }}
      .l2-header {{ font-size: 1rem; font-weight: 600; padding: 10px 14px; background: var(--card); border: 1px solid var(--border); border-radius: 8px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; user-select: none; }}
      .l2-header:hover {{ border-color: var(--accent); }}
      .l2-header .arrow {{ transition: transform 0.2s; }}
      .l2-header.open .arrow {{ transform: rotate(90deg); }}
      .l2-body {{ display: none; padding: 4px 0 4px 8px; }}
      .l2-body.open {{ display: block; }}
      .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 6px; padding: 12px; margin: 6px 0; }}
      .card .title {{ font-size: 0.95rem; font-weight: 600; }}
      .card .title a {{ color: var(--accent); text-decoration: none; }}
      .card .meta {{ font-size: 0.78rem; color: #8b949e; margin-top: 2px; }}
      .card .summary {{ margin-top: 6px; font-size: 0.88rem; line-height: 1.5; }}
      .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; margin-left: 6px; }}
      .badge-star {{ background: #1f3a23; color: var(--green); }}
      .badge-creative {{ background: #3a2f1f; color: var(--orange); }}
      .loading {{ text-align: center; padding: 40px; color: #8b949e; }}
      .empty {{ text-align: center; padding: 20px; color: #8b949e; font-style: italic; }}
      footer {{ text-align: center; padding: 30px 0 20px; color: #8b949e; font-size: 0.8rem; }}
      @media (max-width: 600px) {{ body {{ padding: 10px; }} .stats {{ gap: 6px; }} .stat {{ padding: 6px 10px; min-width: 60px; }} }}
    </style>
    </head>
    <body>
    <header>
      <h1>AI 技术日报</h1>
      <div class="date-nav">
        <button onclick="prevDay()" title="前一天">◀</button>
        <select id="dateSelect" onchange="loadDate(this.value)"></select>
        <button onclick="nextDay()" title="后一天">▶</button>
      </div>
      <div class="stats" id="stats"></div>
      <div class="overview-box" id="overviewBox">
        <p id="overviewText"></p>
        <div class="trends" id="trendsList"></div>
      </div>
      <div class="search-box">
        <input type="text" id="search" placeholder="搜索项目..." oninput="filterCards(this.value)">
      </div>
    </header>
    <div id="content"><div class="loading">加载中...</div></div>
    <footer>自动生成 | 数据来源: GitHub, HN, Reddit, ProductHunt, HuggingFace, itch.io, arXiv, Steam</footer>

    <script>
    var MANIFEST = {{ dates: [] }};
    var CURRENT_DATA = null;
    var CURRENT_DATE = '';
    var ACTIVE_L1 = '全部';
    var ALL_DATES = [];

    async function init() {{
      var hash = window.location.hash.slice(1);
      try {{
        var r = await fetch('data/manifest.json');
        MANIFEST = await r.json();
        ALL_DATES = MANIFEST.dates.map(function(d) {{ return d.date; }}).sort();
      }} catch(e) {{ console.log('No manifest yet'); }}
      buildDateSelect();
      var target = hash || (ALL_DATES[0] || '');
      await loadDate(target);
    }}

    function buildDateSelect() {{
      var sel = document.getElementById('dateSelect');
      sel.innerHTML = '';
      MANIFEST.dates.forEach(function(d) {{
        var opt = document.createElement('option');
        opt.value = d.date;
        opt.textContent = d.date + ' (' + d.total + '项)';
        sel.appendChild(opt);
      }});
    }}

    async function loadDate(d) {{
      if (!d || d === CURRENT_DATE) return;
      CURRENT_DATE = d;
      document.getElementById('dateSelect').value = d;
      window.location.hash = d;
      document.getElementById('content').innerHTML = '<div class="loading">加载中...</div>';

      try {{
        var r = await fetch('data/' + d + '.json');
        CURRENT_DATA = await r.json();
      }} catch(e) {{
        document.getElementById('content').innerHTML = '<div class="loading">暂无该日数据</div>';
        return;
      }}
      render();
    }}

    function prevDay() {{
      var idx = ALL_DATES.indexOf(CURRENT_DATE);
      if (idx > 0) loadDate(ALL_DATES[idx - 1]);
    }}

    function nextDay() {{
      var idx = ALL_DATES.indexOf(CURRENT_DATE);
      if (idx < ALL_DATES.length - 1) loadDate(ALL_DATES[idx + 1]);
    }}

    function render() {{
      var d = CURRENT_DATA;
      if (!d) return;
      document.title = 'AI 技术日报 — ' + d.date;

      // 统计卡片
      var stats = document.getElementById('stats');
      var cats = ['全部', '游戏', 'AI', '互联网', '产品', '科研'];
      var counts = {{}};
      cats.slice(1).forEach(function(c) {{ counts[c] = 0; }});
      Object.entries(d.categories || {{}}).forEach(function(e) {{ counts[e[0]] = e[1].count; }});
      counts['全部'] = d.total;

      stats.innerHTML = cats.map(function(c, i) {{
        return '<div class="stat' + (i === 0 ? ' active' : '') + '" onclick="filterL1(\\'' + c + '\\', this)" data-cat="' + c + '">'
          + '<div class="num">' + (counts[c] || 0) + '</div>'
          + '<div class="label">' + c + '</div></div>';
      }}).join('');

      // 概览
      var ov = d.overview || {{}};
      var ovBox = document.getElementById('overviewBox');
      if (ov.overview) {{
        ovBox.style.display = 'block';
        document.getElementById('overviewText').textContent = ov.overview;
        var trendsList = document.getElementById('trendsList');
        trendsList.innerHTML = (ov.hot_trends || []).map(function(t) {{
          return '<span class="trend">' + t + '</span>';
        }}).join('');
      }} else {{
        ovBox.style.display = 'none';
      }}

      // 分类内容
      var content = document.getElementById('content');
      var l1Order = ['游戏', 'AI', '互联网', '产品', '科研'];
      var l1Icons = {{'游戏': '🎮', 'AI': '🤖', '互联网': '🌐', '产品': '🚀', '科研': '📄'}};

      content.innerHTML = l1Order.map(function(l1) {{
        var l1Data = (d.categories || {{}})[l1];
        if (!l1Data || l1Data.count === 0) return '';
        var icon = l1Icons[l1] || '';
        var children = l1Data.children || [];
        return '<div class="l1-section active" data-l1="' + l1 + '">'
          + '<div class="l1-title">' + icon + ' ' + l1 + ' <span class="count">(' + l1Data.count + '项)</span></div>'
          + children.map(function(ch, ci) {{
              var itemsHtml = ch.items.map(function(it) {{
                var badges = '';
                if (it.stars) badges += '<span class="badge badge-star">⭐ ' + it.stars + '</span>';
                if (it.is_novel) badges += '<span class="badge badge-creative">潜力股</span>';
                if (it.creativity_score) badges += '<span class="badge badge-creative">创意 ' + it.creativity_score + '/10</span>';
                var kw = (it.title + ' ' + (it.cn_summary || '') + ' ' + (it.source || '')).toLowerCase();
                return '<div class="card" data-keywords="' + kw + '" data-l1="' + l1 + '">'
                  + '<div class="title"><a href="' + it.url + '" target="_blank">' + it.title + '</a>' + badges + '</div>'
                  + '<div class="meta">来源: ' + (it.source || '') + '</div>'
                  + '<div class="summary">' + (it.cn_summary || it.description || '') + '</div>'
                  + '</div>';
              }}).join('');
              return '<div class="l2-group">'
                + '<div class="l2-header' + (ci === 0 ? ' open' : '') + '" onclick="toggleL2(this)">'
                + '<span>' + ch.name + ' (' + ch.count + ')</span>'
                + '<span class="arrow">▶</span></div>'
                + '<div class="l2-body' + (ci === 0 ? ' open' : '') + '">' + itemsHtml + '</div>'
                + '</div>';
          }}).join('')
          + '</div>';
      }}).join('');

      ACTIVE_L1 = '全部';
      filterL1('全部', document.querySelector('.stat[data-cat="全部"]'));
    }}

    function toggleL2(el) {{
      el.classList.toggle('open');
      el.nextElementSibling.classList.toggle('open');
    }}

    function filterL1(cat, el) {{
      ACTIVE_L1 = cat;
      document.querySelectorAll('.stat').forEach(function(s) {{ s.classList.remove('active'); }});
      if (el) el.classList.add('active');

      document.querySelectorAll('.l1-section').forEach(function(s) {{
        if (cat === '全部') {{ s.classList.add('active'); }}
        else {{ s.classList.toggle('active', s.getAttribute('data-l1') === cat); }}
      }});
    }}

    function filterCards(query) {{
      var q = query.toLowerCase().trim();
      // 搜索时显示全部 L1
      if (q) filterL1('全部', document.querySelector('.stat[data-cat="全部"]'));
      document.querySelectorAll('.card').forEach(function(card) {{
        var kw = (card.getAttribute('data-keywords') || '').toLowerCase();
        card.style.display = (!q || kw.includes(q)) ? '' : 'none';
      }});
    }}

    init();
    </script>
    </body>
    </html>
    """)

    out = DOCS_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    return out
