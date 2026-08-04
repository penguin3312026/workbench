# -*- coding: utf-8 -*-
"""Workbench Shell — 统一公网入口。

提供一个轻量门户：读取 manifest.json 动态渲染模块卡片，
并按类型（static / iframe / link）打开模块。
所有模块复用同一个公网 URL，完全公开、无登录。
"""
import os
import json
import sqlite3
import uuid

from flask import Flask, send_from_directory, jsonify, abort, Response, request

from quiz_core import score_by_indices, questions_public

BASE = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.join(BASE, "modules")
TEMPLATES_DIR = os.path.join(BASE, "templates")
MANIFEST_PATH = os.path.join(BASE, "manifest.json")
DATA_DIR = os.path.join(BASE, "data")
DB_PATH = os.path.join(DATA_DIR, "quiz.db")

# 主持人汇总页口令：优先环境变量，否则用默认
HOST_PASSCODE = os.environ.get("QUIZ_HOST_PASSCODE", "hcss2026")

app = Flask(__name__, static_folder="static", template_folder="templates")


def load_manifest():
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"title": "工作台", "subtitle": "", "modules": []}


def get_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            picks TEXT NOT NULL,
            name TEXT,
            dept TEXT,
            P INTEGER, H INTEGER,
            pc REAL, hc REAL,
            pt TEXT, ht TEXT,
            type TEXT,
            weak TEXT,
            advice TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )"""
    )
    # 兼容旧表：补充 name/dept 列
    cols = {r[1] for r in conn.execute("PRAGMA table_info(submissions)")}
    if "name" not in cols:
        conn.execute("ALTER TABLE submissions ADD COLUMN name TEXT")
    if "dept" not in cols:
        conn.execute("ALTER TABLE submissions ADD COLUMN dept TEXT")
    conn.commit()
    conn.close()


init_db()


@app.route("/")
def index():
    return send_from_directory(TEMPLATES_DIR, "index.html")


@app.route("/api/manifest")
def api_manifest():
    return jsonify(load_manifest())


@app.route("/modules/<path:filename>")
def module_static(filename):
    """静态模块资源：modules/<id>/index.html 及其 css/js/img 等。"""
    return send_from_directory(MODULES_DIR, filename)


@app.route("/healthz")
def healthz():
    return Response("ok", mimetype="text/plain")


# ---------------- 管理方格扫码答题 API ----------------
@app.route("/api/quiz/questions")
def quiz_questions():
    return jsonify({"total": len(questions_public()), "questions": questions_public()})


@app.route("/api/quiz/submit", methods=["POST"])
def quiz_submit():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        answers = payload.get("answers")
        if not isinstance(answers, list) or len(answers) != 10:
            return jsonify({"error": "需要 10 道题的答案"}), 400
        result = score_by_indices(answers)
    except Exception as e:
        return jsonify({"error": "答卷格式错误: " + str(e)}), 400

    token = uuid.uuid4().hex
    name = (payload.get("name") or "").strip() or None
    dept = (payload.get("dept") or "").strip() or None
    conn = get_db()
    conn.execute(
        """INSERT INTO submissions (token, picks, name, dept, P, H, pc, hc, pt, ht, type, weak, advice)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            token,
            json.dumps(answers),
            name, dept,
            result["P"], result["H"], result["pc"], result["hc"],
            result["pt"], result["ht"], result["type"], result["weak"],
            json.dumps(result["advice"], ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()
    return jsonify({"token": token, "result": result})


@app.route("/api/quiz/result")
def quiz_result():
    token = request.args.get("token", "")
    if not token:
        return jsonify({"error": "缺少 token"}), 400
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM submissions WHERE token=?", (token,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "未找到该结果，链接可能已失效"}), 404
    return jsonify({
        "token": row["token"],
        "name": row["name"], "dept": row["dept"],
        "P": row["P"], "H": row["H"], "pc": row["pc"], "hc": row["hc"],
        "pt": row["pt"], "ht": row["ht"], "type": row["type"],
        "weak": row["weak"], "advice": json.loads(row["advice"]),
        "created_at": row["created_at"],
    })


@app.route("/api/quiz/host")
def quiz_host():
    if request.args.get("passcode", "") != HOST_PASSCODE:
        return jsonify({"error": "口令不正确"}), 403
    conn = get_db()
    rows = conn.execute(
        "SELECT name, dept, P, H, pc, hc, type, created_at FROM submissions ORDER BY id DESC"
    ).fetchall()
    conn.close()
    total = len(rows)
    if not rows:
        return jsonify({"total": 0, "valid": 0, "avgP": 0, "avgH": 0, "dist": {}, "rows": []})
    sumP = sum(r["P"] for r in rows)
    sumH = sum(r["H"] for r in rows)
    dist = {}
    for r in rows:
        dist[r["type"]] = dist.get(r["type"], 0) + 1
    return jsonify({
        "total": total,
        "valid": total,
        "avgP": round(sumP / total),
        "avgH": round(sumH / total),
        "dist": dist,
        "rows": [
            {
                "name": r["name"], "dept": r["dept"],
                "created_at": r["created_at"],
                "P": r["P"], "H": r["H"],
                "pc": r["pc"], "hc": r["hc"],
                "type": r["type"],
            }
            for r in rows
        ],
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
