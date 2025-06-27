import requests
import json
import os
import re
import uuid
from datetime import datetime

# 🌐 Server URL
url = "https://3903db0b-96b8-43fb-af8b-a9f198aeb950-00-1r2py597j4b13.riker.replit.dev/save_canvas"

# 🔐 Authorization
headers = {"Authorization": "Bearer Abracadabra"}

# 🎯 Prebuilt Templates
canvas_templates = {
    "Force_HUD": {
        "alignment": "Gray",
        "force_score": 58,
        "active_powers": ["Force Push", "Mind Trick"],
        "moral_trajectory":
        ["used Force on a civilian", "resisted dark influence"]
    },
    "Financial_Summary": {
        "total_credits": 4820000,
        "black_fund": 940000,
        "controlled_shells": 6,
        "last_movement": "Encrypted transfer to Hutt escrow",
        "notes": ["injected capital into CorSec", "bribed customs officials"]
    },
    "Corp_Tiers": {
        "current_rank": "Syndicate Broker",
        "board_seat": False,
        "next_milestone": "Acquire 5% stake in InterGalFed",
        "rivals": ["Luthan Hross", "Kesso Majar"]
    },
    "Black_Ops_Funding": {
        "current_balance": 420000,
        "projects": ["Silent claw", "Droid reprogramming uplink"],
        "last_injection": "from MandalTech bid skimming"
    },
    "Mission_Log": {
        "last_ops": [
            "Raided Zann Consortium spice node",
            "Intercepted Mandalorian scout pod"
        ],
        "failed_ops": ["Bribe Imperial governor"],
        "next_target":
        "Zeltros central exchange"
    },
    "Force_Visions": {
        "vision_type": "Fragmented",
        "content": "A cloaked figure places a kyber shard on a Sith altar.",
        "interpretation": "Dark path intersects with redemption",
        "urgency": "High"
    }
}


def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name.lower())


# 📋 User Input
print("Choose a canvas to save:")
print("0. Manual custom input")
for i, key in enumerate(canvas_templates.keys()):
    print(f"{i + 1}. {key}")

choice = input("Enter a number: ").strip()
character_name = input("Enter your character name: ").strip()
campaign_name = input(
    "Enter campaign name (optional): ").strip() or "Unnamed_Campaign"

try:
    if choice == "0":
        canvas_name = input("Enter canvas name: ").strip()
        raw_data = input("Paste JSON data: ").strip()

        try:
            data_dict = json.loads(raw_data)
        except json.JSONDecodeError as e:
            print("[❌] Invalid JSON input:", e)
            exit()

        canvas_data = data_dict

        if "alignment" not in canvas_data:
            canvas_data["alignment"] = input(
                "Enter alignment (e.g., Gray, Light, Dark): ").strip() or "N/A"

    else:
        index = int(choice) - 1
        canvas_name = list(canvas_templates.keys())[index]
        canvas_data = canvas_templates[canvas_name]

    # 🆔 Generate Canvas ID
    canvas_id = str(uuid.uuid4())

    payload = {
        "id": canvas_id,
        "user": character_name,
        "campaign": campaign_name,
        "canvas": canvas_name,
        "data": canvas_data,
        "meta": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "alignment": canvas_data.get("alignment", "N/A"),
            "entries": 1
        }
    }

    # 📡 Send to server
    response = requests.post(url, json=payload, headers=headers)

    # 💾 Save local JSON
    os.makedirs("static", exist_ok=True)
    safe_name = sanitize_filename(
        f"{character_name}_{campaign_name}_{canvas_name}")
    local_filename = f"static/{safe_name}.json"
    with open(local_filename, "w") as f:
        json.dump(payload, f, indent=2)

    # 📓 Log JSONL entry to HUD log
    with open("hud_log.jsonl", "a") as log_file:
        log_file.write(json.dumps(payload) + "\n")

    # ✅ Final output
    if response.status_code == 200:
        print(f"\n[✅ SAVED] {canvas_name} for {character_name}")
        print(f"🆔 Canvas ID: {canvas_id}")
        print(f"[💾] Local copy: {local_filename}")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"\n[❌ ERROR {response.status_code}] {response.text}")

except (IndexError, ValueError) as e:
    print("[❌] Invalid selection:", e)
