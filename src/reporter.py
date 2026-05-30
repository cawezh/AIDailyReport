"""Markdown 日报生成器"""
from datetime import date
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def generate_report(
    items: list[dict],
    output_dir: str = "reports",
    overview: dict = None,
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

    # 热度统一字段（提前到排序之前）
    for it in items:
        it["stars"] = it.get("stars", 0) or it.get("points", 0) or it.get("score", 0) or it.get("votes", 0)

    # 开源游戏
    game_oss_items = [
        it for it in game_items
        if it not in godot_items and ("open-source" in it.get("description", "").lower() or "github" in it.get("url", ""))
    ]

    # 创意新游（itch.io 来源 + 高创新分）
    creative_games = [it for it in game_items if it.get("source") == "itch.io" or it.get("innovation_score", 0) >= 8]

    # 多智能体
    multi_agent_items = [it for it in items if it.get("is_highlight") and "agent" in it.get("matched_keywords", [])]

    # 高光项目
    highlights = [it for it in items if it.get("is_highlight")]

    # 潜力新兴项目
    novel_items = [it for it in items if it.get("is_novel")]

    # 按数据源分类
    arxiv_items = [it for it in items if it.get("source") == "arxiv"]
    steam_items = [it for it in items if it.get("source") == "steam"]
    producthunt_items = [it for it in items if it.get("source") == "producthunt"]

    # Top 10
    top10 = sorted(items, key=lambda x: (x.get("relevance_score", 0), x.get("stars", 0)), reverse=True)[:10]

    content = template.render(
        date=today,
        total=len(items),
        overview=overview or {"overview": "", "hot_trends": []},
        counts={
            "ai": len(ai_items),
            "game": len(game_items),
            "android": len(android_items),
            "internet": len(internet_items),
            "arxiv": len(arxiv_items),
            "steam": len(steam_items),
            "producthunt": len(producthunt_items),
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
        novel_items=novel_items[:10],
        arxiv_items=arxiv_items,
        steam_items=steam_items,
        producthunt_items=producthunt_items,
    )

    out_path = Path(output_dir) / f"{today}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")

    return out_path
