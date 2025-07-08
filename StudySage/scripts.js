const DEV_MODE = true; // Set to false to re-enable daily limits
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
    updateUsageMessage(); // Still show a message
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

  try {
    const res = await fetch('http://localhost:5000/upload', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();

    if (data.summary) {
      document.getElementById('summary').innerText = data.summary;
    } else {
      document.getElementById('summary').innerText = 'Error: ' + data.error;
    }
  } catch (err) {
    document.getElementById('summary').innerText = 'Request failed: ' + err.message;
  }
}

window.onload = updateUsageMessage;
