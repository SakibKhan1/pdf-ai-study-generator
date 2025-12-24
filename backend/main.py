from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import fitz  # PyMuPDF
import json
import hashlib
import traceback
from openai import OpenAI

# ================== Setup ==================
load_dotenv()

app = Flask(__name__)

# ================== Debug Logger ==================
def debug_log(label, value):
    print("\n" + "=" * 20)
    print(label)
    print("-" * 20)
    try:
        print(value)
    except Exception:
        print("<<UNPRINTABLE>>")
    print("=" * 20 + "\n")

# ================== CORS ==================
DEBUG_ALLOW_ALL = os.getenv("DEBUG_ALLOW_ALL_ORIGINS", "0") == "1"
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

if DEBUG_ALLOW_ALL:
    CORS(app)
else:
    CORS(app, resources={
        r"/*": {
            "origins": [
                FRONTEND_ORIGIN,
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                r"^https://.*\.vercel\.app$",
            ]
        }
    })

# ================== OpenAI ==================
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

debug_log("OPENAI KEY EXISTS", bool(OPENAI_KEY))
debug_log("MODEL NAME", MODEL_NAME)

client = OpenAI(api_key=OPENAI_KEY)

print("🚀 Backend booted")

# ================== In-memory caches ==================
summary_cache = {}
flashcard_cache = {}
quiz_cache = {}

# ================== Helpers ==================
def compute_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def chunk_text(text: str, max_chars: int = 2500):
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]

def preflight_ok():
    return ("", 200)

def extract_json_array(text: str):
    try:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            return json.loads(text[start:end + 1])
    except Exception as e:
        debug_log("JSON EXTRACT ERROR", e)
    return []

def get_response_text(resp) -> str:
    """
    DO NOT TRUST RESPONSE SHAPE — LOG EVERYTHING
    """
    debug_log("RAW RESPONSE OBJECT", resp)

    if hasattr(resp, "output"):
        debug_log("RESP.OUTPUT", resp.output)

        if resp.output:
            block = resp.output[0]
            debug_log("RESP.OUTPUT[0]", block)

            if hasattr(block, "content"):
                debug_log("BLOCK.CONTENT", block.content)

                if block.content:
                    piece = block.content[0]
                    debug_log("BLOCK.CONTENT[0]", piece)

                    if hasattr(piece, "text"):
                        return piece.text

    return ""

# ================== Health ==================
@app.get("/")
def health():
    return {"status": "ok"}, 200

@app.get("/diag")
def diag():
    return {
        "has_key": bool(OPENAI_KEY),
        "model": MODEL_NAME
    }

# ================== Upload / Summary ==================
@app.route("/upload", methods=["POST", "OPTIONS"])
def upload_pdf():
    if request.method == "OPTIONS":
        return preflight_ok()

    try:
        file = request.files.get("pdf")
        if not file:
            return jsonify({"error": "No PDF uploaded"}), 400

        file_bytes = file.read()
        file_hash = compute_hash(file_bytes)

        debug_log("PDF BYTES SIZE", len(file_bytes))
        debug_log("PDF HASH", file_hash)

        if file_hash in summary_cache:
            return jsonify({"summary": summary_cache[file_hash]})

        # Extract text
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = "".join(page.get_text() for page in doc)

        debug_log("EXTRACTED TEXT LENGTH", len(text))
        debug_log("TEXT PREVIEW", text[:500])

        if not text.strip():
            return jsonify({"error": "PDF text is empty"}), 400

        chunks = chunk_text(text)
        debug_log("TOTAL CHUNKS", len(chunks))

        partials = []

        for i, chunk in enumerate(chunks):
            debug_log(f"CHUNK {i+1} LENGTH", len(chunk))
            debug_log(f"CHUNK {i+1} PREVIEW", chunk[:300])

            resp = client.responses.create(
                model=MODEL_NAME,
                input=(
                    "Summarize this section of a document clearly and concisely, "
                    "preserving important details:\n\n" + chunk
                ),
                max_output_tokens=400
            )

            part = get_response_text(resp)
            debug_log("EXTRACTED PART RAW", repr(part))

            part = part.strip()
            if part:
                partials.append(part)

        debug_log("PARTIAL SUMMARIES COUNT", len(partials))

        if not partials:
            debug_log("SUMMARY FAILURE", {
                "chunks": len(chunks),
                "partials": partials
            })
            return jsonify({"error": "Failed to generate summary"}), 500

        # Combine summaries
        final_resp = client.responses.create(
            model=MODEL_NAME,
            input=(
                "Combine the following partial summaries into one clear, cohesive final summary:\n\n"
                + "\n\n".join(partials)
            ),
            max_output_tokens=800
        )

        summary = get_response_text(final_resp).strip()
        debug_log("FINAL SUMMARY", summary)

        summary_cache[file_hash] = summary
        return jsonify({"summary": summary})

    except Exception as e:
        print("❌ EXCEPTION IN /upload")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ================== Flashcards ==================
@app.route("/flashcards", methods=["POST", "OPTIONS"])
def generate_flashcards():
    if request.method == "OPTIONS":
        return preflight_ok()

    try:
        data = request.get_json(silent=True) or {}
        text = data.get("text", "")

        if not text:
            return jsonify({"error": "No input text provided"}), 400

        key = compute_hash(text.encode())
        if key in flashcard_cache:
            return jsonify({"flashcards": flashcard_cache[key]})

        resp = client.responses.create(
            model=MODEL_NAME,
            input=(
                "Generate 5 flashcards from the following text. "
                "Each flashcard must be a JSON object with 'question' and 'answer'. "
                "Return ONLY a JSON array.\n\n" + text
            ),
            max_output_tokens=700
        )

        content = get_response_text(resp)
        debug_log("FLASHCARD RAW TEXT", content)

        cards = json.loads(content) if content.strip().startswith("[") else extract_json_array(content)
        flashcard_cache[key] = cards
        return jsonify({"flashcards": cards})

    except Exception as e:
        print("❌ EXCEPTION IN /flashcards")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ================== Quiz ==================
@app.route("/quiz", methods=["POST", "OPTIONS"])
def generate_quiz():
    if request.method == "OPTIONS":
        return preflight_ok()

    try:
        data = request.get_json(silent=True) or {}
        text = data.get("text", "")

        if not text:
            return jsonify({"error": "No input text provided"}), 400

        key = compute_hash(text.encode())
        if key in quiz_cache:
            return jsonify({"quiz": quiz_cache[key]})

        resp = client.responses.create(
            model=MODEL_NAME,
            input=(
                "Generate a 5-question multiple choice quiz from the following text. "
                "Each question must have 'question', 'choices', and 'correct' (A/B/C/D). "
                "Return ONLY a JSON array.\n\n" + text
            ),
            max_output_tokens=800
        )

        content = get_response_text(resp)
        debug_log("QUIZ RAW TEXT", content)

        quiz = json.loads(content) if content.strip().startswith("[") else extract_json_array(content)
        quiz_cache[key] = quiz
        return jsonify({"quiz": quiz})

    except Exception as e:
        print("❌ EXCEPTION IN /quiz")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ================== Entrypoint ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
