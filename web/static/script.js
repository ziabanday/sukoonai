const form = document.getElementById("chat-form");
const questionInput = document.getElementById("question");
const responseCard = document.getElementById("response");
const answerDiv = document.getElementById("answer");
const sourcesUl = document.getElementById("sources");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;

  answerDiv.textContent = "Thinking...";
  sourcesUl.innerHTML = "";
  responseCard.hidden = false;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Request failed");

    answerDiv.textContent = data.answer;
    data.sources.forEach(src => {
      const li = document.createElement("li");
      li.textContent = src;
      sourcesUl.appendChild(li);
    });
  } catch (err) {
    answerDiv.textContent = "Error: " + err.message;
  }
});
