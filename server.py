from flask import Flask, request, send_file, jsonify
from gtts import gTTS
import io
import os
import hashlib

app = Flask(__name__)

SECRET = os.environ.get("APP_SECRET", "meri-tts-2024")

# In-memory cache so same phrase is not regenerated
audio_cache = {}

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok", "service": "Meri TTS"})

@app.route("/tts", methods=["POST"])
def synthesize():
    # Check secret header
    secret = request.headers.get("X-App-Secret", "")
    if secret != SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Send JSON body"}), 400

    text = data.get("text", "").strip()
    lang = data.get("lang", "am")

    if not text:
        return jsonify({"error": "text is empty"}), 400

    if len(text) > 500:
        return jsonify({"error": "text too long"}), 400

    # Create cache key
    cache_key = hashlib.md5(f"{lang}:{text}".encode("utf-8")).hexdigest()

    if cache_key not in audio_cache:
        try:
            tts = gTTS(text=text, lang=lang, slow=False)
            buffer = io.BytesIO()
            tts.write_to_fp(buffer)
            buffer.seek(0)
            audio_cache[cache_key] = buffer.getvalue()
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return send_file(
        io.BytesIO(audio_cache[cache_key]),
        mimetype="audio/mpeg",
        as_attachment=False,
        download_name="speech.mp3"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
