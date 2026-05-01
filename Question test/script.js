/**
 * StudyQuest - メインアプリケーション
 */
window.App = (function () {
  let subjects = [];
  let allQuestions = [];
  let currentQuiz = { questions: [], currentIndex: 0, answers: [], subjectId: '', config: {} };
  let quizTypeFilter = 'all';
  let difficultyFilter = 'all';
  let selectedSubjectId = '';

  // === 初期化 ===
  async function init() {
    UI.init();
    await loadData();
    renderHome();
    renderSubjects();
    initSettings();
    populateGenerateModal();
  }

  async function loadData() {
    try {
      const [subRes, qRes] = await Promise.all([
        fetch('data/subjects.json?t=' + Date.now()).then(r => r.json()),
        fetch('data/questions.json?t=' + Date.now()).then(r => r.json())
      ]);
      subjects = subRes.subjects || [];
      allQuestions = qRes.questions || [];
      // カスタム問題を追加
      const custom = Storage.getCustomQuestions();
      allQuestions = allQuestions.concat(custom);
    } catch (e) {
      console.error('データ読み込みエラー:', e);
      UI.showToast('データの読み込みに失敗しました', 'error');
    }
  }

  function getCategoryColor(cat) {
    const colors = { '数学': '#6C63FF', '国語': '#FF6B9D', '理科': '#00D4AA', '英語': '#FFB347', '社会': '#4ECDC4', '情報': '#45B7D1', '家庭': '#F7DC6F', '単語帳': '#E056A0' };
    return colors[cat] || '#6C63FF';
  }

  function getCategoryEmoji(cat) {
    const emojis = { '数学': '∑', '国語': '文', '理科': '🧪', '英語': 'A', '社会': '🌍', '情報': '💻', '家庭': '🏠', '単語帳': '📖' };
    return emojis[cat] || '📚';
  }

  // === ホーム画面 ===
  function renderHome() {
    const stats = Storage.getStats();
    document.getElementById('stat-total').textContent = stats.total;
    document.getElementById('stat-correct').textContent = stats.correct;
    document.getElementById('stat-rate').textContent = stats.rate + '%';

    // 連続正解計算
    const history = Storage.getHistory();
    let streak = 0;
    for (const h of history) { if (h.correct) streak++; else break; }
    document.getElementById('stat-streak').textContent = streak;

    // 間違い数
    const wrongIds = Storage.getWrongQuestionIds();
    document.getElementById('wrong-count-label').textContent = wrongIds.length + '問';

    // 最近の学習
    renderRecentActivity(history.slice(0, 10));
  }

  function renderRecentActivity(items) {
    const el = document.getElementById('recent-list');
    if (items.length === 0) { el.innerHTML = '<p class="text-muted" style="padding:20px;text-align:center">まだ学習記録がありません</p>'; return; }
    const subjectMap = {};
    subjects.forEach(s => subjectMap[s.id] = s);
    el.innerHTML = items.map(item => {
      const subj = subjectMap[item.subjectId];
      const color = subj ? getCategoryColor(subj.category) : '#6C63FF';
      const name = subj ? subj.name : '不明';
      return '<div class="activity-item"><div class="activity-dot" style="background:' + (item.correct ? 'var(--correct)' : 'var(--incorrect)') + '"></div><div style="flex:1"><span style="color:' + color + ';font-weight:500">' + name + '</span><span class="text-muted" style="margin-left:8px;font-size:.8rem">' + (item.correct ? '✓ 正解' : '✕ 不正解') + '</span></div><div class="text-muted" style="font-size:.75rem">' + UI.formatDate(item.timestamp) + '</div></div>';
    }).join('');
  }

  // === 教科選択画面 ===
  function renderSubjects(filterCat) {
    renderCategoryFilter(filterCat);
    const grid = document.getElementById('subjects-grid');
    const stats = Storage.getSubjectStats();
    const filtered = filterCat ? subjects.filter(s => s.category === filterCat) : subjects;
    grid.innerHTML = filtered.map(s => {
      const color = getCategoryColor(s.category);
      const emoji = getCategoryEmoji(s.category);
      const st = stats[s.id] || { total: 0, correct: 0, rate: 0 };
      const qCount = allQuestions.filter(q => q.subjectId === s.id).length;
      return '<div class="card subject-card" style="--subject-color:' + color + '" onclick="App.openSubjectSetup(\'' + s.id + '\')">' +
        '<div class="subject-icon" style="--subject-color:' + color + '">' + emoji + '</div>' +
        '<div class="subject-name">' + s.name + '</div>' +
        '<div class="subject-meta">' + s.textbook.publisher + ' / ' + s.textbook.code + '</div>' +
        '<div class="subject-stats"><span>📝 ' + qCount + '問</span><span>✅ ' + st.rate + '%</span></div></div>';
    }).join('');
  }

  function renderCategoryFilter(active) {
    const cats = [...new Set(subjects.map(s => s.category))];
    const el = document.getElementById('category-filter');
    el.innerHTML = '<button class="category-btn' + (!active ? ' active' : '') + '" onclick="App.filterCategory(null)" style="' + (!active ? 'background:var(--accent);color:#fff' : '') + '">すべて</button>' +
      cats.map(c => {
        const isActive = active === c;
        const color = getCategoryColor(c);
        return '<button class="category-btn' + (isActive ? ' active' : '') + '" onclick="App.filterCategory(\'' + c + '\')" style="' + (isActive ? 'background:' + color + ';color:#fff;border-color:' + color : '') + '">' + c + '</button>';
      }).join('');
  }

  function filterCategory(cat) { renderSubjects(cat); }

  // === 出題設定 ===
  function openSubjectSetup(subjectId) {
    selectedSubjectId = subjectId;
    const subj = subjects.find(s => s.id === subjectId);
    if (!subj) return;
    document.getElementById('setup-subject-title').textContent = subj.name + ' - 出題設定';
    const unitSelect = document.getElementById('setup-unit');
    unitSelect.innerHTML = '<option value="all">すべて</option>' + subj.units.map(u => '<option value="' + u.id + '">' + u.name + '</option>').join('');
    quizTypeFilter = 'all';
    difficultyFilter = 'all';
    document.querySelectorAll('#filter-type-group [data-type]').forEach(b => b.classList.toggle('active', b.dataset.type === 'all'));
    document.querySelectorAll('#filter-diff-group [data-diff]').forEach(b => b.classList.toggle('active', b.dataset.diff === 'all'));
    // 単語帳教科の場合は「単語一覧を見る」ボタンを表示
    const vocabBtn = document.getElementById('btn-vocab-list');
    vocabBtn.style.display = (subjectId === 'bricks1' || subjectId === 'kobun330') ? 'block' : 'none';
    // 単元変更時にもサマリーを更新
    unitSelect.onchange = function() { updateFilterSummary(); };
    updateFilterSummary();
    UI.openModal('modal-subject-setup');
  }

  function setQuizType(btn) {
    quizTypeFilter = btn.dataset.type;
    btn.closest('.filter-btn-group').querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    updateFilterSummary();
  }

  function setDifficulty(btn) {
    difficultyFilter = btn.dataset.diff;
    btn.closest('.filter-btn-group').querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    updateFilterSummary();
  }

  function updateFilterSummary() {
    const typeLabels = { 'all': 'すべて', '選択': '選択式', '記述': '記述式', '○×': '○×' };
    const diffLabels = { 'all': 'すべて', '1': '基礎', '2': '標準', '3': '応用' };
    const summaryType = document.getElementById('summary-type');
    const summaryDiff = document.getElementById('summary-diff');
    const summaryCount = document.getElementById('summary-count');
    if (summaryType) summaryType.textContent = typeLabels[quizTypeFilter] || quizTypeFilter;
    if (summaryDiff) summaryDiff.textContent = diffLabels[difficultyFilter] || difficultyFilter;
    // 対象問題数を計算
    const unitId = document.getElementById('setup-unit') ? document.getElementById('setup-unit').value : 'all';
    let pool = allQuestions.filter(q => q.subjectId === selectedSubjectId);
    if (unitId && unitId !== 'all') pool = pool.filter(q => q.unitId === unitId);
    if (quizTypeFilter && quizTypeFilter !== 'all') pool = pool.filter(q => q.type === quizTypeFilter);
    if (difficultyFilter && difficultyFilter !== 'all') pool = pool.filter(q => q.difficulty === parseInt(difficultyFilter));
    if (summaryCount) summaryCount.textContent = pool.length + '問';
  }

  // === クイズエンジン ===
  function startQuizFromSetup() {
    const unitId = document.getElementById('setup-unit').value;
    UI.closeModal('modal-subject-setup');
    startQuiz(selectedSubjectId, unitId, quizTypeFilter, difficultyFilter);
  }

  function openQuestionList() {
    const unitId = document.getElementById('setup-unit').value;
    let pool = allQuestions.filter(q => q.subjectId === selectedSubjectId);
    if (unitId && unitId !== 'all') pool = pool.filter(q => q.unitId === unitId);
    if (quizTypeFilter && quizTypeFilter !== 'all') pool = pool.filter(q => q.type === quizTypeFilter);
    if (difficultyFilter && difficultyFilter !== 'all') pool = pool.filter(q => q.difficulty === parseInt(difficultyFilter));

    const subj = subjects.find(s => s.id === selectedSubjectId);
    const unit = subj && unitId !== 'all' ? subj.units.find(u => u.id === unitId) : null;
    
    document.getElementById('qlist-title').textContent = (subj ? subj.name : '') + (unit ? ' / ' + unit.name : '') + ' の問題一覧';
    document.getElementById('qlist-stats').textContent = `全 ${pool.length} 問`;
    
    const container = document.getElementById('qlist-container');
    if (pool.length === 0) {
      container.innerHTML = '<p class="text-muted" style="text-align:center;padding:20px">該当する問題がありません</p>';
    } else {
      container.innerHTML = pool.map(q => {
        let ansText = escapeHtml(q.answer);
        if (q.type === '選択' && q.choices) {
            ansText = escapeHtml(q.answer) + ' <span style="font-size:0.8rem;color:var(--text-muted)">（他: ' + escapeHtml(q.choices.filter(c => c !== q.answer).join(', ')) + '）</span>';
        }
        return `<div class="qlist-item">
            <div class="qlist-item-header">
              <span class="qlist-type-badge">${q.type}</span>
              <span style="font-size:0.8rem;color:var(--text-muted)">難易度: ${q.difficulty}</span>
            </div>
            <div class="qlist-question">${escapeHtml(q.question)}</div>
            <div class="qlist-answer"><span style="font-weight:bold;color:var(--correct)">正解:</span> ${ansText}</div>
          </div>`;
      }).join('');
    }
    UI.openModal('modal-question-list');
  }

  function startQuiz(subjectId, unitId, typeFilter, diffFilter) {
    let pool = allQuestions.filter(q => q.subjectId === subjectId);
    if (unitId && unitId !== 'all') pool = pool.filter(q => q.unitId === unitId);
    if (typeFilter && typeFilter !== 'all') pool = pool.filter(q => q.type === typeFilter);
    if (diffFilter && diffFilter !== 'all') pool = pool.filter(q => q.difficulty === parseInt(diffFilter));

    if (pool.length === 0) { UI.showToast('該当する問題がありません', 'warning'); return; }

    const settings = Storage.getSettings();
    const count = Math.min(pool.length, settings.questionCount);
    const shuffled = shuffleArray(pool).slice(0, count);

    currentQuiz = { questions: shuffled, currentIndex: 0, answers: [], subjectId: subjectId, config: { unitId, typeFilter, diffFilter } };

    const subj = subjects.find(s => s.id === subjectId);
    document.getElementById('quiz-subject-name').textContent = subj ? subj.name : '';
    const unit = subj ? subj.units.find(u => u.id === unitId) : null;
    document.getElementById('quiz-unit-name').textContent = unit ? '/ ' + unit.name : '';

    UI.navigateTo('quiz', { onEnter: () => renderQuestion() });
  }

  function quickStart() {
    if (allQuestions.length === 0) { UI.showToast('問題がありません', 'warning'); return; }
    const settings = Storage.getSettings();
    const count = Math.min(allQuestions.length, settings.questionCount);
    const shuffled = shuffleArray(allQuestions).slice(0, count);
    currentQuiz = { questions: shuffled, currentIndex: 0, answers: [], subjectId: 'mixed', config: {} };
    document.getElementById('quiz-subject-name').textContent = 'ランダム出題';
    document.getElementById('quiz-unit-name').textContent = '';
    UI.navigateTo('quiz', { onEnter: () => renderQuestion() });
  }

  function startWrongReview() {
    const wrongIds = Storage.getWrongQuestionIds();
    if (wrongIds.length === 0) { UI.showToast('間違えた問題はありません', 'info'); return; }
    const pool = allQuestions.filter(q => wrongIds.includes(q.id));
    if (pool.length === 0) { UI.showToast('該当する問題が見つかりません', 'warning'); return; }
    const shuffled = shuffleArray(pool);
    currentQuiz = { questions: shuffled, currentIndex: 0, answers: [], subjectId: 'review', config: {} };
    document.getElementById('quiz-subject-name').textContent = '間違い復習';
    document.getElementById('quiz-unit-name').textContent = shuffled.length + '問';
    UI.navigateTo('quiz', { onEnter: () => renderQuestion() });
  }

  function renderQuestion() {
    const q = currentQuiz.questions[currentQuiz.currentIndex];
    if (!q) { showResults(); return; }
    UI.updateProgress(currentQuiz.currentIndex + 1, currentQuiz.questions.length);
    document.getElementById('quiz-feedback').classList.add('hidden');
    document.getElementById('quiz-actions').classList.add('hidden');
    const area = document.getElementById('quiz-area');
    const typeLabel = { '選択': '選択問題', '記述': '記述問題', '○×': '○×問題' };
    let html = '<div class="card quiz-question-card"><div class="question-type">' + (typeLabel[q.type] || q.type) + '</div><div class="question-text">' + escapeHtml(q.question) + '</div>';

    if (q.type === '選択') {
      html += '<div class="choices-list">' + q.choices.map((c, i) => '<button class="choice-btn" data-choice="' + escapeAttr(c) + '" onclick="App.selectChoice(this)">' + escapeHtml(c) + '</button>').join('') + '</div>';
    } else if (q.type === '○×') {
      html += '<div class="tf-buttons"><button class="tf-btn" data-tf="○" onclick="App.selectTF(this)">○</button><button class="tf-btn" data-tf="×" onclick="App.selectTF(this)">×</button></div>';
    } else {
      html += '<div class="answer-input"><input type="text" class="input" id="answer-text" placeholder="回答を入力..." onkeydown="if(event.key===\'Enter\')App.submitAnswer()"><button class="btn btn-primary btn-block mt-8" onclick="App.submitAnswer()">回答する</button></div>';
    }
    html += '</div>';
    area.innerHTML = html;
  }

  function selectChoice(btn) {
    if (btn.classList.contains('correct') || btn.classList.contains('incorrect')) return;
    document.querySelectorAll('.choice-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    checkAnswer(btn.dataset.choice);
  }

  function selectTF(btn) {
    if (btn.classList.contains('correct') || btn.classList.contains('incorrect')) return;
    document.querySelectorAll('.tf-btn').forEach(b => { b.classList.remove('selected-o', 'selected-x'); });
    btn.classList.add(btn.dataset.tf === '○' ? 'selected-o' : 'selected-x');
    checkAnswer(btn.dataset.tf);
  }

  function submitAnswer() {
    const input = document.getElementById('answer-text');
    if (!input) return;
    const value = input.value.trim();
    if (!value) { UI.showToast('回答を入力してください', 'warning'); return; }
    checkAnswer(value);
  }

  function checkAnswer(userAnswer) {
    const q = currentQuiz.questions[currentQuiz.currentIndex];
    let isCorrect = false;

    if (q.type === '記述') {
      const normalize = s => s.replace(/\s+/g, '').toLowerCase();
      isCorrect = normalize(userAnswer) === normalize(q.answer);
      if (!isCorrect && q.alternativeAnswers) {
        isCorrect = q.alternativeAnswers.some(a => normalize(userAnswer) === normalize(a));
      }
    } else {
      isCorrect = userAnswer === q.answer;
    }

    currentQuiz.answers.push({ questionId: q.id, userAnswer, correct: isCorrect });
    Storage.addHistoryEntry({ subjectId: q.subjectId, questionId: q.id, correct: isCorrect, type: q.type });
    if (!isCorrect) { Storage.addWrongAnswer(q.id, q.subjectId); } else { Storage.removeWrongAnswer(q.id); }

    showFeedback(q, isCorrect, userAnswer);
  }

  function showFeedback(q, isCorrect, userAnswer) {
    // ボタンの色を変える
    if (q.type === '選択') {
      document.querySelectorAll('.choice-btn').forEach(b => {
        if (b.dataset.choice === q.answer) b.classList.add('correct');
        else if (b.dataset.choice === userAnswer && !isCorrect) b.classList.add('incorrect');
        b.style.pointerEvents = 'none';
      });
    } else if (q.type === '○×') {
      document.querySelectorAll('.tf-btn').forEach(b => {
        b.classList.remove('selected-o', 'selected-x');
        if (b.dataset.tf === q.answer) b.classList.add('correct');
        else if (b.dataset.tf === userAnswer && !isCorrect) b.classList.add('incorrect');
        b.style.pointerEvents = 'none';
      });
    }

    const settings = Storage.getSettings();
    const fb = document.getElementById('quiz-feedback');
    fb.classList.remove('hidden');
    let html = '<div style="text-align:center;margin-top:16px"><span style="font-size:2rem">' + (isCorrect ? '🎉' : '😢') + '</span><div style="font-size:1.2rem;font-weight:700;margin-top:8px;color:' + (isCorrect ? 'var(--correct)' : 'var(--incorrect)') + '">' + (isCorrect ? '正解！' : '不正解') + '</div></div>';

    if (!isCorrect && q.type === '記述') {
      html += '<div style="text-align:center;margin-top:8px;color:var(--text-secondary)">正解: <strong>' + escapeHtml(q.answer) + '</strong></div>';
    }
    if (settings.showExplanation && q.explanation) {
      html += '<div class="explanation-box"><strong>解説:</strong> ' + escapeHtml(q.explanation) + '</div>';
    }
    fb.innerHTML = html;
    document.getElementById('quiz-actions').classList.remove('hidden');
    const isLast = currentQuiz.currentIndex >= currentQuiz.questions.length - 1;
    document.getElementById('btn-next-question').textContent = isLast ? '結果を見る' : '次の問題';
  }

  function nextQuestion() {
    currentQuiz.currentIndex++;
    if (currentQuiz.currentIndex >= currentQuiz.questions.length) { showResults(); return; }
    renderQuestion();
  }

  function quitQuiz() {
    UI.confirm('クイズを終了しますか？', () => {
      if (currentQuiz.answers.length > 0) showResults();
      else UI.navigateTo('home', { onEnter: renderHome });
    });
  }

  // === 結果画面 ===
  function showResults() {
    const total = currentQuiz.answers.length;
    const correct = currentQuiz.answers.filter(a => a.correct).length;
    const score = total > 0 ? Math.round(correct / total * 100) : 0;

    UI.navigateTo('results', {
      onEnter: () => {
        document.getElementById('result-circle').style.setProperty('--score', score);
        UI.animateCounter(document.getElementById('result-score'), score);
        document.getElementById('result-total').textContent = total;
        document.getElementById('result-correct').textContent = correct;
        document.getElementById('result-incorrect').textContent = total - correct;
        renderReviewList();
      }
    });
  }

  function renderReviewList() {
    const list = document.getElementById('result-review-list');
    list.innerHTML = currentQuiz.answers.map((a, i) => {
      const q = currentQuiz.questions[i];
      if (!q) return '';
      return '<div class="result-review-item ' + (a.correct ? 'was-correct' : 'was-incorrect') + '"><div style="display:flex;justify-content:space-between;align-items:center"><span style="font-weight:500">Q' + (i + 1) + '. ' + escapeHtml(q.question.substring(0, 60)) + (q.question.length > 60 ? '...' : '') + '</span><span style="font-size:1.2rem">' + (a.correct ? '✅' : '❌') + '</span></div>' +
        (!a.correct ? '<div style="margin-top:6px;font-size:.85rem"><span class="text-muted">あなたの回答:</span> ' + escapeHtml(a.userAnswer) + ' <span class="text-muted">→ 正解:</span> <strong>' + escapeHtml(q.answer) + '</strong></div>' : '') +
        (q.explanation ? '<div style="margin-top:4px;font-size:.8rem;color:var(--text-muted)">' + escapeHtml(q.explanation) + '</div>' : '') + '</div>';
    }).join('');
  }

  function retryQuiz() {
    currentQuiz.currentIndex = 0;
    currentQuiz.answers = [];
    currentQuiz.questions = shuffleArray(currentQuiz.questions);
    UI.navigateTo('quiz', { onEnter: renderQuestion });
  }

  function retryWrong() {
    const wrongQs = currentQuiz.answers.filter(a => !a.correct).map(a => currentQuiz.questions.find(q => q.id === a.questionId)).filter(Boolean);
    if (wrongQs.length === 0) { UI.showToast('間違えた問題はありません！', 'success'); return; }
    currentQuiz.questions = shuffleArray(wrongQs);
    currentQuiz.currentIndex = 0;
    currentQuiz.answers = [];
    UI.navigateTo('quiz', { onEnter: renderQuestion });
  }

  // === 問題自動生成 ===
  let currentGenMode = 'text';
  let uploadedFiles = [];

  function populateGenerateModal() {
    const sel = document.getElementById('gen-subject');
    sel.innerHTML = subjects.map(s => '<option value="' + s.id + '">' + s.name + '</option>').join('');
    sel.addEventListener('change', () => {
      const subj = subjects.find(s => s.id === sel.value);
      const unitSel = document.getElementById('gen-unit');
      unitSel.innerHTML = '<option value="">指定なし</option>' + (subj ? subj.units.map(u => '<option value="' + u.id + '">' + u.name + '</option>').join('') : '');
    });
    initFileDropZone();
  }

  function switchGenMode(mode) {
    currentGenMode = mode;
    document.querySelectorAll('.gen-mode-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.gen-mode-content').forEach(c => c.classList.remove('active'));
    const tab = mode === 'text' ? 0 : 1;
    document.querySelectorAll('.gen-mode-tab')[tab].classList.add('active');
    document.getElementById('gen-mode-' + mode).classList.add('active');
  }

  function initFileDropZone() {
    const dropZone = document.getElementById('file-drop-zone');
    if (!dropZone) return;
    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault(); e.stopPropagation();
      dropZone.classList.add('drag-over');
    });
    dropZone.addEventListener('dragleave', (e) => {
      e.preventDefault(); e.stopPropagation();
      dropZone.classList.remove('drag-over');
    });
    dropZone.addEventListener('drop', (e) => {
      e.preventDefault(); e.stopPropagation();
      dropZone.classList.remove('drag-over');
      const files = Array.from(e.dataTransfer.files);
      processFiles(files);
    });
  }

  function handleFileUpload(input) {
    const files = Array.from(input.files);
    processFiles(files);
    input.value = '';
  }

  function processFiles(files) {
    const textExts = ['.txt', '.csv', '.md', '.json', '.text'];
    const pdfExts = ['.pdf'];
    const docxExts = ['.docx'];
    const imageExts = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'];
    const allAllowed = [...textExts, ...pdfExts, ...docxExts, ...imageExts];

    files.forEach(file => {
      const ext = '.' + file.name.split('.').pop().toLowerCase();
      if (!allAllowed.includes(ext)) {
        UI.showToast(file.name + ' は対応していない形式です', 'warning');
        return;
      }
      if (uploadedFiles.some(f => f.name === file.name)) {
        UI.showToast(file.name + ' は既に追加されています', 'info');
        return;
      }

      // テキスト系ファイル
      if (textExts.includes(ext)) {
        const reader = new FileReader();
        reader.onload = (e) => {
          uploadedFiles.push({ name: file.name, size: file.size, content: e.target.result, ext: ext, status: 'ready' });
          renderAttachedFiles();
        };
        reader.readAsText(file);
      }
      // PDF
      else if (pdfExts.includes(ext)) {
        uploadedFiles.push({ name: file.name, size: file.size, content: '', ext: ext, status: 'processing' });
        renderAttachedFiles();
        extractPdfText(file, uploadedFiles.length - 1);
      }
      // DOCX
      else if (docxExts.includes(ext)) {
        uploadedFiles.push({ name: file.name, size: file.size, content: '', ext: ext, status: 'processing' });
        renderAttachedFiles();
        extractDocxText(file, uploadedFiles.length - 1);
      }
      // 画像 (OCR)
      else if (imageExts.includes(ext)) {
        uploadedFiles.push({ name: file.name, size: file.size, content: '', ext: ext, status: 'processing' });
        renderAttachedFiles();
        extractImageText(file, uploadedFiles.length - 1);
      }
    });
  }

  async function extractPdfText(file, index) {
    try {
      if (typeof pdfjsLib === 'undefined') {
        uploadedFiles[index].status = 'error';
        uploadedFiles[index].error = 'PDF.jsが読み込まれていません';
        renderAttachedFiles();
        UI.showToast('PDF.jsの読み込みに失敗しました', 'error');
        return;
      }
      pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
      const arrayBuffer = await file.arrayBuffer();
      const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
      let fullText = '';
      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        const pageText = textContent.items.map(item => item.str).join(' ');
        fullText += pageText + '\n';
      }
      uploadedFiles[index].content = fullText.trim();
      uploadedFiles[index].status = 'ready';
      renderAttachedFiles();
      UI.showToast(file.name + ' のテキストを抽出しました (' + pdf.numPages + 'ページ)', 'success');
    } catch (err) {
      console.error('PDF解析エラー:', err);
      uploadedFiles[index].status = 'error';
      uploadedFiles[index].error = 'PDF解析に失敗しました';
      renderAttachedFiles();
      UI.showToast(file.name + ' の解析に失敗しました', 'error');
    }
  }

  async function extractDocxText(file, index) {
    try {
      if (typeof mammoth === 'undefined') {
        uploadedFiles[index].status = 'error';
        uploadedFiles[index].error = 'mammoth.jsが読み込まれていません';
        renderAttachedFiles();
        UI.showToast('mammoth.jsの読み込みに失敗しました', 'error');
        return;
      }
      const arrayBuffer = await file.arrayBuffer();
      const result = await mammoth.extractRawText({ arrayBuffer: arrayBuffer });
      uploadedFiles[index].content = result.value.trim();
      uploadedFiles[index].status = 'ready';
      renderAttachedFiles();
      UI.showToast(file.name + ' のテキストを抽出しました', 'success');
    } catch (err) {
      console.error('DOCX解析エラー:', err);
      uploadedFiles[index].status = 'error';
      uploadedFiles[index].error = 'DOCX解析に失敗しました';
      renderAttachedFiles();
      UI.showToast(file.name + ' の解析に失敗しました', 'error');
    }
  }

  async function extractImageText(file, index) {
    try {
      const formData = new FormData();
      formData.append('image', file);
      const res = await fetch('/api/ocr', { method: 'POST', body: formData });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || 'OCRサーバーエラー (HTTP ' + res.status + ')');
      }
      const data = await res.json();
      uploadedFiles[index].content = data.text || '';
      uploadedFiles[index].status = 'ready';
      renderAttachedFiles();
      UI.showToast(file.name + ' のOCR処理が完了しました', 'success');
    } catch (err) {
      console.error('OCRエラー:', err);
      uploadedFiles[index].status = 'error';
      uploadedFiles[index].error = err.message || 'OCR処理に失敗しました。server.py が起動しているか確認してください。';
      renderAttachedFiles();
      UI.showToast('OCR失敗: ' + (err.message || '接続エラー'), 'error');
    }
  }

  function renderAttachedFiles() {
    const container = document.getElementById('attached-files');
    if (!container) return;
    const fileIcons = {
      '.txt': '📄', '.csv': '📊', '.md': '📝', '.json': '🔧', '.text': '📄',
      '.pdf': '📕', '.docx': '📘', '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️',
      '.bmp': '🖼️', '.tiff': '🖼️', '.tif': '🖼️'
    };
    const statusLabels = {
      'ready': '<span style="color:var(--correct);font-size:0.75rem">✓ 準備完了</span>',
      'processing': '<span style="color:var(--warning);font-size:0.75rem">⏳ 処理中...</span>',
      'error': '<span style="color:var(--incorrect);font-size:0.75rem">✕ エラー</span>'
    };
    container.innerHTML = uploadedFiles.map((f, i) => {
      const icon = fileIcons[f.ext] || '📄';
      const sizeStr = f.size < 1024 ? f.size + ' B' : (f.size / 1024).toFixed(1) + ' KB';
      const status = statusLabels[f.status] || '';
      const errorMsg = f.error ? '<div style="font-size:0.7rem;color:var(--incorrect);margin-top:2px">' + escapeHtml(f.error) + '</div>' : '';
      return '<div class="attached-file' + (f.status === 'processing' ? ' processing' : '') + '">' +
        '<span class="file-icon">' + icon + '</span>' +
        '<div class="file-info"><div class="file-name">' + escapeHtml(f.name) + '</div><div class="file-size">' + sizeStr + ' ' + status + '</div>' + errorMsg + '</div>' +
        '<button class="file-remove" onclick="App.removeFile(' + i + ')" title="削除">✕</button></div>';
    }).join('');
  }

  function removeFile(index) {
    uploadedFiles.splice(index, 1);
    renderAttachedFiles();
  }

  function generateQuestions() {
    let text = '';
    if (currentGenMode === 'text') {
      text = document.getElementById('gen-text').value.trim();
      if (!text) { UI.showToast('テキストを入力してください', 'warning'); return; }
    } else {
      if (uploadedFiles.length === 0) { UI.showToast('ファイルをアップロードしてください', 'warning'); return; }
      const processing = uploadedFiles.filter(f => f.status === 'processing');
      if (processing.length > 0) { UI.showToast(processing.length + '個のファイルを処理中です。しばらくお待ちください', 'info'); return; }
      const readyFiles = uploadedFiles.filter(f => f.status === 'ready' && f.content);
      if (readyFiles.length === 0) { UI.showToast('テキストを抽出できたファイルがありません', 'warning'); return; }
      text = readyFiles.map(f => f.content).join('\n\n');
    }

    const subjectId = document.getElementById('gen-subject').value;
    const unitId = document.getElementById('gen-unit').value;
    const checkboxes = document.querySelectorAll('#modal-generate input[type=checkbox]:checked');
    const types = Array.from(checkboxes).map(cb => cb.value);
    if (types.length === 0) { UI.showToast('問題タイプを選択してください', 'warning'); return; }

    const generated = QuestionGenerator.generateFromText(text, subjectId, unitId, { types, count: 30 });
    if (generated.length === 0) { UI.showToast('問題を生成できませんでした。テキスト形式を確認してください', 'error'); return; }

    // プレビュー表示
    const preview = document.getElementById('gen-preview');
    preview.classList.remove('hidden');
    preview.innerHTML = '<h3 style="margin-bottom:12px">🎉 ' + generated.length + '問 生成されました</h3>' +
      '<div style="max-height:300px;overflow-y:auto;padding-right:8px">' +
      generated.slice(0, 8).map(q => '<div style="padding:10px;border-bottom:1px solid var(--border);font-size:.85rem"><span class="qlist-type-badge" style="font-size:.7rem;padding:3px 10px;margin-right:8px">' + q.type + '</span>' + escapeHtml(q.question) + '</div>').join('') +
      (generated.length > 8 ? '<div class="text-muted" style="padding:10px;font-size:.85rem">他 ' + (generated.length - 8) + '問...</div>' : '') +
      '</div>' +
      '<button class="btn btn-success btn-block mt-8" onclick="App.saveGeneratedQuestions()">💾 保存して追加</button>';

    window._pendingGenerated = generated;
  }

  function saveGeneratedQuestions() {
    if (!window._pendingGenerated) return;
    Storage.addCustomQuestions(window._pendingGenerated);
    allQuestions = allQuestions.concat(window._pendingGenerated);
    UI.showToast(window._pendingGenerated.length + '問を追加しました！', 'success');
    UI.closeModal('modal-generate');
    document.getElementById('gen-text').value = '';
    document.getElementById('gen-preview').classList.add('hidden');
    uploadedFiles = [];
    renderAttachedFiles();
    window._pendingGenerated = null;
    renderSubjects();
  }

  // === 設定 ===
  function initSettings() {
    const s = Storage.getSettings();
    document.getElementById('toggle-theme').classList.toggle('active', s.theme === 'dark');
    document.getElementById('toggle-explanation').classList.toggle('active', s.showExplanation !== false);
    document.getElementById('setting-count').value = s.questionCount || 10;
    document.getElementById('storage-usage').textContent = Storage.getStorageUsage().formatted;
  }

  function toggleTheme(el) {
    const theme = UI.toggleTheme();
    el.classList.toggle('active', theme === 'dark');
  }

  function toggleSetting(el, key) {
    const s = Storage.getSettings();
    s[key] = !s[key];
    Storage.saveSettings(s);
    el.classList.toggle('active', s[key]);
  }

  function updateQuestionCount(val) {
    const s = Storage.getSettings();
    s.questionCount = parseInt(val);
    Storage.saveSettings(s);
  }

  function exportData() {
    const data = Storage.exportData();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'studyquest_backup_' + new Date().toISOString().slice(0, 10) + '.json';
    a.click();
    URL.revokeObjectURL(a.href);
    UI.showToast('データをエクスポートしました', 'success');
  }

  function importData(input) {
    const file = input.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result);
        Storage.importData(data);
        UI.showToast('データをインポートしました', 'success');
        renderHome();
        initSettings();
      } catch (err) {
        UI.showToast('ファイルの読み込みに失敗しました', 'error');
      }
    };
    reader.readAsText(file);
    input.value = '';
  }

  function clearAllData() {
    UI.confirm('すべてのデータを削除しますか？この操作は取り消せません。', () => {
      Storage.clearAllData();
      UI.showToast('データを削除しました', 'info');
      renderHome();
      initSettings();
    });
  }

  // === ナビゲーション ===
  function onNavigate(screen) {
    if (screen === 'home') renderHome();
    if (screen === 'subjects') renderSubjects();
    if (screen === 'settings') { initSettings(); document.getElementById('storage-usage').textContent = Storage.getStorageUsage().formatted; }
  }

  // === ユーティリティ ===
  function shuffleArray(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
    return a;
  }
  function escapeHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
  function escapeAttr(s) { return s.replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }

  // === 起動 ===
  document.addEventListener('DOMContentLoaded', init);

  // === 単語一覧 ===
  let vocabData = {};

  async function openVocabList() {
    const subj = subjects.find(s => s.id === selectedSubjectId);
    if (!subj) return;
    const file = selectedSubjectId === 'bricks1' ? 'data/vocab_bricks1.json' : 'data/vocab_kobun330.json';
    try {
      const res = await fetch(file + '?t=' + Date.now());
      vocabData = await res.json();
    } catch(e) { UI.showToast('単語データを読み込めませんでした', 'error'); return; }

    document.getElementById('vocab-title').textContent = subj.name + ' - 単語一覧';
    const unitSel = document.getElementById('vocab-unit-select');
    unitSel.innerHTML = '<option value="all">すべて</option>' + subj.units.map(u => '<option value="' + u.id + '">' + u.name + '</option>').join('');
    renderVocabUnit();
    UI.openModal('modal-vocab-list');
  }

  function renderVocabUnit() {
    const unitId = document.getElementById('vocab-unit-select').value;
    const subj = subjects.find(s => s.id === selectedSubjectId);
    const container = document.getElementById('vocab-container');
    const statsEl = document.getElementById('vocab-stats');
    let html = '';
    let totalCount = 0;

    const unitsToShow = unitId === 'all' ? Object.keys(vocabData.units) : [unitId];
    const isBricks = selectedSubjectId === 'bricks1';

    for (const uid of unitsToShow) {
      const words = vocabData.units[uid];
      if (!words) continue;
      const unitInfo = subj ? subj.units.find(u => u.id === uid) : null;
      const unitName = unitInfo ? unitInfo.name : uid;
      totalCount += words.length;

      html += '<div class="vocab-unit-section">';
      html += '<h3 class="vocab-unit-title">' + escapeHtml(unitName) + ' <span class="text-muted" style="font-size:0.85rem;font-weight:400">(' + words.length + '語)</span></h3>';
      html += '<div class="vocab-table"><div class="vocab-table-header"><span>' + (isBricks ? '英単語' : '古語') + '</span><span>' + (isBricks ? '意味' : '現代語訳') + '</span></div>';
      for (const [word, meaning] of words) {
        html += '<div class="vocab-row"><span class="vocab-word">' + escapeHtml(word) + '</span><span class="vocab-meaning">' + escapeHtml(meaning) + '</span></div>';
      }
      html += '</div></div>';
    }

    statsEl.textContent = '全 ' + totalCount + ' 語';
    container.innerHTML = html || '<p class="text-muted" style="text-align:center;padding:20px">該当する単語がありません</p>';
  }

  return {
    quickStart, startWrongReview, openSubjectSetup, setQuizType, setDifficulty,
    startQuizFromSetup, openQuestionList, selectChoice, selectTF, submitAnswer, nextQuestion, quitQuiz,
    retryQuiz, retryWrong, generateQuestions, saveGeneratedQuestions,
    toggleTheme, toggleSetting, updateQuestionCount,
    exportData, importData, clearAllData, filterCategory, onNavigate,
    openVocabList, renderVocabUnit,
    switchGenMode, handleFileUpload, removeFile
  };
})();
