from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import openai
import fitz
import json
import hashlib

load_dotenv()

app = Flask(__name__)
CORS(app)

openai.api_key = os.getenv("OPENAI_API_KEY")

#Caches 
summary_cache = {}
flashcard_cache = {}
quiz_cache = {}

#JSON fallback extraction 
def extract_json_array(text):
    try:
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
    except Exception as e:
        print("JSON extraction fallback failed:", e)
    return []

#Get file hash for caching 
def compute_pdf_hash(file_bytes):
    return hashlib.sha256(file_bytes).hexdigest()

#PDF Upload and summary 
@app.route("/upload", methods=["POST"])
def upload_pdf():
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
        text = ""
        for page in doc:
            text += page.get_text()

        if not text.strip():
            return jsonify({"error": "PDF text is empty"}), 400

        prompt = (
            "You are a helpful assistant. Summarize the following PDF thoroughly and clearly.\n"
            "- The summary should preserve key ideas, important terminology, and structure.\n"
            "- Do not leave out any major details.\n"
            "- Keep it readable and in paragraph form.\n\n"
            "PDF content:\n" + text
        )

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500
        )

        summary = response['choices'][0]['message']['content'].strip()
        summary_cache[file_hash] = summary
        return jsonify({"summary": summary})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

#Flashcard Generation 
@app.route("/flashcards", methods=["POST"])
def generate_flashcards():
    data = request.get_json()
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

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700
        )

        content = response['choices'][0]['message']['content']
        print("🧠 Flashcard Raw Output:\n", content)

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

#Quiz Generation 
@app.route("/quiz", methods=["POST"])
def generate_quiz():
    data = request.get_json()
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

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800
        )

        content = response['choices'][0]['message']['content']
        print("🧠 Quiz Raw Output:\n", content)

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))