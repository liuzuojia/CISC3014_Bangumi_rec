#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bangumi 偏好推荐 demo（Flask，中英双语）。

启动：  python app.py            ->  http://127.0.0.1:5000/?lang=zh
                                   http://127.0.0.1:5000/?lang=en
数据：  data/items.json, data/tag_matrix.npz, data/vocab.json, data/tags.json, data/stats.json

模型：  score = w_c * cos(偏好标签向量, 条目标签向量)
               + w_q * z(Bayesian 评分)
               + w_h * z(log 评价人数)
               + w_f * 当季/在播加成
        再用 MMR 做多样性重排。
"""

from __future__ import annotations

import json
import os

import numpy as np
from flask import Flask, jsonify, render_template_string, request

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
app = Flask(__name__)

items = json.load(open(os.path.join(DATA, "items.json"), encoding="utf-8"))
vocab = json.load(open(os.path.join(DATA, "vocab.json"), encoding="utf-8"))
tags = json.load(open(os.path.join(DATA, "tags.json"), encoding="utf-8"))
stats = json.load(open(os.path.join(DATA, "stats.json"), encoding="utf-8"))
idx = {t: i for i, t in enumerate(vocab)}
M = np.load(os.path.join(DATA, "tag_matrix.npz"))["matrix"]

bayes = np.array([x["bayes"] for x in items], dtype=np.float32)
heat = np.array([x["heat"] for x in items], dtype=np.float32)
fresh = np.array([1.0 if x["is_current_season"] else (0.5 if x["is_airing"] else 0.0) for x in items], dtype=np.float32)


def z(a: np.ndarray) -> np.ndarray:
    mu, sd = float(a.mean()), float(a.std()) or 1.0
    return (a - mu) / sd


Z_Q, Z_H = z(bayes), z(heat)


def query_vector(selected: list[str]) -> np.ndarray:
    q = np.zeros(M.shape[1], dtype=np.float32)
    for t in selected:
        if t in idx:
            q[idx[t]] = 1.0
    n = np.linalg.norm(q)
    return q / n if n else q


def mmr(order: list[int], relevance: np.ndarray, k: int, lam: float) -> list[int]:
    """Maximal marginal relevance over item vectors (diversity control)."""
    chosen: list[int] = []
    cand = list(order)
    while cand and len(chosen) < k:
        if not chosen:
            best = cand[0]
            chosen.append(best)
            cand = [c for c in cand if c != best]
            continue
        C = M[chosen]
        best, best_score = None, -1e9
        for i in cand:
            sim = float(np.max(C @ M[i]))
            s = lam * relevance[i] - (1 - lam) * sim
            if s > best_score:
                best, best_score = i, s
        chosen.append(best)
        cand = [c for c in cand if c != best]
    return chosen


def recommend(selected: list[str], kind: str, airing_only: bool, n: int,
              w_quality: float, w_heat: float, w_fresh: float, lam: float) -> list[dict]:
    q = query_vector(selected)
    content = M @ q if q.any() else np.zeros(len(items), dtype=np.float32)

    score = content + w_quality * 0.25 * Z_Q + w_heat * 0.20 * Z_H + w_fresh * 0.5 * fresh

    allowed = []
    for i, x in enumerate(items):
        if kind == "anime" and x["subject_type"] != 2:
            continue
        if kind == "book" and x["subject_type"] != 1:
            continue
        if airing_only and not x["is_airing"]:
            continue
        allowed.append(i)

    if not allowed:
        return []

    # when preferences are given, prefer items that actually carry one of the tags
    if q.any():
        on_tag = [i for i in allowed if content[i] > 0]
        if len(on_tag) >= max(n, 6):
            allowed = on_tag

    allowed.sort(key=lambda i: -score[i])
    top = allowed[:120]
    rel = np.full(len(items), -1e9)
    for i in top:
        rel[i] = score[i]
    picked = mmr(top, rel, n, lam) if lam < 1 else top[:n]

    out = []
    for i in (picked or top[:n]):
        x = items[i]
        its = [t for t in x["tags"].split("|") if t]
        shared = [t for t in selected if t in its]
        reason = "、".join(shared) if shared else "、".join([t for t in x["genre_tags"].split("|")[:3] if t])
        out.append(
            {
                "id": x["subject_id"],
                "name": x["name"],
                "name_orig": x["name_orig"],
                "type": x["type_label"],
                "type_en": {1: "Book", 2: "Anime"}.get(x["subject_type"], "Other"),
                "date": x["date"],
                "season": x["season"],
                "airing": bool(x["is_airing"]),
                "score": x["score"],
                "bayes": x["bayes"],
                "votes": x["rating_total"],
                "tags": its[:6],
                "reason": reason,
                "cover": x["cover"],
                "final": round(float(score[i]), 4),
                "content": round(float(content[i]), 4),
                "platform": x["platform"],
                "eps": x["eps"],
            }
        )
    return out


STRINGS = {
    "zh": {
        "title": "Bangumi 偏好推荐",
        "sub": "从 bangumi.tv 采集 {items} 个条目（动画 {anime} · 书籍 {books}）· 当季 {season} 共 {cur} 部 · 用户评分 {ratings} 条",
        "tags_h": "偏好标签（可多选）",
        "scope_h": "范围",
        "kind_anime": "动画",
        "kind_book": "书籍 / 小说",
        "kind_all": "全部",
        "airing": "只看当季在播（{season}）",
        "n": "结果数",
        "wq": "口碑权重",
        "wh": "热度权重",
        "wf": "新番加成",
        "div": "多样性",
        "go": "开始推荐",
        "hint": "选择标签后点击「开始推荐」",
        "working": "计算中…",
        "result": "按「{tags}」推荐 {n} 条",
        "reason": "推荐理由",
        "airing_badge": "在播",
        "votes": "人评分",
        "lang_label": "English",
        "lang_code": "en",
    },
    "en": {
        "title": "Bangumi recommender",
        "sub": "{items} items crawled from bangumi.tv ({anime} anime · {books} books) · {cur} airing in {season} · {ratings} user ratings",
        "tags_h": "Preference tags (multi-select)",
        "scope_h": "Scope",
        "kind_anime": "Anime",
        "kind_book": "Books / novels",
        "kind_all": "All",
        "airing": "Only airing now ({season})",
        "n": "Results",
        "wq": "Quality weight",
        "wh": "Heat weight",
        "wf": "Freshness boost",
        "div": "Diversity",
        "go": "Recommend",
        "hint": "Pick some tags, then press Recommend",
        "working": "Working…",
        "result": "Top {n} for “{tags}”",
        "reason": "Why",
        "airing_badge": "airing",
        "votes": "votes",
        "lang_label": "中文",
        "lang_code": "zh",
    },
}

PAGE = """<!doctype html>
<html lang="{{ lang }}"><head><meta charset="utf-8">
<title>{{ t.title }} · CISC3014</title>
<style>
:root{--pink:#f09199;--ink:#2b2b2b;--muted:#7a7a7a;--bg:#fbf7f6}
*{box-sizing:border-box}
body{margin:0;font-family:"Segoe UI","Microsoft YaHei",system-ui;background:var(--bg);color:var(--ink)}
header{padding:20px 28px;background:#fff;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:flex-start;gap:20px}
h1{margin:0 0 6px;font-size:22px}
.sub{color:var(--muted);font-size:13px}
.lang{font-size:13px;color:var(--pink);text-decoration:none;white-space:nowrap;border:1px solid var(--pink);padding:5px 12px;border-radius:999px}
.wrap{display:grid;grid-template-columns:330px 1fr;gap:20px;padding:20px 28px;max-width:1400px;margin:0 auto}
.panel{background:#fff;border:1px solid #eee;border-radius:12px;padding:16px}
.panel h3{margin:0 0 10px;font-size:13px;color:var(--muted);font-weight:600;letter-spacing:.04em}
.chips{display:flex;flex-wrap:wrap;gap:6px;max-height:260px;overflow:auto}
.chip{padding:5px 10px;border:1px solid #e3d6d4;border-radius:999px;font-size:12px;cursor:pointer;background:#fff;user-select:none}
.chip.on{background:var(--pink);border-color:var(--pink);color:#fff}
.row{display:flex;gap:8px;align-items:center;margin:9px 0;font-size:13px}
input[type=range]{width:100%}
select{font-size:13px;padding:6px 8px;border-radius:8px;border:1px solid #ddd;background:#fff}
button{width:100%;padding:11px;border-radius:10px;border:0;background:var(--pink);color:#fff;font-size:15px;cursor:pointer}
button:hover{filter:brightness(.96)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px}
.card{background:#fff;border:1px solid #eee;border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
.cover{height:120px;background:linear-gradient(135deg,#f6dfe0,#e8eef6);display:flex;align-items:center;justify-content:center;font-size:26px;color:#b98d8d;overflow:hidden}
.cover img{width:100%;height:100%;object-fit:cover}
.body{padding:10px 12px}
.title{font-weight:600;font-size:14px;margin-bottom:4px;line-height:1.3}
.meta{font-size:11.5px;color:var(--muted);margin-bottom:6px}
.badge{display:inline-block;padding:2px 7px;border-radius:6px;background:#fdeef0;color:#c2535e;font-size:11px;margin-right:4px}
.tag{display:inline-block;padding:2px 7px;border-radius:6px;background:#f3f3f3;color:#555;font-size:11px;margin:2px 3px 0 0}
.reason{margin-top:6px;font-size:11.5px;color:#9a6b70}
</style></head>
<body>
<header>
  <div>
    <h1>{{ t.title }}</h1>
    <div class="sub">{{ t.sub.format(items=stats['items'], anime=stats.anime, books=stats.books,
        season=stats.current_season, cur=stats.current_season_items, ratings=stats.ratings) }}</div>
  </div>
  <a class="lang" href="?lang={{ t.lang_code }}&tags={{ preset }}">{{ t.lang_label }}</a>
</header>
<div class="wrap">
  <div>
    <div class="panel">
      <h3>{{ t.tags_h }}</h3>
      <div class="chips" id="chips"></div>
    </div>
    <div class="panel" style="margin-top:14px">
      <h3>{{ t.scope_h }}</h3>
      <div class="row"><select id="kind">
        <option value="anime">{{ t.kind_anime }}</option>
        <option value="book">{{ t.kind_book }}</option>
        <option value="all">{{ t.kind_all }}</option>
      </select></div>
      <div class="row"><label><input type="checkbox" id="airing"> {{ t.airing.format(season=stats.current_season) }}</label></div>
      <div class="row">{{ t.n }} <input type="range" id="n" min="6" max="30" value="12" step="3"><span id="nv">12</span></div>
      <div class="row">{{ t.wq }} <input type="range" id="wq" min="0" max="2" value="1" step="0.1"><span id="wqv">1.0</span></div>
      <div class="row">{{ t.wh }} <input type="range" id="wh" min="0" max="2" value="0.6" step="0.1"><span id="whv">0.6</span></div>
      <div class="row">{{ t.wf }} <input type="range" id="wf" min="0" max="2" value="1" step="0.1"><span id="wfv">1.0</span></div>
      <div class="row">{{ t.div }} <input type="range" id="div" min="0" max="1" value="0.6" step="0.1"><span id="divv">0.6</span></div>
      <button id="go" style="margin-top:10px">{{ t.go }}</button>
    </div>
  </div>
  <div class="panel">
    <h3 id="hint">{{ t.hint }}</h3>
    <div class="grid" id="grid"></div>
  </div>
</div>
<script>
const TAGS = {{ tags|tojson }};
const LANG = {{ lang|tojson }};
const S = {{ js|tojson }};
const params = new URLSearchParams(location.search);
const preset = (params.get('tags') || '{{ preset }}').split(',').filter(Boolean);
const chips = document.getElementById('chips');
const selected = new Set(preset);
if (params.get('airing') === '1') document.getElementById('airing').checked = true;
if (params.get('kind')) document.getElementById('kind').value = params.get('kind');
TAGS.forEach(t => {
  const el = document.createElement('div');
  el.className = 'chip' + (selected.has(t.tag) ? ' on' : '');
  el.textContent = t.tag;
  el.onclick = () => {
    if (selected.has(t.tag)) { selected.delete(t.tag); el.classList.remove('on'); }
    else { selected.add(t.tag); el.classList.add('on'); }
  };
  chips.appendChild(el);
});
['n','wq','wh','wf','div'].forEach(id => {
  const el = document.getElementById(id), out = document.getElementById(id+'v');
  el.oninput = () => out.textContent = (id==='n') ? el.value : parseFloat(el.value).toFixed(1);
});
async function run() {
  const hint = document.getElementById('hint');
  hint.textContent = S.working;
  const p = new URLSearchParams({
    tags: [...selected].join(','),
    kind: document.getElementById('kind').value,
    airing: document.getElementById('airing').checked ? '1' : '0',
    n: document.getElementById('n').value,
    wq: document.getElementById('wq').value,
    wh: document.getElementById('wh').value,
    wf: document.getElementById('wf').value,
    div: document.getElementById('div').value,
  });
  const r = await fetch('/api/recommend?' + p);
  const data = await r.json();
  hint.textContent = S.result.replace('{tags}', [...selected].join(LANG === 'zh' ? '、' : ', ') || '-').replace('{n}', data.items.length);
  const grid = document.getElementById('grid');
  grid.innerHTML = data.items.map(x => `
    <div class="card">
      <div class="cover">${x.cover ? `<img src="${x.cover}" loading="lazy" onerror="this.remove()">` : (x.name||'?')[0]}</div>
      <div class="body">
        <div class="title">${x.name}</div>
        <div class="meta">
          <span class="badge">${LANG === 'zh' ? x.type : x.type_en}</span>${x.airing ? `<span class="badge">${S.airing_badge}</span>` : ''}
          ${x.date || x.season || ''} · ${x.score ? x.score.toFixed(1) : '—'} ${LANG === 'zh' ? '分' : 'pts'} (${x.votes} ${S.votes})
        </div>
        <div>${x.tags.map(t => `<span class="tag">${t}</span>`).join('')}</div>
        <div class="reason">${S.reason}: ${x.reason}</div>
      </div>
    </div>`).join('');
}
document.getElementById('go').onclick = run;
run();
</script></body></html>"""


@app.route("/")
def home():
    lang = request.args.get("lang", "zh")
    if lang not in STRINGS:
        lang = "zh"
    preset = request.args.get("tags", "异世界" if lang == "zh" else "异世界")
    return render_template_string(PAGE, t=STRINGS[lang], lang=lang, tags=tags, stats=stats,
                                  preset=preset, js=STRINGS[lang])


@app.route("/api/recommend")
def api_recommend():
    tags_sel = [t for t in (request.args.get("tags") or "").split(",") if t]
    kind = request.args.get("kind", "anime")
    airing_only = request.args.get("airing") == "1"
    if kind == "book":          # books have no airing schedule
        airing_only = False
    n = max(1, min(int(request.args.get("n", 12)), 30))
    wq = float(request.args.get("wq", 1.0))
    wh = float(request.args.get("wh", 0.6))
    wf = float(request.args.get("wf", 1.0))
    div = float(request.args.get("div", 0.6))
    res = recommend(tags_sel, kind, airing_only, n, wq, wh, wf, lam=max(0.0, min(1.0, 1 - div)))
    return jsonify({"items": res, "count": len(res)})


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Bangumi recommender (Flask)")
    ap.add_argument("--host", default="127.0.0.1",
                    help="127.0.0.1 = local only; 0.0.0.0 = reachable from the LAN")
    ap.add_argument("--port", type=int, default=5000)
    a = ap.parse_args()
    app.run(host=a.host, port=a.port, debug=False, threaded=True)
