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
                {"role": "system", "content": "You generate educational flashcards in Q&A format."},
                {"role": "user", "content": f"Generate 5 flashcards from the following text:\n{text}"}
            ]
        )
        flashcards = response.choices[0].message.content
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
                {"role": "system", "content": "You generate multiple-choice quizzes from academic material."},
                {"role": "user", "content": f"Create 3 multiple-choice quiz questions from this text:\n{text}"}
            ]
        )
        quiz = response.choices[0].message.content
        return jsonify({"quiz": quiz})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#validation for if backend running properly 
@app.route("/")
def home():
    return "StudySage backend is running."

if __name__ == "__main__":
    app.run(debug=True)
