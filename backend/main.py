from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import fitz  # PyMuPDF
import json
import hashlib
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

# ================== Setup ==================
load_dotenv()
app = Flask(__name__)

# ================== CORS ==================
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

CORS(app, resources={
    r"/*": { 
        "origins": [
            FRONTEND_ORIGIN,
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    }
})


# ================== OpenAI ==================
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

client = OpenAI(api_key=OPENAI_KEY)

print("Backend booted")
print("AI Model currently being used for this project:", MODEL_NAME)

# ================== Caches ==================
summary_cache = {}
flashcard_cache = {}
quiz_cache = {}

# ================== Helpers ==================
def compute_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def chunk_text(text: str, max_chars: int = 5000):
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]

def get_response_text(resp) -> str:
    try:
        for item in resp.output:
            if hasattr(item, "content"):
                for block in item.content:
                    if hasattr(block, "text"):
                        return block.text
    except Exception:
        pass
    return ""

def extract_json_array(text: str):
    try:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            return json.loads(text[start:end + 1])
    except Exception:
        pass
    return []

# ================== Health ==================
@app.get("/")
def health():
    return {"status": "ok"}, 200

@app.get("/diag")
def diag():
    return {"has_key": bool(OPENAI_KEY), "model": MODEL_NAME}

# ================== Upload / Summary ==================
@app.route("/upload", methods=["POST"])
def upload_pdf():
    try:
        file = request.files.get("pdf")
        if not file:
            return jsonify({"error": "No PDF uploaded"}), 400

        file_bytes = file.read()
        file_hash = compute_hash(file_bytes)

        if file_hash in summary_cache:
            return jsonify({"summary": summary_cache[file_hash]})

        # Extract text
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = "".join(page.get_text() for page in doc)

        if not text.strip():
            return jsonify({"error": "PDF text is empty"}), 400

        # ================== FAST PATH ==================
        if len(text) < 25_000:
            print("⚡ Using single-call summary")

            resp = client.responses.create(
                model=MODEL_NAME,
                input=(
                    "Summarize this section in 5-6 sentences. "
                    "Focus only on the main ideas. "
                    "Do NOT include examples, lists, or headings. "
                    "Use plain text only:\n\n"

                    + text
                ),
                max_output_tokens=300
            )

            summary = get_response_text(resp).strip()
            summary_cache[file_hash] = summary
            return jsonify({"summary": summary})

        # ================== LARGE PDF PATH ==================
        print("🐢 Large PDF detected — using parallel chunking")

        chunks = chunk_text(text)
        partials = []

        def summarize_chunk(chunk):
            resp = client.responses.create(
                model=MODEL_NAME,
                input=(
                    "Summarize this section in 2–3 short sentences. "
                    "Focus only on the main ideas. "
                    "Do NOT include examples, lists, headings, or definitions. "
                    "Use plain text only:\n\n" + chunk
                ),
                max_output_tokens=120
            )
            return get_response_text(resp).strip()

        total = len(chunks)
        completed = 0

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(summarize_chunk, c) for c in chunks]

            for future in as_completed(futures):
                completed += 1
                try:
                    result = future.result()
                    if result:
                        partials.append(result)
                except Exception as e:
                    print("❌ Chunk failed:", e)

                print(f"🧩 Completed {completed}/{total} chunks")


        if not partials:
            return jsonify({"error": "Failed to generate summary"}), 500

        # Combine partial summaries
        final_resp = client.responses.create(
            model=MODEL_NAME,
            input=(
                "Combine the following summaries into ONE concise overview of the document. "
                "Limit the final summary to about 150–250 words total. "
                "Focus on high-level concepts only. "
                "Do NOT include headings, bullet points, or formatting. "
                "Use plain text paragraphs:\n\n"
                + "\n\n".join(partials)
            ),
            max_output_tokens=350
        )

        summary = get_response_text(final_resp).strip()
        summary_cache[file_hash] = summary
        return jsonify({"summary": summary})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ================== Flashcards ==================
@app.route("/flashcards", methods=["POST"])
def generate_flashcards():
    try:
        data = request.get_json() or {}
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
        cards = json.loads(content) if content.strip().startswith("[") else extract_json_array(content)
        flashcard_cache[key] = cards
        return jsonify({"flashcards": cards})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ================== Quiz ==================
@app.route("/quiz", methods=["POST"])
def generate_quiz():
    try:
        data = request.get_json() or {}
        text = data.get("text", "")
        if not text:
            return jsonify({"error": "No input text provided"}), 400

        key = compute_hash(text.encode())
        if key in quiz_cache:
            return jsonify({"quiz": quiz_cache[key]})

        resp = client.responses.create(
            model=MODEL_NAME,
            input=(
                "Generate a 5-question multiple choice quiz from the following text.\n"
                "Each question must be an object with:\n"
                "- 'question': string\n"
                "- 'choices': array of 4 plain answer strings (DO NOT include A/B/C/D or numbering)\n"
                "- 'correct': a single letter 'A', 'B', 'C', or 'D' indicating the correct choice index\n"
                "Return ONLY a valid JSON array. No extra text.\n\n"
                + text
            ),
            max_output_tokens=800
        )

        content = get_response_text(resp)
        quiz = json.loads(content) if content.strip().startswith("[") else extract_json_array(content)
        quiz_cache[key] = quiz
        return jsonify({"quiz": quiz})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ================== Entrypoint ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
