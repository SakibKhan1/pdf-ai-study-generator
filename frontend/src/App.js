import React, { useState, useRef } from 'react';
import './App.css';

// Backend URL for deployed API
const BACKEND_URL = "https://pdf-ai-study-generator.onrender.com";

// Main app function
function App() {
  // State management
  const [fileName, setFileName] = useState('');
  const [summary, setSummary] = useState('');
  const [flashcards, setFlashcards] = useState([]);
  const [quiz, setQuiz] = useState([]);
  const [loading, setLoading] = useState(false);
  const [flashcardLoading, setFlashcardLoading] = useState(false);
  const [quizLoading, setQuizLoading] = useState(false);
  const [flashcardsVisible, setFlashcardsVisible] = useState(false);
  const [quizVisible, setQuizVisible] = useState(false);
  const [quizResults, setQuizResults] = useState({});
  const flashcardRef = useRef(null);
  const quizRef = useRef(null);
  const inputRef = useRef();

  // File selected
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) setFileName(file.name);
  };

  // Handle file drop
  const handleDrop = (e) => {
    e.preventDefault();
    inputRef.current.files = e.dataTransfer.files;
    setFileName(e.dataTransfer.files[0]?.name || '');
  };

  // Submit PDF for summary
  const submitPDFForSummary = async () => {
    const file = inputRef.current.files[0];
    if (!file) return;

    setFileName(file.name);
    setLoading(true);
    setSummary('');
    setFlashcards([]);
    setQuiz([]);
    setFlashcardsVisible(false);
    setQuizVisible(false);
    setQuizResults({});

    const formData = new FormData();
    formData.append('pdf', file);

    try {
      const res = await fetch(`${BACKEND_URL}/upload`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      setSummary(data.summary || 'No summary returned.');
      console.log("Summary loaded:", data.fromCache ? "from cache" : "fresh");
    } catch (err) {
      setSummary('Request failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Generate flashcards
  const generateFlashcards = async () => {
    if (!summary || flashcards.length > 0) return;

    setFlashcardLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/flashcards`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: summary }),
      });

      const data = await res.json();
      if (data.error) throw new Error(data.error);

      setFlashcards(data.flashcards);
      setFlashcardsVisible(true);

      setTimeout(() => {
        flashcardRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);

      console.log("Flashcards loaded:", data.fromCache ? "from cache" : "fresh");
    } catch (err) {
      console.error("Flashcard error:", err);
      setFlashcards([{ question: 'Error', answer: err.message }]);
    } finally {
      setFlashcardLoading(false);
    }
  };

  // Generate quiz
  const generateQuiz = async () => {
    if (!summary || quiz.length > 0) return;

    setQuizLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/quiz`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: summary }),
      });

      const data = await res.json();
      if (data.error) throw new Error(data.error);

      setQuiz(data.quiz);
      setQuizResults({});
      setQuizVisible(true);

      setTimeout(() => {
        quizRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);

      console.log("Quiz loaded:", data.fromCache ? "from cache" : "fresh");
    } catch (err) {
      console.error("Quiz error:", err);
      setQuiz([{ question: 'Error: ' + err.message, choices: [], correct: 'A' }]);
    } finally {
      setQuizLoading(false);
    }
  };

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', padding: '2rem', backgroundColor: '#eeeeee', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <h1 style={{ textAlign: 'center', fontSize: '2rem' }}>PDF AI Study Generator</h1>

      {/*Upload area*/}
      <div
        className="dropzone"
        onClick={() => inputRef.current.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        <img
          src="https://upload.wikimedia.org/wikipedia/commons/8/87/PDF_file_icon.svg"
          alt="PDF Icon"
          className="pdf-icon"
        />
        <p><strong>Drag and drop a PDF here</strong> or click to upload</p>
        <input
          type="file"
          ref={inputRef}
          accept="application/pdf"
          hidden
          onChange={handleFileChange}
        />
        {fileName && (
          <div style={{ marginTop: "12px", fontStyle: "italic", fontSize: "0.9rem", color: "#444" }}>
            Uploaded: <strong>{fileName}</strong>
          </div>
        )}
      </div>

      {/*Summarize button*/}
      <div style={{ textAlign: 'center', marginTop: '1rem' }}>
        <button onClick={submitPDFForSummary}>Summarize PDF</button>
      </div>

      {loading && <div className="spinner" style={{ marginTop: '10px' }}></div>}

      {/*Summary output*/}
      {summary && (
        <div className="output-box">
          <h3>Summary</h3>
          <div id="summary">{summary}</div>
        </div>
      )}

      {/*Flashcard & quiz buttons*/}
      {summary && (
        <div style={{ marginTop: '1rem', display: 'flex', gap: '20px', justifyContent: 'center' }}>
          <div>
            <button onClick={generateFlashcards} disabled={flashcards.length > 0}>Generate Flashcards</button>
            {flashcardLoading && <div className="spinner" style={{ marginTop: '8px' }}></div>}
          </div>
          <div>
            <button onClick={generateQuiz} disabled={quiz.length > 0}>Generate Quiz</button>
            {quizLoading && <div className="spinner" style={{ marginTop: '8px' }}></div>}
          </div>
        </div>
      )}

      {/*Flashcard section*/}
      {flashcardsVisible && (
        <div className="card" ref={flashcardRef}>
          <span className="close-btn" onClick={() => setFlashcardsVisible(false)}>×</span>
          <h3>Flashcards</h3>
          <div className="flashcard-grid">
            {flashcards.map((fc, idx) => (
              <div className="flashcard" key={idx} onClick={(e) => e.currentTarget.classList.toggle('flip')}>
                <div className="flashcard-inner">
                  <div className="flashcard-front">{fc.question}</div>
                  <div className="flashcard-back">{fc.answer}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/*Quiz section*/}
      {quizVisible && (
        <div className="card" ref={quizRef}>
          <span className="close-btn" onClick={() => setQuizVisible(false)}>×</span>
          <h3>Quiz</h3>
          <div id="quizContent">
            {quiz.map((q, i) => (
              <div className="quiz-question" key={i}>
                <p><strong>{i + 1}. {q.question}</strong></p>
                <div className="quiz-options">
                  {q.choices.map((choice, j) => {
                    const letter = String.fromCharCode(65 + j);
                    const isAnswered = quizResults[i] !== undefined;

                    return (
                      <button
                        key={j}
                        className={`quiz-option ${
                          isAnswered
                            ? (letter === q.correct
                              ? 'correct'
                              : quizResults[i].selected === letter && 'wrong')
                            : ''
                        }`}
                        disabled={isAnswered}
                        onClick={() => {
                          if (isAnswered) return;
                          setQuizResults(prev => ({
                            ...prev,
                            [i]: {
                              selected: letter,
                              correct: letter === q.correct
                            }
                          }));
                        }}
                      >
                        {letter}) {choice}
                      </button>
                    );
                  })}
                </div>
                {quizResults[i] && (
                  <div style={{ marginTop: '5px', fontWeight: 'bold', color: quizResults[i].correct ? 'green' : 'red' }}>
                    {quizResults[i].correct ? '✅ Correct answer' : '❌ Wrong answer'}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/*Footer*/}
      <footer style={{ marginTop: '6rem', textAlign: 'center', color: '#444' }}>
        <div style={{
          borderTop: '1px solid #ccc',
          maxWidth: '600px',
          margin: '0 auto',
          paddingTop: '3rem',
          marginTop: '2rem'
        }}>
          <p style={{ fontSize: '1.2rem', marginBottom: '0.75rem' }}>
            PDF AI Study Generator is a tool that converts your uploaded PDFs into AI-generated summaries, flashcards, and quizzes for fast learning.
          </p>
          <p style={{ fontSize: '0.9rem', color: '#666' }}>
            © 2025 Sakib Khan · Powered by OpenAI's GPT API
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;