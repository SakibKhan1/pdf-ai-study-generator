# 📚 PDF AI Study Generator

**PDF AI Study Generator** is a web app that transforms uploaded PDFs into AI-powered study materials including summaries, flashcards, and quizzes. Designed for fast, focused learning, the app makes studying from dense lecture slides, textbook chapters, or research papers more interactive and efficient.

Built with a modern full-stack architecture, the app uses GPT-3.5 to process document content and deliver accurate, structured outputs. It features a clean UI, responsive design, and intelligent caching to minimize unnecessary API usage.

Check out the live app here 👉: https://pdf-ai-study-generator.vercel.app/
Backend: Flask + OpenAI API  
Frontend: React.js + Vercel Hosting  

---

## ⚙️ Built With

- **React** – Frontend user interface built with functional components and hooks  
- **Flask** – Lightweight Python backend server for routing and API integration  
- **OpenAI GPT-3.5** – Generates summaries, flashcards, and quiz content  
- **PyMuPDF (fitz)** – Parses text from uploaded PDF files  
- **HTML/CSS** – Clean styling and layout for accessible, mobile-friendly use  
- **localStorage** – Client-side caching and usage tracking

---

## ✅ User Stories

The following **required** functionality is completed:

- ✅ User can **upload a PDF** file from their device  
- ✅ User can **generate a detailed summary** of the PDF using GPT-3.5  
- ✅ User can **create 5 flashcards** based on the summary, with flip animation  
- ✅ User can **generate a 5-question multiple-choice quiz** from the summary  
- ✅ User can **interact with quiz questions** and get instant feedback on correctness  
- ✅ User sees **loading indicators** and error handling throughout  
- ✅ Summary, flashcards, and quiz content is **cached using a hash of the PDF**, preventing redundant GPT calls

---

## Optional Features

- ✅ Flashcards support **question/answer flipping** on click  
- ✅ Quiz section shows **correctness feedback** with colored indicators (✅ / ❌)  
- ✅ **Drag-and-drop PDF upload** supported alongside file picker  
- ✅ Smooth **scrolling to flashcards/quiz** after generation  
- ✅ **Responsive layout** optimized for both desktop and mobile screens  
- ✅ Summary text is rendered with **preserved formatting and readability**

---

## Additional Features

- ✅ **Local caching** of responses using SHA256 PDF/text hash to avoid redundant API usage  
- ✅ Prompts are carefully engineered to **enforce JSON format** from GPT responses  
- ✅ **Fallback logic** included to extract partial JSON if GPT output includes noise  
- ✅ **Minimalist UI** with soft card styling, centered content, and intuitive buttons  
- ✅ Clearly marked footer with **credits and OpenAI attribution**
