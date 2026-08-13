from flask import Flask, request, send_file, jsonify
from gtts import gTTS
from gtts.lang import tts_langs
import io
import os
import hashlib
import threading
import time
import urllib.request

app = Flask(__name__)

SECRET = os.environ.get("APP_SECRET", "meri-tts-2024")
SERVER_URL = os.environ.get("SERVER_URL", "")

audio_cache = {}

# ─────────────────────────────────────────
# SELF-PING — keeps Render free tier alive
# pings own /ping endpoint every 10 minutes
# ─────────────────────────────────────────
def keep_alive():
    while True:
        time.sleep(600)  # wait 10 minutes
        if SERVER_URL:
            try:
                urllib.request.urlopen(f"{SERVER_URL}/ping", timeout=10)
                print(f"[KeepAlive] Pinged {SERVER_URL}/ping successfully")
            except Exception as e:
                print(f"[KeepAlive] Ping failed: {e}")

# Start keep-alive thread when server starts
keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
keep_alive_thread.start()

# ─────────────────────────────────────────
# SUPPORTED LANGUAGES FOR MERI APP
# ─────────────────────────────────────────
MERI_LANGUAGES = {
    "am": "Amharic / አማርኛ",
    "om": "Afaan Oromoo",
    "ti": "Tigrinya / ትግርኛ",
    "so": "Somali / Soomaali",
    "en": "English",
    "sw": "Swahili / Kiswahili",
    "ar": "Arabic / عربي",
}

@app.route("/ping", methods=["GET"])
def ping():
    supported = list(tts_langs().keys())
    meri_supported = {
        code: name
        for code, name in MERI_LANGUAGES.items()
        if code in supported
    }
    return jsonify({
        "status": "ok",
        "service": "Meri TTS ሜሪ",
        "meri_languages": meri_supported,
        "amharic": "am" in supported,
        "oromoo": "om" in supported,
        "tigrinya": "ti" in supported,
    })

@app.route("/languages", methods=["GET"])
def languages():
    supported = list(tts_langs().keys())
    return jsonify({
        "available": {
            code: name
            for code, name in MERI_LANGUAGES.items()
            if code in supported
        }
    })

@app.route("/tts", methods=["POST"])
def synthesize():
    secret = request.headers.get("X-App-Secret", "")
    if secret != SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Send JSON body"}), 400

    text = data.get("text", "").strip()
    lang = data.get("lang", "en")

    if not text:
        return jsonify({"error": "text is empty"}), 400

    if len(text) > 500:
        return jsonify({"error": "text too long"}), 400

    cache_key = hashlib.md5(
        f"{lang}:{text}".encode("utf-8")
    ).hexdigest()

    if cache_key not in audio_cache:

        # Fallback chain — try requested lang first
        # then fall back to English if not supported
        if lang in MERI_LANGUAGES:
            lang_chain = [lang, "en"]
        else:
            lang_chain = ["en"]

        audio_bytes = None
        last_error = None

        for try_lang in lang_chain:
            try:
                tts = gTTS(text=text, lang=try_lang, slow=False)
                buffer = io.BytesIO()
                tts.write_to_fp(buffer)
                buffer.seek(0)
                audio_bytes = buffer.getvalue()
                print(f"[TTS] Success: lang={try_lang} text={text[:30]}")
                break
            except Exception as e:
                last_error = str(e)
                print(f"[TTS] Failed lang={try_lang}: {e}")
                continue

        if audio_bytes is None:
            return jsonify({
                "error": f"All TTS attempts failed: {last_error}"
            }), 500

        audio_cache[cache_key] = audio_bytes

    return send_file(
        io.BytesIO(audio_cache[cache_key]),
        mimetype="audio/mpeg",
        as_attachment=False,
        download_name="speech.mp3"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
