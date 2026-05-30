# AI 技术日报系统 — 设计文档

**日期**: 2026-05-30
**状态**: 待实现

---

## 概述

一个 GitHub Actions 驱动的每日技术日报系统，自动抓取 GitHub、Hacker News、Reddit 等 10+ 主流网站，通过 DeepSeek v4 智能筛选和总结 AI、游戏、Android、互联网相关热门内容，重点关注 GODOT 开源项目（引擎插件、工具链、成品游戏）、开源游戏创意和多智能体协同办公。产物包括 Markdown 日报（本地留档）、Web Dashboard（GitHub Pages 展示）、飞书推送和微信公众号推送。

## 架构

```
GitHub Actions (schedule: 每天 9:00 CST)
    │
    ├── Fetch Layer (并行)
    │   ├── GitHub Trending      → trending repos
    │   ├── GitHub Search API    → keyword search
    │   ├── Hacker News API      → top/ask/show stories
    │   ├── Reddit API           → r/gamedev, r/MachineLearning, r/androiddev
    │   ├── ProductHunt          → trending products
    │   ├── HuggingFace          → trending models
    │   ├── GitHub Search "godot" → GODOT 开源项目
    │   ├── itch.io / IndieDB    → indie games
    │   └── RSS (TechCrunch等)   → tech news
    │
    ├── Filter Layer
    │   ├── Keyword pre-filter   → numpy keywords
    │   └── DeepSeek v4          → classify + chinese summary + score
    │
    ├── Generate Layer
    │   ├── reports/YYYY-MM-DD.md  → Markdown 日报
    │   ├── docs/index.html        → Dashboard (GitHub Pages)
    │   ├── 飞书 Webhook           → 卡片推送
    │   └── 微信公众号模板消息     → 图文推送
    │
    └── Git auto-commit (reports + docs)
```

## 项目结构

```
ai-daily-report/
├── .github/workflows/daily.yml          # GitHub Actions 定时任务
├── src/
│   ├── main.py                           # 入口：编排全流程
│   ├── config.py                         # 加载配置
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── github_trending.py            # GitHub Trending 抓取
│   │   ├── github_search.py             # GitHub Search API
│   │   ├── hackernews.py                # HN API
│   │   ├── reddit.py                    # Reddit API
│   │   ├── producthunt.py               # ProductHunt
│   │   ├── huggingface.py               # HF Trending
│   │   └── indie_games.py              # itch.io / IndieDB
│   ├── filter.py                        # 关键词预筛选
│   ├── llm.py                           # DeepSeek API 调用
│   ├── reporter.py                      # Markdown 报告生成
│   ├── dashboard.py                     # HTML Dashboard 生成
│   ├── feishu.py                        # 飞书 Webhook 推送
│   └── wechat.py                        # 微信公众号模板消息推送
├── config/
│   ├── keywords.yaml                    # 筛选关键词
│   └── sources.yaml                     # 数据源配置
├── reports/                             # 生成的日报 .md
├── docs/                                # GitHub Pages 站点
│   ├── index.html                       # Dashboard 主页
│   └── reports/                         # 历史报告 HTML
├── templates/
│   ├── report.md.j2                     # Markdown 模板
│   ├── dashboard.html.j2                # Dashboard 模板
│   └── feishu_card.json.j2             # 飞书卡片模板
├── requirements.txt
└── README.md
```

## 数据源详情

### GitHub Trending
- 端点：`https://github.com/trending` （HTML 解析）
- 频率：daily / weekly
- 分类：全部语言，后按关键词筛选

### GitHub Search API
- 端点：`GET /search/repositories`
- 搜索词：`godot`, `godot-engine`, `godot-plugin`, `godot-game`, `gdscript`, `game-engine`, `multi-agent`, `agent-framework`, `android`, `open-source-game`, `llm`, `rag`, `ai-agent`
- 排序：stars, updated
- 无需 Token 即可读取公开仓库

### Hacker News
- 端点：`https://hacker-news.firebaseio.com/v0/`
- 获取 topstories 前 100 条，按标题关键词筛选

### Reddit
- Subreddits：`r/gamedev`, `r/MachineLearning`, `r/androiddev`, `r/programming`, `r/indiegames`
- 端点：`https://www.reddit.com/r/{sub}/hot.json`
- 无需 API Key

### ProductHunt
- HTML 解析首页 trending 产品
- 按 AI、游戏、开发者工具分类

### HuggingFace
- HTML 解析 models/datasets trending 页面
- 按下载量/点赞排序

### 独立游戏（itch.io / IndieDB）
- itch.io：HTML 解析热门/新品
- IndieDB：RSS 订阅

## 筛选机制（两级）

### 第一级：关键词预筛
在 `config/keywords.yaml` 维护四类关键词：

- **AI**：`llm`, `agent`, `rag`, `multimodal`, `fine-tune`, `inference`, `transformer`, `embedding`, `vector-db`, `prompt`, `chain-of-thought`
- **游戏**：`godot`, `godot-engine`, `godot-plugin`, `godot-game`, `gdscript`, `godot-shader`, `godot-tool`, `game-engine`, `open-source-game`, `indie-game`, `bevy`, `roguelike`, `sandbox`, `procedural-generation`, `game-ai`, `multiplayer`
- **Android**：`android`, `jetpack`, `compose`, `kotlin`, `flutter`, `react-native`, `performance`, `reverse-engineering`
- **互联网**：`distributed`, `protocol`, `devops`, `kubernetes`, `rust`, `go`, `database`, `streaming`, `edge-computing`

### 第二级：DeepSeek v4 精筛
通过 DeepSeek API 对预筛结果进行分类、打分和中文摘要生成：

- 输入：标题 + 简介 + 来源 + star/热度
- 输出：`{category, relevance_score, cn_summary, creativity_score, is_highlight}`
- 开源游戏额外评估创意新颖度
- 多智能体项目额外评估协同设计思路

## 产物规格

### Markdown 日报
保存路径：`reports/YYYY-MM-DD.md`

```markdown
# AI 技术日报 — 2026.05.30

## 今日概览
- 收录项目：47 | AI: 18 | 游戏: 12 | Android: 8 | 互联网: 9
- 重点关注：3 个创新游戏 | 2 个多智能体项目

## 🔥 今日 Top 10

## 🤖 AI 相关
### 项目
| 项目 | Stars | 摘要 |
|------|-------|------|
| ... | ... | ... |

### 论文 / 模型

## 🎮 游戏相关
### 🔧 GODOT 项目（重点关注）
### 开源游戏
### 💡 创意新游

## 📱 Android 相关

## 🌐 互联网 / 基础设施

## 📌 多智能体协同（重点关注）
```

### Web Dashboard
- 单页应用，纯静态 HTML + CSS + JS
- 日期选择器 → 加载对应日报
- 四个 Tab 切换
- 创意游戏 & 多智能体专区置顶高亮
- 搜索功能：按项目名/关键词搜索
- 响应式布局，移动端适配

### 飞书推送
- 卡片消息模板
- 内容：日期 + Top 5 摘要 + Dashboard 链接
- 通过飞书 Webhook 发送

### 微信公众号推送
- 使用公众号官方模板消息 API，完全合规
- 仅推送给已关注公众号的用户
- 需要：`WECHAT_APPID` + `WECHAT_APPSECRET` + 模板 ID
- 调用流程：获取 access_token → 发送模板消息
- 消息内容：日报概要 + 点击跳转 Dashboard 链接
- 注意：订阅号单个粉丝日推送上限约 1-2 条，日报每天仅 1 次推送，不受影响

## GitHub Actions 工作流

```yaml
name: Daily AI Report
on:
  schedule:
    - cron: '0 1 * * *'   # UTC 01:00 = CST 09:00
  workflow_dispatch:        # 支持手动触发
jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r requirements.txt
      - run: python src/main.py
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          FEISHU_WEBHOOK_URL: ${{ secrets.FEISHU_WEBHOOK_URL }}
          WECHAT_APPID: ${{ secrets.WECHAT_APPID }}
          WECHAT_APPSECRET: ${{ secrets.WECHAT_APPSECRET }}
          WECHAT_TEMPLATE_ID: ${{ secrets.WECHAT_TEMPLATE_ID }}
      - run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add reports/ docs/
          git diff --staged --quiet || git commit -m "Daily report $(date +%Y-%m-%d)"
          git push
```

## 成本估算

| 项目 | 用量 | 费用 |
|------|------|------|
| GitHub Actions | ~90分钟/月 | 免费（2000分钟/月额度） |
| GitHub Pages | 静态托管 | 免费 |
| DeepSeek API | ~50K tokens/天 | ~$0.05/天 ≈ $1.5/月 |
| 其他 API | GitHub/HN/Reddit | 免费 |

**总计：约 $1.5/月，几乎零成本。**

## 配置项

### 环境变量（GitHub Secrets）
- `DEEPSEEK_API_KEY`：DeepSeek API 密钥
- `FEISHU_WEBHOOK_URL`：飞书机器人 Webhook 地址
- `WECHAT_APPID`：微信公众号 AppID
- `WECHAT_APPSECRET`：微信公众号 AppSecret
- `WECHAT_TEMPLATE_ID`：模板消息 ID

### config/keywords.yaml
- 四类关键词列表
- 支持动态增删

### config/sources.yaml
- 各数据源开关（可单独启停）
- 抓取数量限制

## 实现阶段

### 阶段 1：核心流水线
- GitHub Actions 工作流骨架
- GitHub Trending + Search API 抓取
- 关键词预筛
- DeepSeek 摘要生成
- Markdown 报告生成

### 阶段 2：多源扩展
- Hacker News、Reddit 接入
- ProductHunt、HuggingFace 接入
- 独立游戏源接入

### 阶段 3：Dashboard + 推送
- HTML Dashboard 生成
- GitHub Pages 配置
- 飞书卡片推送

### 阶段 4：优化
- 增量更新（避免抓重复内容）
- 历史趋势图
- 个性化订阅配置
