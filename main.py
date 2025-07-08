from flask import Flask, request, jsonify
import fitz  # PyMuPDF
from openai import OpenAI
import os
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()  #loads .env variable
app = Flask(__name__) #uses flask here for backend
CORS(app)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/upload", methods=["POST"])
def upload_pdf():
    file = request.files.get("pdf")
    if not file:
        return jsonify({"error": "No PDF uploaded"}), 400

    #extracts text from PDF
    doc = fitz.open(stream=file.read(), filetype="pdf")
    full_text = ""
    for page in doc:
        full_text += page.get_text()

    #send to OpenAI for summarization
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert academic summarizer. Provide detailed and thorough summaries that preserve all key ideas and important details from the original document."
                },
                {
                    "role": "user",
                    "content": f"Summarize this document in a detailed, multi-paragraph format:\n{full_text}"
                }
            ]
        )
        summary = response.choices[0].message.content
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#generates the flashcards from the AI text 
@app.route("/flashcards", methods=["POST"])
def generate_flashcards():
    data = request.json
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an educational assistant. Generate exactly 5 flashcards "
                        "from the user's provided academic text. "
                        "Each flashcard should be in this JSON format:\n\n"
                        "[\n"
                        "  {\"question\": \"...\", \"answer\": \"...\"},\n"
                        "  {\"question\": \"...\", \"answer\": \"...\"},\n"
                        "  ... (5 total)\n"
                        "]\n\n"
                        "Ensure the response is valid JSON. Do not include any explanation or extra text — only output the JSON array."
                    )
                },
                {
                    "role": "user",
                    "content": f"Create 5 flashcards from this content:\n\n{text}"
                }
            ]
        )
        flashcards = response.choices[0].message.content.strip()
        return jsonify({"flashcards": flashcards})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
#generates the quizk from the AI text like flashcards
@app.route("/quiz", methods=["POST"])
def generate_quiz():
    data = request.json
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that generates multiple-choice quiz questions. "
                        "Return exactly 5 questions in valid JSON format. Each question should have: "
                        "`question`, `choices` (list of 4 strings), and `correct` (the correct letter A, B, C, or D). "
                        "Example format:\n"
                        "[\n"
                        "  {\n"
                        '    "question": "What is the capital of France?",\n'
                        '    "choices": ["Paris", "Berlin", "London", "Rome"],\n'
                        '    "correct": "A"\n'
                        "  },\n"
                        "  ...\n"
                        "]"
                    )
                },
                {
                    "role": "user",
                    "content": f"Generate a multiple-choice quiz from the following text:\n{text}"
                }
            ]
        )
        quiz_json = response.choices[0].message.content.strip()
        return jsonify({"quiz": quiz_json})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#validation for if backend running properly 
@app.route("/")
def home():
    return "StudySage backend is running."

if __name__ == "__main__":
    app.run(debug=True)
