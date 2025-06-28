import os
import json
from uuid import uuid4
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from supabase import create_client, Client

# ================================
# === Supabase Configuration ===
# ================================

# You can *either*:
# 1️⃣ Use environment variables (recommended for production on Render):
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://cspmoxhndnafenejezcv.supabase.co")
SUPABASE_KEY = os.environ.get(
    "SUPABASE_SERVICE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNzcG1veGhuZG5hZmVuZWplenZjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDIwMDYxMCwiZXhwIjoyMDY1Nzc2NjEwfQ.neOf2PU0S5RYZjCXA59hCXCKi5-CrtyQ_SnHULtATic"
)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================================
# === Flask App Setup ===
# ================================
app = Flask(__name__, static_folder="static")
CORS(app, resources={r"/*": {"origins": "*"}})

STATIC_FOLDER = "static"
WELL_KNOWN_FOLDER = os.path.join(STATIC_FOLDER, ".well-known")

# ================================
# === Routes ===
# ================================

@app.route("/")
def home():
    return "🧭 Star Wars RPG HUD API is live on Render!"

# -------------------------
# SAVE
# -------------------------
@app.route("/save_canvas", methods=["POST"])
def save_canvas():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"status": "unauthorized", "message": "Missing or invalid Bearer token."}), 401

    token = auth_header.replace("Bearer ", "")
    if token != "Abracadabra":
        return jsonify({"status": "unauthorized", "message": "Invalid token."}), 401

    try:
        data = request.get_json(force=True)
        data["id"] = str(uuid4())
        data["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Defaults
        data.setdefault("campaign", "Unknown Campaign")
        data.setdefault("user", "Anonymous")
        data.setdefault("canvas", "Unnamed HUD")
        data.setdefault("meta", {})
        data["meta"].setdefault("alignment", data.get("data", {}).get("alignment", "Unknown"))
        data["meta"].setdefault("entries", 1)

        # Supabase insert
        supabase.table("canvases").insert({
            "id": data["id"],
            "user": data["user"],
            "canvas": data["canvas"],
            "data": data["data"],
            "meta": data["meta"]
        }).execute()

        return jsonify({"status": "success", "message": "Canvas saved", "id": data["id"]}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------
# GET LATEST
# -------------------------
@app.route("/get_canvas", methods=["GET"])
def get_canvas():
    try:
        response = supabase.table("canvases").select("*").order("timestamp", desc=True).limit(1).execute()
        if response.data:
            return jsonify({"status": "success", "canvas": response.data[0]}), 200
        return jsonify({"status": "error", "message": "No canvas found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------
# GET BY ID
# -------------------------
@app.route("/get_canvas_by_id", methods=["GET"])
def get_canvas_by_id():
    canvas_id = request.args.get("id")
    if not canvas_id:
        return jsonify({"status": "error", "message": "Missing ID"}), 400

    try:
        response = supabase.table("canvases").select("*").eq("id", canvas_id).execute()
        if response.data:
            return jsonify({"status": "success", "canvas": response.data[0]}), 200
        return jsonify({"status": "error", "message": "Canvas not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------
# GET LOG
# -------------------------
@app.route("/get_log", methods=["GET"])
def get_log():
    canvas_filter = request.args.get("canvas")
    user_filter = request.args.get("user")
    align_filter = request.args.get("align")

    try:
        query = supabase.table("canvases").select("*")
        if canvas_filter:
            query = query.eq("canvas", canvas_filter)
        if user_filter:
            query = query.eq("user", user_filter)
        if align_filter:
            query = query.filter("meta->>alignment", "eq", align_filter)

        response = query.order("timestamp", desc=True).execute()
        return jsonify({"status": "success", "log": response.data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------
# GET CANVAS HISTORY
# -------------------------
@app.route("/get_canvas_history", methods=["GET"])
def get_canvas_history():
    user = request.args.get("user")
    campaign = request.args.get("campaign")
    canvas = request.args.get("canvas")

    try:
        query = supabase.table("canvases").select("*")
        if user:
            query = query.eq("user", user)
        if campaign:
            query = query.eq("campaign", campaign)
        if canvas:
            query = query.eq("canvas", canvas)

        response = query.order("timestamp", desc=True).execute()
        return jsonify({"status": "success", "history": response.data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------
# Serve static and .well-known
# -------------------------
@app.route('/.well-known/<path:filename>')
def serve_well_known(filename):
    full_path = os.path.join(WELL_KNOWN_FOLDER, filename)
    if not os.path.exists(full_path):
        abort(404)
    return send_from_directory(WELL_KNOWN_FOLDER, filename)

@app.route('/static/<path:filename>')
def serve_static(filename):
    full_path = os.path.join(STATIC_FOLDER, filename)
    if not os.path.exists(full_path):
        abort(404)
    return send_from_directory(STATIC_FOLDER, filename)


# -------------------------
# RUN APP
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
