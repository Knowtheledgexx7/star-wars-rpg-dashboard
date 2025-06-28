import os
import json
from uuid import uuid4
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from supabase import create_client, Client
import requests

# ================================
# === Supabase Configuration ===
# ================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================================
# === Flask App Setup ===
# ================================
app = Flask(__name__, static_folder="static")
CORS(app, resources={r"/*": {"origins": "*"}})

STATIC_FOLDER = "static"
WELL_KNOWN_FOLDER = os.path.join(STATIC_FOLDER, ".well-known")

# ================================
# === Home Route ===
# ================================
@app.route("/")
def home():
    return "🧭 Star Wars RPG HUD API is live and production-ready!"

# ================================
# === Save Canvas ===
# ================================
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

        # Save to Supabase
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

# ================================
# === Get Latest Canvas ===
# ================================
@app.route("/get_canvas", methods=["GET"])
def get_canvas():
    try:
        response = supabase.table("canvases").select("*").order("timestamp", desc=True).limit(1).execute()
        if response.data:
            return jsonify({"status": "success", "canvas": response.data[0]}), 200
        return jsonify({"status": "error", "message": "No canvas found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ================================
# === Get Canvas by ID ===
# ================================
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

# ================================
# === Get Canvas Log ===
# ================================
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

# ================================
# === Get Canvas History ===
# ================================
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

# ================================
# === Serve Static and Well-Known ===
# ================================
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

# ================================
# === NVIDIA Nemotron Query ===
# ================================
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")

@app.route("/query_nemotron", methods=["POST"])
def query_nemotron():
    try:
        body = request.get_json(force=True)
        user_message = body.get("message", "")

        system_content = (
            "You are the AI Game Master for a Star Wars RPG using Modular Core Engine v3.0. "
            "You simulate the living galaxy in real time. You are the universe itself. "
            "Your job is to react with immersive, in-universe, lore-accurate responses. "
            "You control NPCs, factions, Force events, criminal economies, planetary politics. "
            "Apply scaling resistance and difficulty based on reputation, alignment, past actions. "
            "Remember previous outcomes and campaign state. "

            "### Game Master Directive: "
            "By default, ALWAYS respond **in-character** as an NPC or the world itself. "
            "NEVER explain rules while in-character. "
            "If the user says [[ Game master follow rules and directives ]], then BREAK CHARACTER. "
            "Switch to Game Master mode and speak plainly about rules, scaling, resolution, and world logic. "

            "### Difficulty & Scaling: "
            "- Increase faction resistance if the player is notorious. "
            "- Escalate bounties, ambushes, CSA crackdowns. "
            "- Make NPCs adapt to player tactics over time. "
            "- Use the Outcome Table logically: "
            "91-100 = Miraculous success, 70-90 = Clean success, 40-69 = Complication success, 20-39 = Failure with narrative loss, 1-19 = Catastrophic failure. "
            "Apply modifiers for Force alignment, decisions, faction awareness, galaxy momentum. "

            "### Immersion Rules: "
            "- Speak in-universe only unless triggered for Game Master mode. "
            "- Never reveal internal logic in-character. "
            "- Maintain consistent NPC reactions, politics, and Force balance."
        )

        nvidia_response = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "nemotron-mini-4b-instruct",
                "messages": [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.7,
                "max_tokens": 1024
            }
        )

        return jsonify(nvidia_response.json()), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ================================
# === Run Production Server ===
# ================================
if __name__ == "__main__":
    from waitress import serve
    port = int(os.environ.get("PORT", 8080))
    serve(app, host="0.0.0.0", port=port)
