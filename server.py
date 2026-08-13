from flask import Flask, request, send_file, jsonify
from gtts import gTTS
from gtts.lang import tts_langs
import io
import os
import hashlib

app = Flask(__name__)

SECRET = os.environ.get("APP_SECRET", "meri-tts-2024")

audio_cache = {}

@app.route("/ping", methods=["GET"])
def ping():
    supported = list(tts_langs().keys())
    return jsonify({
        "status": "ok",
        "service": "Meri TTS",
        "amharic_supported": "am" in supported,
        "supported_langs": supported
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

    cache_key = hashlib.md5(f"{lang}:{text}".encode("utf-8")).hexdigest()

    if cache_key not in audio_cache:

        # Try requested language first
        # If it fails try fallback chain
        lang_chain = []

        if lang in ("am", "am-ET"):
            lang_chain = ["am", "en"]
        else:
            lang_chain = [lang, "en"]

        audio_bytes = None
        last_error = None

        for try_lang in lang_chain:
            try:
                tts = gTTS(text=text, lang=try_lang, slow=False)
                buffer = io.BytesIO()
                tts.write_to_fp(buffer)
                buffer.seek(0)
                audio_bytes = buffer.getvalue()
                break  # success — stop trying
            except Exception as e:
                last_error = str(e)
                continue  # try next language in chain

        if audio_bytes is None:
            return jsonify({"error": f"All TTS attempts failed: {last_error}"}), 500

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
