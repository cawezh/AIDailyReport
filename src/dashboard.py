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
        it["stars"] = it.get("stars", 0) or it.get("points", 0) or it.get("score", 0) or it.get("votes", 0)

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
