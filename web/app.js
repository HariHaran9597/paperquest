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
  for (const item of quest.evidence) {
    const link = document.createElement('a');
    link.href = item.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = `${item.section} · ${item.reference} ↗`;
    links.append(link);
  }
  document.querySelector('#limitations').textContent = quest.limitations.join(' ');
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

slider.addEventListener('input', () => {
  document.querySelector('#positionState').textContent = slider.value === '0' ? 'OFF' : `${slider.value}%`;
  slider.style.background = `linear-gradient(90deg, var(--lime) ${slider.value}%, #384032 ${slider.value}%)`;
});
document.querySelector('#runButton').addEventListener('click', runExperiment);
document.querySelector('#resetButton').addEventListener('click', async () => {
  selectedToken = quest.defaults.query_token;
  slider.value = String(Math.round(quest.defaults.position_strength * 100));
  for (const item of tokensRoot.querySelectorAll('.token')) {
    const active = Number(item.dataset.index) === selectedToken;
    item.classList.toggle('selected', active);
    item.setAttribute('aria-pressed', String(active));
  }
  await runExperiment();
});

loadQuest().catch((error) => { resultText.textContent = error.message; });

