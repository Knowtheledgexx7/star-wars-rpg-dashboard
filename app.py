from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from datetime import datetime
from uuid import uuid4
import os
import json

app = Flask(__name__)
CORS(app)

# In-memory storage
latest_canvas = {}
log_history = []

# File paths
log_file = "hud_log.jsonl"
char_file = "characters.jsonl"

# Load history on startup
if os.path.exists(log_file):
    with open(log_file, "r") as f:
        for line in f:
            try:
                log_history.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue


@app.route("/save_canvas", methods=["POST"])
def save_canvas():
    auth_header = request.headers.get("Authorization", "")
    if auth_header != "Bearer Abracadabra":
        return jsonify({"status": "unauthorized"}), 401

    try:
        data = request.get_json(force=True)
        data["id"] = str(uuid4())
        data["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Defaults
        data.setdefault("campaign", "Unknown Campaign")
        data.setdefault("user", "Anonymous")
        data.setdefault("canvas", "Unnamed HUD")
        data.setdefault("meta", {})
        data["meta"].setdefault(
            "alignment",
            data.get("data", {}).get("alignment", "Unknown"))
        data["meta"].setdefault("entries", 1)

        latest_canvas.clear()
        latest_canvas.update(data)
        log_history.append(data)

        with open(log_file, "a") as f:
            f.write(json.dumps(data) + "\n")

        return jsonify({
            "status": "success",
            "message": "Canvas saved",
            "id": data["id"]
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/get_canvas", methods=["GET"])
def get_canvas():
    if log_history:
        latest = max(log_history, key=lambda x: x.get("timestamp", ""))
        return jsonify({"status": "success", "canvas": latest}), 200
    return jsonify({"status": "error", "message": "No canvas found"}), 404


@app.route("/get_canvas_by_id", methods=["GET"])
def get_canvas_by_id():
    canvas_id = request.args.get("id")
    for entry in log_history:
        if entry.get("id") == canvas_id:
            return jsonify({"status": "success", "canvas": entry}), 200
    return jsonify({"status": "error", "message": "Canvas not found"}), 404


@app.route("/get_log", methods=["GET"])
def get_log():
    canvas_filter = request.args.get("canvas")
    user_filter = request.args.get("user")
    align_filter = request.args.get("align")

    filtered = log_history
    if canvas_filter:
        filtered = [e for e in filtered if e.get("canvas") == canvas_filter]
    if user_filter:
        filtered = [e for e in filtered if e.get("user") == user_filter]
    if align_filter:
        filtered = [
            e for e in filtered
            if e.get("meta", {}).get("alignment") == align_filter
        ]

    return jsonify({"status": "success", "log": filtered}), 200


@app.route("/get_canvas_history", methods=["GET"])
def get_canvas_history():
    user = request.args.get("user")
    campaign = request.args.get("campaign")
    canvas = request.args.get("canvas")

    history = [
        e for e in log_history if (not user or e.get("user") == user) and (
            not campaign or e.get("campaign") == campaign) and (
                not canvas or e.get("canvas") == canvas)
    ]
    history.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify({"status": "success", "history": history}), 200


# ✅ Serve Plugin Files (.well-known)
@app.route('/.well-known/<path:filename>')
def serve_well_known(filename):
    return send_from_directory('static/.well-known', filename)


# Optional landing route (can be removed for React-only use)
@app.route("/")
def home():
    return "RPG HUD API is live."


# Dev entrypoint
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
