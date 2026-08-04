# -*- coding: utf-8 -*-
"""Workbench Shell — 统一公网入口。

提供一个轻量门户：读取 manifest.json 动态渲染模块卡片，
并按类型（static / iframe / link）打开模块。
所有模块复用同一个公网 URL，完全公开、无登录。
"""
import os
import json

from flask import Flask, send_from_directory, jsonify, abort, Response

BASE = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.join(BASE, "modules")
TEMPLATES_DIR = os.path.join(BASE, "templates")
MANIFEST_PATH = os.path.join(BASE, "manifest.json")

app = Flask(__name__, static_folder="static", template_folder="templates")


def load_manifest():
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"title": "工作台", "subtitle": "", "modules": []}


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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
