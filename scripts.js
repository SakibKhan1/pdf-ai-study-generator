const DEV_MODE = true; // set to false to re-enable daily limits
const MAX_USES_PER_DAY = 5;

function getTodayUsage() {
  const today = new Date().toISOString().split("T")[0];
  let usage = JSON.parse(localStorage.getItem("studysage_usage") || "{}");

  if (usage.date !== today) {
    usage = { date: today, count: 0 };
    localStorage.setItem("studysage_usage", JSON.stringify(usage));
  }

  return usage;
}

function canUseToday() {
  if (DEV_MODE) {
    updateUsageMessage();
    return true;
  }

  const usage = getTodayUsage();
  if (usage.count >= MAX_USES_PER_DAY) return false;

  usage.count += 1;
  localStorage.setItem("studysage_usage", JSON.stringify(usage));
  updateUsageMessage();
  return true;
}

function updateUsageMessage() {
  const usageElement = document.getElementById("usageCount");

  if (DEV_MODE) {
    usageElement.innerText = "🧪 Developer mode: unlimited summaries enabled.";
    return;
  }

  const usage = getTodayUsage();
  const remaining = MAX_USES_PER_DAY - usage.count;

  if (remaining > 0) {
    usageElement.innerText = `You have ${remaining} summary use${remaining === 1 ? "" : "s"} left today.`;
  } else {
    usageElement.innerText = "You've reached your daily limit of 5 summaries. Try again tomorrow!";
  }
}

function closeBox(id) {
  document.getElementById(id).style.display = 'none';
}

async function uploadPDF() {
  const input = document.getElementById('pdfInput');
  if (!input.files.length) return alert('Please select a PDF file');

  if (!canUseToday()) {
    alert("You've reached your daily limit of 5 summaries. Try again tomorrow!");
    return;
  }

  const formData = new FormData();
  formData.append('pdf', input.files[0]);

  document.getElementById('summary').innerText = 'Loading summary...';
  document.getElementById('flashcardsContent').innerText = '';
  document.getElementById('quizContent').innerText = '';
  document.getElementById('flashcards').style.display = 'none';
  document.getElementById('quiz').style.display = 'none';
  document.getElementById('actionButtons').style.display = 'none';

  try {
    const res = await fetch('http://localhost:5000/upload', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();

    if (data.summary) {
      document.getElementById('summary').innerText = data.summary;
      document.getElementById('actionButtons').style.display = 'flex';
    } else {
      document.getElementById('summary').innerText = 'Error: ' + data.error;
    }
  } catch (err) {
    document.getElementById('summary').innerText = 'Request failed: ' + err.message;
  }
}

async function generateFlashcards() {
  const summaryText = document.getElementById("summary").innerText;
  if (!summaryText) return;

  const flashcardsBox = document.getElementById("flashcards");
  const flashcardsContent = document.getElementById("flashcardsContent");
  flashcardsBox.style.display = "block";
  flashcardsContent.innerHTML = "Generating flashcards...";

  try {
    const res = await fetch("http://localhost:5000/flashcards", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: summaryText })
    });

    const data = await res.json();

    const flashcards = (data.flashcards || "Error: " + data.error)
      .split(/\n\n+|\n---\n|---|\r\n\r\n+/)
      .filter(f => f.trim());

    const cardsHTML = flashcards.slice(0, 10).map(card => {
      const [q, a] = card.split(/Answer:\s*/);
      if (!q || !a) return "";

      const cleaned = q
        .replace(/Flashcard\s*\d+\s*:?/i, "")
        .replace(/Question[:\-]?\s*/i, "")
        .replace(/\*\*/g, "")
        .trim();

      const answer = a
        .replace(/\*\*/g, "")
        .replace(/^Answer[:\-]?\s*/i, "")
        .trim();

      if (!cleaned || !answer || answer === "**" || answer.toLowerCase().includes("no answer")) return "";

      return `
        <div class="flashcard">
          <div class="flashcard-inner">
            <div class="flashcard-front">${cleaned}</div>
            <div class="flashcard-back">${answer}</div>
          </div>
        </div>
      `;
    }).join("");

    flashcardsContent.innerHTML = cardsHTML || "No valid flashcards generated.";
    document.getElementById("flashcards").scrollIntoView({ behavior: "smooth" });

  } catch (err) {
    flashcardsContent.innerText = "Request failed: " + err.message;
  }
}

async function generateQuiz() {
  const summaryText = document.getElementById("summary").innerText;
  if (!summaryText) return;

  const quizBox = document.getElementById("quiz");
  const quizContent = document.getElementById("quizContent");
  quizBox.style.display = "block";
  quizContent.innerText = "Generating quiz...";

  try {
    const res = await fetch("http://localhost:5000/quiz", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: summaryText })
    });

    const data = await res.json();
    const quizText = data.quiz || "";

    const rawBlocks = quizText.trim().split(/\n\s*\n/);

    let questions = rawBlocks
      .map(block => {
        const lines = block.trim().split("\n");
        const hasQuestion = lines[0]?.match(/^\d+\./);
        const hasOptions = lines.filter(line => /^[A-D]\)/.test(line)).length >= 4;
        const hasAnswer = lines.some(line => /Correct Answer:/i.test(line));
        return (hasQuestion && hasOptions && hasAnswer) ? block : null;
      })
      .filter(Boolean)
      .slice(0, 5); // up to 5 valid questions

    if (!questions.length) {
      quizContent.innerText = "No valid questions were generated.";
      return;
    }

    const quizHTML = questions.map((block, i) => {
      const lines = block.trim().split("\n");
      const questionText = lines[0].replace(/^\d+\.\s*/, "").trim();
      const options = lines.filter(line => /^[A-D]\)/.test(line));
      const correctLine = lines.find(line => /Correct Answer:/i.test(line));
      const correctLetter = correctLine ? correctLine.trim().split(":")[1].trim().charAt(0).toUpperCase() : null;

      const optionsHTML = options.map(option => {
        const letter = option.trim().charAt(0);
        const text = option.trim().slice(3).trim();
        return `
          <button class="quiz-option" onclick="checkAnswer(this, '${letter}', '${correctLetter}', ${i})">
            ${letter}) ${text}
          </button>
        `;
      }).join("");

      return `
        <div class="quiz-question">
          <p><strong>${i + 1}. ${questionText}</strong></p>
          <div class="quiz-options" id="quiz-options-${i}">
            ${optionsHTML}
          </div>
          <p class="quiz-feedback" id="quiz-feedback-${i}"></p>
        </div>
      `;
    }).join("");

    quizContent.innerHTML = quizHTML;
    document.getElementById("quiz").scrollIntoView({ behavior: "smooth" });

  } catch (err) {
    quizContent.innerText = "Request failed: " + err.message;
  }
}


function checkAnswer(button, selected, correct, index) {
  const buttons = document.querySelectorAll(`#quiz-options-${index} .quiz-option`);
  buttons.forEach(btn => btn.disabled = true);

  const feedback = document.getElementById(`quiz-feedback-${index}`);
  if (selected === correct) {
    button.classList.add("correct");
    feedback.innerText = "✅ Correct!";
  } else {
    button.classList.add("wrong");
    const correctBtn = Array.from(buttons).find(b => b.innerText.startsWith(`${correct})`));
    if (correctBtn) correctBtn.classList.add("correct");
    feedback.innerText = `❌ Wrong. Correct answer: ${correct}`;
  }
}


window.onload = updateUsageMessage;
