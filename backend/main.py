from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
from openai import OpenAI
import fitz
import json
import hashlib

load_dotenv()

app = Flask(__name__)

# ========= CORS =========
DEBUG_ALLOW_ALL = os.getenv("DEBUG_ALLOW_ALL_ORIGINS", "0") == "1"

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
ALLOWED_ORIGINS = {
    FRONTEND_ORIGIN,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
}
VERCEL_PREVIEW_REGEX = r"^https://.*\.vercel\.app$"

if DEBUG_ALLOW_ALL:
    CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"]}})
else:
    CORS(app, resources={
        r"/*": {
            "origins": list(ALLOWED_ORIGINS) + [VERCEL_PREVIEW_REGEX],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["*", "Content-Type", "Authorization", "X-Requested-With"],
            "expose_headers": ["*"],
            "supports_credentials": False,
        }
    })

# ========= Health / Diag =========
@app.get("/")
def health():
    return {"status": "ok"}, 200

@app.get("/diag")
def diag():
    return {
        "has_key": bool(os.getenv("OPENAI_API_KEY")),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "frontend_origin": FRONTEND_ORIGIN,
        "debug_allow_all": DEBUG_ALLOW_ALL,
    }, 200

# ========= OpenAI =========
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

print("🚀 Backend booted")
print("🤖 OpenAI model in use:", MODEL_NAME)

# ========= In-memory caches =========
summary_cache = {}
flashcard_cache = {}
quiz_cache = {}

# ========= Helpers =========
def extract_json_array(text: str):
    try:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            return json.loads(text[start:end + 1])
    except Exception as e:
        print("JSON extraction fallback failed:", e)
    return []

def compute_pdf_hash(file_bytes: bytes):
    return hashlib.sha256(file_bytes).hexdigest()

def chunk_text(text, max_chars=4000):
    """Split text into safe character-based chunks."""
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]

def preflight_ok():
    return ("", 200)

def log_req(tag):
    print(f"➡️  {tag}: {request.method} {request.path}")

# ========= Routes =========
@app.route("/upload", methods=["POST", "OPTIONS"])
def upload_pdf():
    if request.method == "OPTIONS":
        return preflight_ok()

    log_req("UPLOAD")
    file = request.files.get("pdf")
    if not file:
        return jsonify({"error": "No PDF uploaded"}), 400

    file_bytes = file.read()
    file_hash = compute_pdf_hash(file_bytes)

    if file_hash in summary_cache:
        print("✅ Using cached summary")
        return jsonify({"summary": summary_cache[file_hash]})

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = "".join(page.get_text() for page in doc)

        if not text.strip():
            return jsonify({"error": "PDF text is empty"}), 400

        chunks = chunk_text(text)
        partial_summaries = []

        for i, chunk in enumerate(chunks):
            print(f"🧩 Summarizing chunk {i + 1}/{len(chunks)}")

            chunk_prompt = (
                "Summarize the following section of a document clearly and concisely. "
                "Preserve key ideas and important details.\n\n" + chunk
            )

            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": chunk_prompt}],
                max_completion_tokens=400
            )

            part = response.choices[0].message.content.strip()
            if part:
                partial_summaries.append(part)

        if not partial_summaries:
            return jsonify({"error": "Failed to generate summary"}), 500

        final_prompt = (
            "Combine the following partial summaries into one clear, cohesive final summary:\n\n"
            + "\n\n".join(partial_summaries)
        )

        final_response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": final_prompt}],
            max_completion_tokens=800
        )

        summary = final_response.choices[0].message.content.strip()
        summary_cache[file_hash] = summary
        return jsonify({"summary": summary})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========= Flashcards =========
@app.route("/flashcards", methods=["POST", "OPTIONS"])
def generate_flashcards():
    if request.method == "OPTIONS":
        return preflight_ok()

    log_req("FLASHCARDS")
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No input text provided"}), 400

    key = hashlib.sha256(text.encode()).hexdigest()
    if key in flashcard_cache:
        return jsonify({"flashcards": flashcard_cache[key]})

    try:
        prompt = (
            "Generate 5 flashcards from the following text. "
            "Each flashcard should be a JSON object with 'question' and 'answer'. "
            "Return ONLY a JSON array.\n\n" + text
        )

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=700
        )

        content = response.choices[0].message.content
        flashcards = json.loads(content) if content.strip().startswith("[") else extract_json_array(content)

        flashcard_cache[key] = flashcards
        return jsonify({"flashcards": flashcards})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========= Quiz =========
@app.route("/quiz", methods=["POST", "OPTIONS"])
def generate_quiz():
    if request.method == "OPTIONS":
        return preflight_ok()

    log_req("QUIZ")
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No input text provided"}), 400

    key = hashlib.sha256(text.encode()).hexdigest()
    if key in quiz_cache:
        return jsonify({"quiz": quiz_cache[key]})

    try:
        prompt = (
            "Generate a 5-question multiple choice quiz from the following text. "
            "Each question should have 'question', 'choices', and 'correct' (A/B/C/D). "
            "Return ONLY a JSON array.\n\n" + text
        )

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=800
        )

        content = response.choices[0].message.content
        quiz = json.loads(content) if content.strip().startswith("[") else extract_json_array(content)

        quiz_cache[key] = quiz
        return jsonify({"quiz": quiz})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========= Entrypoint =========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
