"""本地审核服务：卡片式列表 + 点击卡片弹出二级详情菜单"""
import json

from flask import Flask, jsonify, render_template, request

from .organizer import drafts_path, load_drafts, save_drafts


def create_app(cfg: dict) -> Flask:
    app = Flask(__name__)
    app.config["CFG"] = cfg
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    @app.get("/")
    def index():
        return render_template("review.html")

    @app.get("/api/reports")
    def get_reports():
        day = request.args.get("date", "")
        if not day:
            return jsonify({"error": "缺少 date 参数"}), 400
        p = drafts_path(app.config["CFG"], day)
        if not p.exists():
            return jsonify({"error": f"{day} 暂无草稿，请先执行 process"}), 404
        return jsonify(json.loads(p.read_text(encoding="utf-8")))

    @app.post("/api/reports/<rid>")
    def act(rid: str):
        day = request.args.get("date", "")
        body = request.get_json(force=True, silent=True) or {}
        action = body.get("action")
        if action not in ("approve", "reject", "reset"):
            return jsonify({"error": "action 必须是 approve/reject/reset"}), 400
        drafts = load_drafts(app.config["CFG"], day)
        report = next((r for r in drafts["reports"] if r["id"] == rid), None)
        if report is None:
            return jsonify({"error": f"未找到报告 {rid}"}), 404

        # 人工修改内容（可选，随审核动作一起提交）
        if body.get("title"):
            report["title"] = str(body["title"]).strip()
        if body.get("content"):
            report["content"] = str(body["content"]).strip()
        if body.get("stars") is not None:
            try:
                report["human_stars"] = max(1, min(5, int(body["stars"])))
            except (TypeError, ValueError):
                pass

        if action == "approve":
            report["status"] = "approved"
        elif action == "reject":
            report["status"] = "rejected"
        else:  # reset
            report["status"] = "pending"
            report["human_stars"] = None

        save_drafts(app.config["CFG"], day, drafts)
        return jsonify({"ok": True, "report": report})

    return app


def serve(cfg: dict) -> None:
    app = create_app(cfg)
    host = cfg["review"]["host"]
    port = int(cfg["review"]["port"])
    print(f"审核页面已启动: http://{host}:{port}  （审核完成后 Ctrl+C 退出，再执行 publish）")
    app.run(host=host, port=port, debug=False)
