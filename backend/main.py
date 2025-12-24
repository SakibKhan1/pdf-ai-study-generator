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
# Flip this to 1 while debugging preflight issues.
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
    k = os.getenv("OPENAI_API_KEY")
    return {
        "has_key": bool(k),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "frontend_origin": FRONTEND_ORIGIN,
        "debug_allow_all": DEBUG_ALLOW_ALL,
    }, 200

# ========= OpenAI =========
# ========= OpenAI =========
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

print("Backend booted")
print("OpenAI model in use:", MODEL_NAME)


# ========= In-memory caches =========
summary_cache = {}
flashcard_cache = {}
quiz_cache = {}

# ========= Helpers =========
def extract_json_array(text: str):
    try:
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
    except Exception as e:
        print("JSON extraction fallback failed:", e)
    return []

def compute_pdf_hash(file_bytes: bytes):
    return hashlib.sha256(file_bytes).hexdigest()

def preflight_ok():
    """Return a fast OK for preflight and log details."""
    print(f"↪️  Preflight OPTIONS {request.path} from Origin={request.headers.get('Origin')}")
    # Flask-CORS will add the correct CORS headers; we just return OK.
    return ("", 200)

def log_req(tag):
    print(f"➡️  {tag}: {request.method} {request.path} Origin={request.headers.get('Origin')}")

# ========= Routes =========
# Upload -> Summary
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

        prompt = (
            "You are a helpful assistant. Summarize the following PDF thoroughly and clearly.\n"
            "- Preserve key ideas, important terminology, and structure.\n"
            "- Do not leave out any major details.\n"
            "- Keep it readable and in paragraph form.\n\n"
            "PDF content:\n" + text
        )

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=1500
        )
        summary = response.choices[0].message.content.strip()
        summary_cache[file_hash] = summary
        return jsonify({"summary": summary})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Flashcards
@app.route("/flashcards", methods=["POST", "OPTIONS"])
def generate_flashcards():
    if request.method == "OPTIONS":
        return preflight_ok()

    log_req("FLASHCARDS")
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No input text provided"}), 400

    summary_hash = hashlib.sha256(text.encode()).hexdigest()
    if summary_hash in flashcard_cache:
        print("✅ Using cached flashcards")
        return jsonify({"flashcards": flashcard_cache[summary_hash]})

    try:
        prompt = (
            "Generate 5 flashcards from the following text. "
            "Each flashcard should be a JSON object with a 'question' and 'answer'. "
            "Return a JSON array of these objects ONLY. Do not add explanations or formatting.\n\nText:\n" + text
        )

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=700
        )

        content = response.choices[0].message.content
        try:
            flashcards = json.loads(content)
        except Exception:
            flashcards = extract_json_array(content)

        if not isinstance(flashcards, list):
            raise ValueError("Invalid flashcard format returned.")

        flashcard_cache[summary_hash] = flashcards
        return jsonify({"flashcards": flashcards})

    except Exception as e:
        return jsonify({"error": f"Flashcard generation failed: {str(e)}"}), 500

# Quiz
@app.route("/quiz", methods=["POST", "OPTIONS"])
def generate_quiz():
    if request.method == "OPTIONS":
        return preflight_ok()

    log_req("QUIZ")
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No input text provided"}), 400

    summary_hash = hashlib.sha256(text.encode()).hexdigest()
    if summary_hash in quiz_cache:
        print("✅ Using cached quiz")
        return jsonify({"quiz": quiz_cache[summary_hash]})

    try:
        prompt = (
            "Generate a 5-question multiple choice quiz from the following text. "
            "Each question should be an object with 'question', 'choices', and 'correct' (A/B/C/D). "
            "Return a JSON array like this ONLY:\n"
            "[{\"question\": ..., \"choices\": [...], \"correct\": \"A\"}, ...]\n\nText:\n" + text
        )

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=800
        )

        content = response.choices[0].message.content
        try:
            quiz = json.loads(content)
        except Exception:
            quiz = extract_json_array(content)

        if not isinstance(quiz, list):
            raise ValueError("Invalid quiz format returned.")

        quiz_cache[summary_hash] = quiz
        return jsonify({"quiz": quiz})

    except Exception as e:
        return jsonify({"error": f"Quiz generation failed: {str(e)}"}), 500

# ========= Entrypoint =========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
