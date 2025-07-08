from flask import Flask, request, jsonify
import fitz  # PyMuPDF
from openai import OpenAI
import os
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()  # ✅ Add this to load .env variables
app = Flask(__name__)
CORS(app)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/upload", methods=["POST"])
def upload_pdf():
    file = request.files.get("pdf")
    if not file:
        return jsonify({"error": "No PDF uploaded"}), 400

    # Extract text from PDF
    doc = fitz.open(stream=file.read(), filetype="pdf")
    full_text = ""
    for page in doc:
        full_text += page.get_text()

    # Send to OpenAI for summarization
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You summarize academic documents clearly and concisely."},
                {"role": "user", "content": f"Summarize this document:\n{full_text}"}
            ]
        )
        summary = response.choices[0].message.content
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    return "StudySage backend is running."

if __name__ == "__main__":
    app.run(debug=True)
