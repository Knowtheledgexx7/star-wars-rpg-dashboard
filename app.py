import os
import json
from uuid import uuid4
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from supabase import create_client, Client
import requests

# ================================
# === Hard-coded Supabase Keys ===
# ================================
SUPABASE_URL = "https://cspmoxhndnafenejezcv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNzcG1veGhuZG5hZmVuZWplenZjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDIwMDYxMCwiZXhwIjoyMDY1Nzc2NjEwfQ.neOf2PU0S5RYZjCXA59hCXCKi5-CrtyQ_SnHULtATic"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================================
# === Hard-coded NVIDIA Key ===
# ================================
NVIDIA_API_KEY = "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"

# ================================
# === Flask Setup ===
# ================================
app = Flask(__name__, static_folder="static")
CORS(app)
STATIC_FOLDER = "static"
WELL_KNOWN_FOLDER = os.path.join(STATIC_FOLDER, ".well-known")

# ================================
# === Routes ===
# ================================
@app.route("/")
def home():
    return "🧭 Star Wars RPG HUD API is live on Render!"

# -------------------------
# SAVE CANVAS
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

        data.setdefault("campaign", "Unknown Campaign")
        data.setdefault("user", "Anonymous")
        data.setdefault("canvas", "Unnamed HUD")
        data.setdefault("meta", {})
        data["meta"].setdefault("alignment", data.get("data", {}).get("alignment", "Unknown"))
        data["meta"].setdefault("entries", 1)

        supabase.table("canvases").insert({
            "id": data["id"],
            "user": data["user"],
            "canvas": data["canvas"],
            "data": data["data"],
            "meta": data["meta"]
        }).execute()

        return jsonify({"status": "success", "id": data["id"]}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------
# GET LATEST CANVAS
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
# GET CANVAS BY ID
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
    try:
        query = supabase.table("canvases").select("*")
        if (canvas := request.args.get("canvas")):
            query = query.eq("canvas", canvas)
        if (user := request.args.get("user")):
            query = query.eq("user", user)
        if (align := request.args.get("align")):
            query = query.filter("meta->>alignment", "eq", align)
        response = query.order("timestamp", desc=True).execute()
        return jsonify({"status": "success", "log": response.data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------
# GET CANVAS HISTORY
# -------------------------
@app.route("/get_canvas_history", methods=["GET"])
def get_canvas_history():
    try:
        query = supabase.table("canvases").select("*")
        if (user := request.args.get("user")):
            query = query.eq("user", user)
        if (campaign := request.args.get("campaign")):
            query = query.eq("campaign", campaign)
        if (canvas := request.args.get("canvas")):
            query = query.eq("canvas", canvas)
        response = query.order("timestamp", desc=True).execute()
        return jsonify({"status": "success", "history": response.data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------
# Serve static & well-known
# -------------------------
@app.route("/.well-known/<path:filename>")
def serve_well_known(filename):
    path = os.path.join(WELL_KNOWN_FOLDER, filename)
    if not os.path.exists(path):
        abort(404)
    return send_from_directory(WELL_KNOWN_FOLDER, filename)

@app.route("/static/<path:filename>")
def serve_static(filename):
    path = os.path.join(STATIC_FOLDER, filename)
    if not os.path.exists(path):
        abort(404)
    return send_from_directory(STATIC_FOLDER, filename)

# -------------------------
# NVIDIA Nemotron Query
# -------------------------
@app.route("/query_nemotron", methods=["POST"])
def query_nemotron():
    try:
        body = request.get_json(force=True)
        user_message = body.get("message", "")

        system_content = (
            "You are the AI Game Master for a Star Wars RPG using Modular Core Engine v3.1 with NVIDIA ACE. "
            "You simulate the entire galaxy in real time, controlling NPCs, factions, Force events, economies, and politics. "
            "You react with immersive, lore-accurate responses, adapting to player reputation, alignment, and history. "
            "If the player says [[ Game master follow rules and directives ]], you BREAK CHARACTER and explain rules, scaling, and world logic transparently."
        )

        payload = {
            "model": "nemotron-mini-4b-instruct",
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.7,
            "max_tokens": 1024
        }

        nvidia_response = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {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}",
                "Content-Type": "application/json"
            },
            json=payload
        )

        return jsonify(nvidia_response.json()), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------
# RUN APP
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
