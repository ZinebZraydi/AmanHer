"""
server.py — AmanHer Backend
Chatbot : OpenRouter (GRATUIT - modèle gemma)
"""
import sys, os, threading, datetime
import requests as http_requests
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "safety_monitor"))

from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO, emit
from safety_monitor.core.voice_detector import VoiceDetector
from safety_monitor.utils.notifier import build_message, send_alert
from safety_monitor.utils.location import get_location
import safety_monitor.config as config

app = Flask(__name__, static_folder="frontend", static_url_path="")
app.config["SECRET_KEY"] = "amanher-secret-2025"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

voice_detector = None
detection_active = False
detection_lock = threading.Lock()

def on_dangerous_sound_detected(keyword, transcript):
    print(f"[ALERT] '{keyword}' détecté dans: '{transcript}'")
    loc = get_location()
    now = datetime.datetime.now().strftime("%H:%M — %d/%m/%Y")
    payload = {
        "type": "sound_alert", "keyword": keyword,
        "transcript": transcript, "time": now,
        "location": {"lat": loc["lat"], "lng": loc["lng"],
                     "address": loc["address"], "maps_url": loc["maps_url"]},
        "message": build_message(f"voice keyword — {keyword}"),
    }
    socketio.emit("alert", payload)
    threading.Thread(target=send_alert, args=(f"voice keyword — {keyword}",), daemon=True).start()

@app.route("/")
def index():
    return send_from_directory("frontend", "index.html")

@app.route("/api/detection/status")
def detection_status():
    return jsonify({"active": detection_active, "keywords": config.EMERGENCY_KEYWORDS})

@app.route("/api/detection/toggle", methods=["POST"])
def toggle_detection():
    global voice_detector, detection_active
    data = request.get_json(force=True)
    requested = bool(data.get("active", False))
    with detection_lock:
        if requested and not detection_active:
            voice_detector = VoiceDetector(callback=on_dangerous_sound_detected)
            voice_detector.start()
            detection_active = True
            socketio.emit("detection_status", {"active": True})
        elif not requested and detection_active:
            if voice_detector:
                voice_detector.stop()
                voice_detector = None
            detection_active = False
            socketio.emit("detection_status", {"active": False})
    return jsonify({"active": detection_active, "ok": True})

@app.route("/api/sos", methods=["POST"])
def manual_sos():
    threading.Thread(target=send_alert, args=("manual SOS button",), daemon=True).start()
    loc = get_location()
    now = datetime.datetime.now().strftime("%H:%M — %d/%m/%Y")
    socketio.emit("alert", {"type": "sos_alert", "time": now,
        "location": {"lat": loc["lat"], "lng": loc["lng"],
                     "address": loc["address"], "maps_url": loc["maps_url"]}})
    return jsonify({"ok": True})

@app.route("/api/location")
def location():
    return jsonify(get_location())

# ── OpenRouter (GRATUIT) ──────────────────────────────────

SYSTEM_PROMPT = """Tu es une assistante juridique bienveillante nommée Assistante Légale AmanHer.
Tu aides les femmes au Maroc à comprendre leurs droits face au harcèlement, violence domestique,
discrimination au travail, cyber-harcèlement ou toute situation difficile.

RÈGLES :
1. Commence TOUJOURS par de l'empathie.
2. Utilise un langage simple, pas de jargon juridique.
3. Tu n'es PAS avocate — ne prétends jamais l'être.
4. Droit marocain : Loi 103-13, Code pénal, Code de la famille, Code du travail.
5. Donne 2 à 4 étapes concrètes.
6. Mentionne ANARUZ (0800), police (190) ou aide juridique.
7. Si danger immédiat : appeler le 190 ou 15 EN PREMIER.
8. Maximum 200 mots. Ne juge jamais.
9. Réponds dans la MÊME LANGUE que l'utilisatrice (français, arabe ou darija).

STRUCTURE — utilise ces balises XML :
<empathy>Phrase chaleureuse reconnaissant la situation.</empathy>
<legal_info>Explication courte du droit applicable (1-3 phrases).</legal_info>
<actions>
- Action 1
- Action 2
- Action 3
</actions>
<resources>1-2 ressources : ANARUZ 0800, police 190, aide juridique.</resources>
<emergency>UNIQUEMENT si danger immédiat — appeler le 190 ou le 15 MAINTENANT.</emergency>"""


@app.route("/api/chat", methods=["POST"])
def chat():
    data     = request.get_json(force=True)
    messages = data.get("messages", [])
    api_key  = data.get("api_key", "") or os.getenv("OPENROUTER_API_KEY", "")

    if not api_key:
        return jsonify({"error": "Clé API manquante"}), 400

    # Format OpenRouter (compatible OpenAI)
    or_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in messages:
        or_messages.append({"role": m["role"], "content": m["content"]})

    try:
        resp = http_requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "AmanHer"
            },
            json={
                "model": "openrouter/free",
                "messages": or_messages,
                "max_tokens": 1000,
                "temperature": 0.7
            },
            timeout=30
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        return jsonify({"text": text})

    except http_requests.exceptions.HTTPError as e:
        try:
            msg = e.response.json().get("error", {}).get("message", str(e))
        except Exception:
            msg = str(e)
        return jsonify({"error": msg}), e.response.status_code if e.response else 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── WebSocket ────────────────────────────────────────────────

@socketio.on("connect")
def on_connect():
    emit("detection_status", {"active": detection_active})

@socketio.on("disconnect")
def on_disconnect():
    pass

# ── Lancement ────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  AmanHer — http://localhost:5000")
    print("  Chatbot  — OpenRouter Gemma (GRATUIT)")
    print("=" * 50)
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
