import React, { useState, useRef } from 'react';
import './App.css';


const computedDefault = window.location.hostname === 'localhost'
  ? 'http://localhost:5000'
  : 'https://pdf-ai-study-generator-2.vercel.app';

const envUrl = (process.env.REACT_APP_BACKEND_URL || '').trim();
// If env var is the empty string, we’ll use relative paths 
const BACKEND_URL = envUrl === '' ? '' : (envUrl || computedDefault);

console.log('BACKEND_URL =', BACKEND_URL || '(relative paths via dev proxy)');


const makeUrl = (path) => `${BACKEND_URL}${path.startsWith('/') ? path : `/${path}`}`;

// Small helper: fetch with timeout + JSON + nicer errors
async function apiFetch(path, options = {}, { timeoutMs = 45000 } = {}) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(makeUrl(path), { ...options, signal: controller.signal });
    let data;
    const text = await res.text();
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      // Non-JSON response
      throw new Error(`Unexpected response format (${res.status}): ${text?.slice(0, 200) || 'empty'}`);
    }
    if (!res.ok) {
      // Bubble up backend error if present
      const msg = data?.error || data?.message || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return data;
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Request timed out. PDF might be too big to process, please try again with a smaller PDF please.');
    }
    throw err;
  } finally {
    clearTimeout(id);
  }
}

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
    const file = inputRef.current?.files?.[0];
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
    // Backend expects "pdf"
    formData.append('pdf', file);

    try {
      const data = await apiFetch(
        '/upload',
        {
          method: 'POST',
          body: formData,
        },
        { timeoutMs: 120000 } // 2 minutes
      );

      setSummary(data.summary || 'No summary returned.');
      console.log('Summary loaded:', data.fromCache ? 'from cache' : 'fresh');
    } catch (err) {
      console.error('Summary error:', err);
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
      const data = await apiFetch('/flashcards', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: summary }),
      });
      if (data.error) throw new Error(data.error);

      setFlashcards(data.flashcards || []);
      setFlashcardsVisible(true);

      setTimeout(() => {
        flashcardRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);

      console.log('Flashcards loaded:', data.fromCache ? 'from cache' : 'fresh');
    } catch (err) {
      console.error('Flashcard error:', err);
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
      const data = await apiFetch('/quiz', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: summary }),
      });
      if (data.error) throw new Error(data.error);

      setQuiz(data.quiz || []);
      setQuizResults({});
      setQuizVisible(true);

      setTimeout(() => {
        quizRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);

      console.log('Quiz loaded:', data.fromCache ? 'from cache' : 'fresh');
    } catch (err) {
      console.error('Quiz error:', err);
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
          <div style={{ marginTop: '12px', fontStyle: 'italic', fontSize: '0.9rem', color: '#444' }}>
            Uploaded: <strong>{fileName}</strong>
          </div>
        )}
      </div>

      {/*Summarize button*/}
      <div style={{ textAlign: 'center', marginTop: '1rem' }}>
        <button onClick={submitPDFForSummary}>Summarize PDF</button>
      </div>

      {loading && <div className="spinner" style={{ marginTop: '10px' }}></div>}
      {loading && (
  <p style={{ textAlign: 'center', color: '#666', marginTop: '10px' }}>
    Processing PDF… Large files may take up to a minute.
  </p>
)}

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
            © 2025 Sakib Khan · Powered by OpenAI&apos;s GPT API
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
