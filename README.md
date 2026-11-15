# Bangumi Recommender · 番剧推荐系统

A taste-aware recommender for anime, manga and light novels, built on data crawled from
[bangumi.tv](https://bangumi.tv). Pick preference tags (isekai, yuri, sci-fi…), restrict to the current
season, and get an explained recommendation in milliseconds.

基于 bangumi.tv 数据抓取的口味化番剧 / 漫画 / 轻小说推荐系统。选择偏好标签（异世界、百合、科幻…）、
限定当季，即可获得带解释的推荐结果。

## Run locally · 本地运行

```bash
pip install -r requirements.txt
python app.py --host 127.0.0.1 --port 5000
# http://127.0.0.1:5000/?lang=zh    中文
# http://127.0.0.1:5000/?lang=en    English
```

## API

```
GET /api/recommend?tags=异世界,百合&kind=anime&airing=1&n=12&wq=1&wh=0.6&wf=1&div=0.6
```

| Parameter | Meaning | 含义 |
|---|---|---|
| `tags` | comma separated preference tags | 逗号分隔的偏好标签 |
| `kind` | `anime` / `book` / `all` | 类型 |
| `airing` | `1` = only currently airing | 只看在播 |
| `n` | number of results (6–30) | 结果数 |
| `wq` / `wh` / `wf` | quality / heat / freshness weights | 口碑 / 热度 / 新番权重 |
| `div` | diversity 0–1 (MMR) | 多样性 |

## Model · 模型

```
score(i) = cos(q, v_i) + 0.25·w_q·z(bayes_i) + 0.20·w_h·z(heat_i) + 0.50·w_f·fresh_i
```

`q` — TF-IDF preference vector · 偏好标签向量; `v_i` — item tag vector · 条目标签向量;
`bayes` — Bayesian average · 贝叶斯平均; `heat` — log votes · 对数热度;
`fresh` — season/airing boost · 当季加成; MMR re-ranking for diversity · MMR 多样性重排.

## Data · 数据

912 items (632 anime / 280 books), 137 airing in 2026-10, 8,125 ratings from 165 users.
Collected politely from public pages and the public API; see `DEPLOY.md` for details.
912 个条目（动画 632 / 书籍 280），当季 137 部，8,125 条评分、165 位用户。

## License · 许可

Course project (CISC3014, University of Macau). Data belongs to bangumi.tv and its contributors;
this repository is for academic use only. · 课程项目，数据版权归 bangumi.tv 及其贡献者，仅供学习使用。
