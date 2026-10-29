const tokensRoot = document.querySelector('#tokens');
const heatmap = document.querySelector('#heatmap');
const slider = document.querySelector('#positionSlider');
const resultLine = document.querySelector('#resultLine');
const resultText = document.querySelector('#resultText');
const questClaim = document.querySelector('#questClaim');
let quest;
let selectedToken = 4;

async function loadQuest() {
  const response = await fetch('/api/v1/quest');
  if (!response.ok) throw new Error('Quest could not be loaded. Refresh and try again.');
  quest = await response.json();
  selectedToken = quest.defaults.query_token;
  slider.value = String(Math.round(quest.defaults.position_strength * 100));
  tokensRoot.replaceChildren();
  quest.tokens.forEach((word, index) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `token${index === selectedToken ? ' selected' : ''}`;
    button.dataset.index = String(index);
    button.textContent = word;
    button.setAttribute('aria-pressed', String(index === selectedToken));
    button.addEventListener('click', () => {
      selectedToken = index;
      for (const item of tokensRoot.querySelectorAll('.token')) {
        const active = Number(item.dataset.index) === index;
        item.classList.toggle('selected', active);
        item.setAttribute('aria-pressed', String(active));
      }
      document.querySelector('#focusToken').textContent = `“${word}”`;
      runExperiment();
    });
    tokensRoot.append(button);
  });
  questClaim.textContent = quest.claim;
  const links = document.querySelector('#evidenceLinks');
  links.replaceChildren();
  for (const item of quest.evidence) {
    const link = document.createElement('a');
    link.href = item.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = `${item.section} · ${item.reference} ↗`;
    links.append(link);
  }
  document.querySelector('#limitations').textContent = quest.limitations.join(' ');
  document.querySelector('#quizQuestion').textContent = quest.quiz.question;
  const quizOptions = document.querySelector('#quizForm');
  quizOptions.replaceChildren();
  quest.quiz.options.forEach((option) => {
    const label = document.createElement('label');
    label.className = 'quiz-option';
    const input = document.createElement('input');
    input.type = 'radio';
    input.name = 'answer';
    input.value = option.id;
    input.required = true;
    const text = document.createElement('span');
    text.textContent = option.text;
    label.append(input, text);
    quizOptions.append(label);
  });
  const submit = document.createElement('button');
  submit.type = 'submit';
  submit.className = 'quiz-submit';
  submit.textContent = 'Check answer';
  quizOptions.append(submit);
  await runExperiment();
}

async function runExperiment() {
  resultText.textContent = 'Running the fixed experiment…';
  resultLine.classList.remove('success');
  try {
    const response = await fetch('/api/v1/experiment/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query_token: selectedToken,
        position_strength: Number(slider.value) / 100,
      }),
    });
    if (!response.ok) throw new Error('The experiment rejected the input. Reset and try again.');
    const result = await response.json();
    heatmap.replaceChildren();
    result.tokens.forEach((word, index) => {
      const cell = document.createElement('div');
      cell.className = `heat-cell${index === selectedToken ? ' focus' : ''}`;
      const weight = result.weights[index];
      cell.style.backgroundColor = `rgba(193, 243, 106, ${0.08 + weight * 0.82})`;
      cell.style.color = weight > 0.27 ? '#192013' : '#dcebc5';
      const percent = document.createElement('small');
      percent.textContent = `${(weight * 100).toFixed(1)}%`;
      const label = document.createElement('span');
      label.textContent = word;
      cell.append(percent, label);
      heatmap.append(cell);
    });
    document.querySelector('#focusToken').textContent = `“${result.query_label}”`;
    document.querySelector('#positionState').textContent = result.position_strength === 0
      ? 'OFF'
      : `${Math.round(result.position_strength * 100)}%`;
    slider.style.background = `linear-gradient(90deg, var(--lime) ${slider.value}%, #384032 ${slider.value}%)`;
    document.querySelector('#scoresOutput').textContent = result.scores.map((score, i) => `${result.tokens[i]}: ${score}`).join('\n');
    document.querySelector('#outputVector').textContent = `[${result.output_vector.join(', ')}]`;
    resultText.textContent = `“${result.query_label}” assigns its largest weight to “${result.most_attended_token}”. Change the position signal and compare the scores.`;
    resultLine.classList.add('success');
  } catch (error) {
    resultText.textContent = error.message || 'The experiment could not run. Please refresh.';
  }
}

async function compareExperiment() {
  const button = document.querySelector('#compareButton');
  const panel = document.querySelector('#comparisonPanel');
  button.disabled = true;
  button.textContent = 'Comparing…';
  try {
    const response = await fetch('/api/v1/experiment/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query_token: selectedToken, position_strength: Number(slider.value) / 100 }),
    });
    if (!response.ok) throw new Error('Comparison failed. Please try again.');
    const result = await response.json();
    const grid = document.querySelector('#comparisonGrid');
    grid.replaceChildren();
    [result.baseline, result.current].forEach((run, runIndex) => {
      const card = document.createElement('article');
      card.className = 'comparison-card';
      const title = document.createElement('h5');
      title.textContent = runIndex === 0 ? result.baseline_label : result.current_label;
      card.append(title);
      run.tokens.forEach((token, index) => {
        const row = document.createElement('div');
        row.className = 'comparison-row';
        const name = document.createElement('span');
        name.textContent = token;
        const value = document.createElement('strong');
        value.textContent = `${(run.weights[index] * 100).toFixed(1)}%`;
        row.append(name, value);
        card.append(row);
      });
      grid.append(card);
    });
    document.querySelector('#comparisonNote').textContent = result.interpretation;
    panel.hidden = false;
  } catch (error) {
    document.querySelector('#comparisonNote').textContent = error.message || 'Comparison failed.';
    panel.hidden = false;
  } finally {
    button.disabled = false;
    button.textContent = 'Compare with signal off';
  }
}

async function submitQuiz(event) {
  event.preventDefault();
  const selected = new FormData(event.currentTarget).get('answer');
  if (!selected) return;
  const response = await fetch('/api/v1/quiz/answer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ option_id: selected }),
  });
  const feedback = document.querySelector('#quizFeedback');
  if (!response.ok) {
    feedback.textContent = 'Could not check the answer. Please try again.';
    return;
  }
  const result = await response.json();
  feedback.textContent = `${result.feedback} ${result.explanation}`;
  feedback.classList.toggle('correct', result.correct);
  feedback.classList.toggle('incorrect', !result.correct);
}

slider.addEventListener('input', () => {
  document.querySelector('#positionState').textContent = slider.value === '0' ? 'OFF' : `${slider.value}%`;
  slider.style.background = `linear-gradient(90deg, var(--lime) ${slider.value}%, #384032 ${slider.value}%)`;
});
document.querySelector('#runButton').addEventListener('click', runExperiment);
document.querySelector('#compareButton').addEventListener('click', compareExperiment);
document.querySelector('#quizForm').addEventListener('submit', submitQuiz);
document.querySelector('#resetButton').addEventListener('click', async () => {
  selectedToken = quest.defaults.query_token;
  slider.value = String(Math.round(quest.defaults.position_strength * 100));
  document.querySelector('#comparisonPanel').hidden = true;
  for (const item of tokensRoot.querySelectorAll('.token')) {
    const active = Number(item.dataset.index) === selectedToken;
    item.classList.toggle('selected', active);
    item.setAttribute('aria-pressed', String(active));
  }
  await runExperiment();
});

loadQuest().catch((error) => { resultText.textContent = error.message; });

