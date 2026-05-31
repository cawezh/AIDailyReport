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
    ("游戏", "创意新游", lambda it: it.get("source") == "itch.io" or it.get("innovation_score", 0) >= 8),
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


def save_daily_data(items: list[dict], overview: dict = None, key: str = None):
    """保存分类数据到 docs/data/{key}.json，默认当天日期。周报用 week_key"""
    _ensure_data_dir()

    for it in items:
        it["stars"] = it.get("stars", 0) or it.get("points", 0) or it.get("score", 0) or it.get("votes", 0)

    day_key = key or date.today().isoformat()
    categorized = classify(items)

    payload = {
        "date": day_key,
        "total": len(items),
        "overview": overview or {"overview": "", "hot_trends": []},
        "categories": categorized,
    }
    out = DATA_DIR / f"{day_key}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False))
    return out


def update_manifest(items: list[dict], overview: dict = None, key: str = None, weekly: bool = False):
    """更新 manifest.json"""
    _ensure_data_dir()

    day_key = key or date.today().isoformat()
    overview = overview or {}

    mf = DATA_DIR / "manifest.json"
    dates = []
    if mf.exists():
        data = json.loads(mf.read_text())
        dates = data.get("dates", [])

    import collections
    l1_counts = collections.Counter(_pick_l1(it) for it in items)
    entry = {
        "date": day_key,
        "total": len(items),
        "overview": overview.get("overview", "")[:80],
        "counts": dict(l1_counts),
        "type": "weekly" if weekly else "daily",
    }
    # upsert
    replaced = False
    for i, d in enumerate(dates):
        if d["date"] == day_key:
            dates[i] = entry
            replaced = True
            break
    if not replaced:
        dates.append(entry)
    dates.sort(key=lambda d: d["date"], reverse=True)

    mf.write_text(json.dumps({"dates": dates}, ensure_ascii=False))
    return mf


# ── SPA 首页生成 ───────────────────────────────────────────

def generate_index_html() -> Path:
    """生成自包含 SPA 首页 docs/index.html"""
    _ensure_data_dir()

    import time
    import textwrap

    ts = int(time.time())

    html = textwrap.dedent(f"""\
    <!DOCTYPE html>
    <html lang="zh-CN" class="bg-zinc-950">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 技术日报</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
      tailwind.config = {{
        theme: {{
          extend: {{
            fontFamily: {{ sans: ['-apple-system','BlinkMacSystemFont','"Segoe UI"','Roboto','sans-serif'] }}
          }}
        }}
      }}
    </script>
    <style>
      .l1-panel, .l2-panel {{ display: none; }}
      .l1-panel.active, .l2-panel.active {{ display: block; }}
    </style>
    </head>
    <body class="bg-zinc-950 text-zinc-300 min-h-screen">
    <div class="max-w-4xl mx-auto px-4 py-6 md:py-10">

    <!-- Header -->
    <header class="text-center mb-8">
      <h1 class="text-3xl font-bold text-white tracking-tight">
        <span class="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">AI 技术日报</span>
      </h1>
      <p class="text-zinc-500 text-sm mt-2">聚合 GitHub · HN · Reddit · ProductHunt · arXiv · Steam 的每日技术趋势</p>
    </header>

    <!-- Date Navigator -->
    <div class="flex items-center justify-center gap-3 mb-6">
      <button onclick="prevDay()" class="flex items-center justify-center w-9 h-9 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white hover:border-zinc-600 transition text-sm">◀</button>
      <select id="dateSelect" onchange="loadDate(this.value)" class="bg-zinc-900 border border-zinc-700 text-zinc-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500 cursor-pointer appearance-none text-center min-w-[180px]"></select>
      <button onclick="nextDay()" class="flex items-center justify-center w-9 h-9 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white hover:border-zinc-600 transition text-sm">▶</button>
    </div>

    <!-- Overview -->
    <div id="overviewBox" class="hidden mb-6 p-5 bg-gradient-to-br from-blue-950/40 to-zinc-900 border border-blue-500/20 rounded-2xl">
      <p id="overviewText" class="text-zinc-300 leading-relaxed text-sm"></p>
      <div id="trendsList" class="flex gap-2 flex-wrap mt-3"></div>
    </div>

    <!-- L1 Tabs -->
    <div class="flex justify-center mb-3">
      <div id="l1Tabs" class="inline-flex bg-zinc-900 rounded-2xl p-1 gap-0.5 flex-wrap justify-center"></div>
    </div>

    <!-- L2 Tabs -->
    <div class="flex justify-center mb-5">
      <div id="l2Tabs" class="flex gap-2 flex-wrap justify-center"></div>
    </div>

    <!-- Search -->
    <div class="flex justify-center mb-6">
      <div class="relative w-full max-w-md">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
        <input type="text" id="search" placeholder="搜索标题、摘要、来源..." oninput="filterCards(this.value)"
          class="w-full pl-10 pr-4 py-2.5 bg-zinc-900 border border-zinc-800 rounded-xl text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition">
      </div>
    </div>

    <!-- Content -->
    <div id="content" class="min-h-[200px]">
      <div class="text-center py-16 text-zinc-600 text-sm">加载中...</div>
    </div>

    <!-- Footer -->
    <footer class="text-center mt-12 py-8 border-t border-zinc-800/50">
      <p class="text-zinc-600 text-xs">GitHub · Hacker News · Reddit · ProductHunt · HuggingFace · itch.io · arXiv · Steam</p>
    </footer>
    </div>

    <script>
    var MANIFEST = {{ dates: [] }};
    var CURRENT_DATA = null;
    var CURRENT_DATE = '';
    var ACTIVE_L1 = '全部';
    var ACTIVE_L2 = '全部';
    var ALL_DATES = [];
    var ALL_L2 = [];
    var CACHE_VER = '{ts}';

    async function init() {{
      var hash = window.location.hash.slice(1);
      try {{
        var r = await fetch('data/manifest.json?v=' + CACHE_VER);
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
        opt.textContent = d.date + ' · ' + d.total + ' 项';
        sel.appendChild(opt);
      }});
    }}

    async function loadDate(d) {{
      if (!d || d === CURRENT_DATE) return;
      CURRENT_DATE = d;
      document.getElementById('dateSelect').value = d;
      window.location.hash = d;
      document.getElementById('content').innerHTML = '<div class="text-center py-16 text-zinc-600 text-sm">加载中...</div>';
      try {{
        var r = await fetch('data/' + d + '.json?v=' + CACHE_VER);
        CURRENT_DATA = await r.json();
      }} catch(e) {{
        document.getElementById('content').innerHTML = '<div class="text-center py-16 text-zinc-600 text-sm">暂无该日数据</div>';
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
      document.title = 'AI 技术日报 - ' + d.date;

      var ov = d.overview || {{}};
      var ovBox = document.getElementById('overviewBox');
      if (ov.overview) {{
        ovBox.classList.remove('hidden');
        document.getElementById('overviewText').textContent = ov.overview;
        document.getElementById('trendsList').innerHTML = (ov.hot_trends || []).map(function(t) {{
          return '<span class="px-2.5 py-1 rounded-full text-xs bg-blue-500/15 text-blue-300 border border-blue-500/20">' + t + '</span>';
        }}).join('');
      }} else {{
        ovBox.classList.add('hidden');
      }}

      var l1Order = ['游戏', 'AI', '互联网', '产品', '科研'];
      var counts = {{}};
      l1Order.forEach(function(c) {{ counts[c] = (d.categories && d.categories[c]) ? d.categories[c].count : 0; }});
      counts['全部'] = d.total;

      // L1 Tabs — pill group style
      var l1Icons = {{'游戏':'🎮','AI':'🤖','互联网':'🌐','产品':'🚀','科研':'📄'}};
      var l1Tabs = document.getElementById('l1Tabs');
      l1Tabs.innerHTML = ['全部'].concat(l1Order).map(function(c) {{
        var isActive = c === ACTIVE_L1;
        var icon = l1Icons[c] || '';
        return '<button data-cat="' + c + '" onclick="switchL1(this.dataset.cat)"'
          + ' class="px-4 py-1.5 text-sm font-medium rounded-xl transition-all duration-150 whitespace-nowrap'
          + (isActive ? ' bg-blue-600 text-white shadow-lg shadow-blue-600/25' : ' text-zinc-400 hover:text-zinc-200') + '">'
          + icon + ' ' + c + ' <span class="text-xs ' + (isActive ? 'opacity-70' : 'opacity-40') + '">' + (counts[c] || 0) + '</span></button>';
      }}).join('');

      // Content
      var content = document.getElementById('content');
      content.innerHTML = l1Order.map(function(l1) {{
        var l1Data = (d.categories || {{}})[l1];
        if (!l1Data) return '';
        var children = l1Data.children || [];
        return '<div class="l1-panel' + (l1 === ACTIVE_L1 || ACTIVE_L1 === '全部' ? ' active' : '') + '" data-l1="' + l1 + '">'
          + children.map(function(ch) {{
              var itemsHtml = ch.items.map(function(it) {{
                var badges = '';
                if (it.stars) badges += '<span class="inline-flex items-center gap-1 ml-2 px-1.5 py-0.5 rounded-md text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">⭐ ' + it.stars + '</span>';
                if (it.is_novel) badges += '<span class="ml-1.5 px-1.5 py-0.5 rounded-md text-xs bg-amber-500/10 text-amber-400 border border-amber-500/20">潜力股</span>';
                var innov = it.innovation_score || it.creativity_score || 0;
                if (innov && innov >= 7) badges += '<span class="ml-1.5 px-1.5 py-0.5 rounded-md text-xs bg-purple-500/10 text-purple-400 border border-purple-500/20">创新 ' + innov + '</span>';
                if (it.value_score && it.value_score >= 7) badges += '<span class="ml-1.5 px-1.5 py-0.5 rounded-md text-xs bg-sky-500/10 text-sky-400 border border-sky-500/20">实用 ' + it.value_score + '</span>';
                if (it.tag) badges += '<span class="ml-1.5 px-1.5 py-0.5 rounded-md text-xs bg-pink-500/10 text-pink-400 border border-pink-500/20">' + it.tag + '</span>';
                var sourceLabel = (it.source || '').replace('github_', '');
                return '<div class="card group bg-zinc-900 border border-zinc-800 rounded-xl p-4 mb-2 hover:border-zinc-700 transition-colors" data-keywords="' + (it.title + ' ' + (it.cn_summary||'') + ' ' + (it.source||'')).toLowerCase() + '">'
                  + '<div class="flex items-start justify-between gap-3">'
                  + '<div class="min-w-0 flex-1">'
                  + '<div class="flex items-center flex-wrap gap-1">'
                  + '<a href="' + it.url + '" target="_blank" class="text-sm font-semibold text-zinc-200 hover:text-blue-400 transition-colors truncate">' + it.title + '</a>'
                  + badges
                  + '</div>'
                  + '<p class="text-xs text-zinc-500 mt-1">' + sourceLabel + '</p>'
                  + '<p class="text-sm text-zinc-400 mt-2 leading-relaxed line-clamp-3">' + (it.cn_summary || it.description || '') + '</p>'
                  + (it.why_matters ? '<p class="text-xs text-amber-400/80 mt-1">💡 ' + it.why_matters + '</p>' : '')
                  + '</div></div></div>';
              }}).join('');
              var l2Icon = ch.name.startsWith('Steam') ? '🎮' : ch.name.startsWith('GODOT') ? '🔧' : ch.name.startsWith('LLM') ? '🧠' : ch.name.startsWith('多模态') ? '👁' : ch.name.startsWith('RAG') ? '📚' : ch.name.startsWith('推理') ? '⚡' : ch.name.startsWith('AI 工具') ? '🛠' : ch.name.startsWith('cs.') ? '📄' : ch.name.startsWith('开源') ? '💎' : ch.name.startsWith('创意') ? '💡' : ch.name.startsWith('基础') ? '🏗' : ch.name.startsWith('开发者') ? '🔨' : ch.name.startsWith('安全') ? '🔒' : ch.name.startsWith('数据库') ? '🗄' : ch.name.startsWith('AI 产品') ? '🤖' : '';
              return '<div class="l2-panel' + (ch.name === _lastActiveL2(l1) ? ' active' : '') + '" data-l1="' + l1 + '" data-l2="' + ch.name + '">'
                + (itemsHtml || '<div class="text-center py-10 text-zinc-600 text-sm">暂无项目</div>') + '</div>';
          }}).join('')
          + '</div>';
      }}).join('');

      ALL_L2 = [];
      var seen = {{}};
      l1Order.forEach(function(l1) {{
        var l1Data = (d.categories || {{}})[l1];
        if (!l1Data) return;
        (l1Data.children || []).forEach(function(ch) {{
          if (!seen[ch.name]) {{ seen[ch.name] = true; ALL_L2.push(ch.name); }}
        }});
      }});
      if (ACTIVE_L1 === '全部') {{ renderAllL2Tabs(); }} else {{ renderL2Tabs(ACTIVE_L1); }}
    }}

    function _lastActiveL2(l1) {{
      var d = CURRENT_DATA;
      if (!d || !d.categories || !d.categories[l1]) return '';
      var children = d.categories[l1].children || [];
      return children.length > 0 ? children[0].name : '';
    }}

    function renderL2Tabs(l1) {{
      var l2Tabs = document.getElementById('l2Tabs');
      var d = CURRENT_DATA;
      if (!d || !d.categories || !d.categories[l1]) {{ l2Tabs.innerHTML = ''; return; }}
      var children = d.categories[l1].children || [];
      var tabs = ['全部'].concat(children.map(function(ch) {{ return ch.name; }}));
      l2Tabs.innerHTML = tabs.map(function(t) {{
        var isActive = t === ACTIVE_L2;
        return '<button onclick="switchL2(this.textContent.trim())"'
          + ' class="px-3 py-1 text-xs rounded-lg transition-all duration-150 whitespace-nowrap'
          + (isActive ? ' bg-blue-500/15 text-blue-400 border border-blue-500/30' : ' text-zinc-500 hover:text-zinc-300 border border-transparent') + '">'
          + t + '</button>';
      }}).join('');
      if (ACTIVE_L1 !== l1) {{
        ACTIVE_L2 = '全部';
        document.querySelectorAll('#l2Tabs button').forEach(function(b, i) {{ b.classList.toggle('bg-blue-500/15', i === 0); b.classList.toggle('text-blue-400', i === 0); b.classList.toggle('border-blue-500/30', i === 0); }});
      }}
      applyL2Filter();
    }}

    function renderAllL2Tabs() {{
      var l2Tabs = document.getElementById('l2Tabs');
      l2Tabs.innerHTML = ['全部'].concat(ALL_L2).map(function(t) {{
        var isActive = t === ACTIVE_L2;
        return '<button onclick="switchL2(this.textContent.trim())"'
          + ' class="px-3 py-1 text-xs rounded-lg transition-all duration-150 whitespace-nowrap'
          + (isActive ? ' bg-blue-500/15 text-blue-400 border border-blue-500/30' : ' text-zinc-500 hover:text-zinc-300 border border-transparent') + '">'
          + t + '</button>';
      }}).join('');
      applyAllL2Filter();
    }}

    function applyAllL2Filter() {{
      document.querySelectorAll('.l2-panel').forEach(function(lp) {{
        lp.classList.toggle('active', ACTIVE_L2 === '全部' || lp.getAttribute('data-l2') === ACTIVE_L2);
      }});
    }}

    function switchL1(l1) {{
      ACTIVE_L1 = l1; ACTIVE_L2 = '全部'; SEARCHING = false;
      document.getElementById('search').value = '';

      document.querySelectorAll('#l1Tabs button').forEach(function(b) {{
        var isActive = b.getAttribute('data-cat') === l1;
        b.className = 'px-4 py-1.5 text-sm font-medium rounded-xl transition-all duration-150 whitespace-nowrap'
          + (isActive ? ' bg-blue-600 text-white shadow-lg shadow-blue-600/25' : ' text-zinc-400 hover:text-zinc-200');
      }});

      document.querySelectorAll('.l1-panel').forEach(function(p) {{
        var show = (l1 === '全部') || (p.getAttribute('data-l1') === l1);
        p.classList.toggle('active', show);
        p.querySelectorAll('.l2-panel').forEach(function(lp) {{ lp.classList.toggle('active', show); }});
      }});

      if (l1 === '全部') {{ renderAllL2Tabs(); }} else {{ renderL2Tabs(l1); }}
    }}

    function switchL2(l2) {{
      ACTIVE_L2 = l2;
      document.querySelectorAll('#l2Tabs button').forEach(function(b) {{
        var isActive = b.textContent.trim() === l2;
        b.className = 'px-3 py-1 text-xs rounded-lg transition-all duration-150 whitespace-nowrap'
          + (isActive ? ' bg-blue-500/15 text-blue-400 border border-blue-500/30' : ' text-zinc-500 hover:text-zinc-300 border border-transparent');
      }});
      applyL2Filter();
    }}

    function applyL2Filter() {{
      if (ACTIVE_L1 === '全部') {{ applyAllL2Filter(); return; }}
      document.querySelectorAll('.l1-panel.active .l2-panel').forEach(function(lp) {{
        lp.classList.toggle('active', ACTIVE_L2 === '全部' || lp.getAttribute('data-l2') === ACTIVE_L2);
      }});
    }}

    var SEARCHING = false;
    function filterCards(query) {{
      var q = query.toLowerCase().trim();
      if (q && !SEARCHING) {{
        SEARCHING = true;
        document.querySelectorAll('.l1-panel').forEach(function(p) {{ p.classList.add('active'); }});
        document.querySelectorAll('.l2-panel').forEach(function(p) {{ p.classList.add('active'); }});
      }} else if (!q && SEARCHING) {{
        SEARCHING = false;
        switchL1(ACTIVE_L1);
      }}
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
