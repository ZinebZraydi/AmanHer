# AmanHer — Integrated Safety App

AI-powered sound detection integrated into the AmanHer web application.

---

## Project Structure

```
amanher_integrated/
├── server.py                  ← Flask backend (run this)
├── requirements.txt
├── .env.example               ← copy to .env and fill in secrets
│
├── safety_monitor/            ← AI detection engine
│   ├── config.py              ← keywords, contacts, timeouts
│   ├── core/
│   │   ├── voice_detector.py  ← microphone + speech recognition
│   │   └── alert_manager.py   ← state machine
│   └── utils/
│       ├── notifier.py        ← SMS / email dispatch
│       ├── location.py        ← GPS / IP geolocation
│       └── logger.py
│
└── frontend/                  ← AmanHer web UI
    ├── index.html
    ├── css/
    │   └── sound_detection.css  ← new UI styles
    ├── js/
    │   └── sound_detection.js   ← WebSocket client + toggle logic
    └── pages/
```

---

## Setup & Run

### 1 — Install system dependency (microphone)

**macOS:**
```bash
brew install portaudio
```

**Ubuntu / Debian:**
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
```

**Windows:** No extra step needed.

### 2 — Install Python dependencies

```bash
cd amanher_integrated
pip install -r requirements.txt
```

### 3 — Configure secrets (optional)

```bash
cp .env.example .env
# Edit .env with your contact details, Twilio/email credentials
```

### 4 — Run the app

```bash
python server.py
```

Then open **http://localhost:5000** in your browser.

---

## How the Integration Works

```
Browser (AmanHer UI)
        │
        │  WebSocket (Socket.IO)
        │◄──────────────────────────────────────────┐
        │                                           │
        │  REST API                                 │
        ├──POST /api/detection/toggle──►  Flask     │
        │                               Server      │
        │                                  │        │
        │                          VoiceDetector    │
        │                          (background      │
        │                           thread)         │
        │                               │           │
        │                    keyword    │           │
        │                    detected   ▼           │
        │                          on_dangerous_    │
        │                          sound_detected() │
        │                               │           │
        │                          socketio.emit────┘
        │                          ("alert", ...)
        │
        ▼
   Sound alert overlay shown in browser
   + SOS notification sent to emergency contacts
```

### Flow summary

1. User opens **Profile page** → toggles **"Détection sonore IA"** ON
2. Browser sends `POST /api/detection/toggle { active: true }` to Flask
3. Flask starts `VoiceDetector` in a background thread
4. VoiceDetector continuously listens to the microphone
5. When an emergency keyword is heard (help, sos, au secours…):
   - Server emits `alert` event via WebSocket
   - Browser shows the **Sound Alert Overlay** with location + options
   - Server dispatches SMS/email to emergency contacts (if configured)
   - User can press **"Envoyer SOS"** to also trigger the manual SOS

---

## Customising Keywords

Edit `safety_monitor/config.py`:

```python
EMERGENCY_KEYWORDS = [
    "help",
    "sos",
    "danger",
    "emergency",
    "au secours",
    "socorro",
    # add your own…
]
```

---

## Enabling SMS / Email Alerts

In `.env`:
```env
# Twilio SMS
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_PHONE=+1234567890

# Email
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your_app_password
```

In `safety_monitor/config.py`:
```python
SEND_SMS   = True
SEND_EMAIL = True
```
