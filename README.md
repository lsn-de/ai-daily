# AI 半自动日报

从国内官方渠道（机器之心 / 量子位 / 36氪等 RSS）抓取每日资讯纯文本，
AI 二次整理成多份小报告（标题 + 内容），AI 按可配置标准自评推荐星级，
最后在本地卡片式页面中人工审核，通过后归档为 Markdown。

## 流程

```
fetch 抓取 ──▶ process（AI 整理成多份小报告 + 星级自评）
                      │
                      ▼
              review 卡片式人工审核（浏览器）
                      │
                      ▼
                publish 定稿归档 Markdown
```

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env          # 填入 OPENAI_BASE_URL / OPENAI_API_KEY
cp config.example.yaml config.yaml   # 按需调整信源、评估标准

python main.py run            # 抓取 + AI 整理 + 星级自评（今天）
python main.py review         # 打开 http://127.0.0.1:7860 审核
python main.py publish        # 通过审核的报告归档到 data/published/
```

不带模型跑通流程（测试）：`python main.py run --mock`

处理历史日期：所有命令支持 `--date YYYY-MM-DD`。

## 审核（review）

卡片网格：每份小报告一张卡（标题 / 分类 / AI 星级 / 状态 / 内容预览）。
点击卡片弹出二级详情菜单，可以：

- 直接修改标题和正文
- 点击星星覆盖 AI 星级（通过时生效）
- 查看评分依据、各维度细分分、引用的原始资讯链接
- 通过 / 拒绝 / 恢复待审

## 星级评估标准（暂定，config.yaml 可改）

| 维度 | 权重 |
| --- | --- |
| 重要性 | 40% |
| 新颖性 | 20% |
| 相关性 | 20% |
| 可信度 | 10% |
| 实用性 | 10% |

## 目录结构

```
data/
├── raw/YYYY-MM-DD/        # 抓取的当日纯文本 items.json
├── drafts/YYYY-MM-DD/     # AI 整理 + 星级 + 审核状态 reports.json
└── published/YYYY-MM-DD/  # 定稿：index.md + 每份报告一个 .md
```

## 信源说明

默认启用：机器之心（官方 RSS）、量子位、36氪快讯（经公共 RSSHub）。
RSSHub 公共实例不稳定时，建议[自部署 RSSHub](https://docs.rsshub.app/)
并把 config.yaml 里的 `rsshub.app` 替换为自己的地址；也可随意增删任意 RSS 源。

## 定时（可选）

crontab 示例（每天 8:00 生成草稿）：

```
0 8 * * * cd /path/to/ai-daily && python main.py run >> run.log 2>&1
```

审核环节保留人工，publish 由你在审核完成后手动执行。
