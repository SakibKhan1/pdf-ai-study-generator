const DEV_MODE = true; //set to false to re-enable daily limits
const MAX_USES_PER_DAY = 5;
// if new day then the usage limit is reset using localstorage
function getTodayUsage() {
  const today = new Date().toISOString().split("T")[0];
  let usage = JSON.parse(localStorage.getItem("studysage_usage") || "{}");

  if (usage.date !== today) {
    usage = { date: today, count: 0 };
    localStorage.setItem("studysage_usage", JSON.stringify(usage));
  }

  return usage;
}
// determines whether the user can use the app today or not 
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
//updates the usage remaining
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
//handles pdf upload and fetches summary from backend 
async function uploadPDF() {
  const input = document.getElementById('pdfInput');
  if (!input.files.length) return alert('Please select a PDF file');

  if (!canUseToday()) {
    alert("You've reached your daily limit of 5 summaries. Try again tomorrow!");
    return;
  }

  const formData = new FormData();
  formData.append('pdf', input.files[0]);
  //clear existing outputs and shows the loading message to make it organized
  document.getElementById('summary').innerText = 'Loading summary...';
  document.getElementById('flashcards').innerText = '';
  document.getElementById('quiz').innerText = '';
  document.getElementById('flashcardBtn').style.display = 'none';
  document.getElementById('quizBtn').style.display = 'none';

  try {
    const res = await fetch('http://localhost:5000/upload', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();

    if (data.summary) {
      document.getElementById('summary').innerText = data.summary;
      document.getElementById('flashcardBtn').style.display = 'inline-block';
      document.getElementById('quizBtn').style.display = 'inline-block';
    } else {
      document.getElementById('summary').innerText = 'Error: ' + data.error;
    }
  } catch (err) {
    document.getElementById('summary').innerText = 'Request failed: ' + err.message;
  }
}
//handles creating flashcards after summarizing is done 
async function generateFlashcards() {
  const summaryText = document.getElementById("summary").innerText;
  if (!summaryText) return;

  document.getElementById("flashcards").innerText = "Generating flashcards...";

  try {
    const res = await fetch("http://localhost:5000/flashcards", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: summaryText })
    });

    const data = await res.json();
    document.getElementById("flashcards").innerText = data.flashcards || "Error: " + data.error;
  } catch (err) {
    document.getElementById("flashcards").innerText = "Request failed: " + err.message;
  }
}
//same as flashcards but for a quiz instead after summary is done
async function generateQuiz() {
  const summaryText = document.getElementById("summary").innerText;
  if (!summaryText) return;

  document.getElementById("quiz").innerText = "Generating quiz...";

  try {
    const res = await fetch("http://localhost:5000/quiz", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: summaryText })
    });

    const data = await res.json();
    document.getElementById("quiz").innerText = data.quiz || "Error: " + data.error;
  } catch (err) {
    document.getElementById("quiz").innerText = "Request failed: " + err.message;
  }
}

window.onload = updateUsageMessage;
