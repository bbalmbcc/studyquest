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
  let questionEditMode = false;

  // === 初期化 ===
  async function init() {
    UI.init();
    await loadData();
    renderHome();
    renderSubjects();
    initSettings();
    populateGenerateModal();
    // 起動時にバックグラウンドでサーバー同期
    silentSync();
  }

  async function loadData() {
    try {
      const [subRes, qRes] = await Promise.all([
        fetch('data/subjects.json?t=' + Date.now()).then(r => r.json()),
        fetch('data/questions.json?t=' + Date.now()).then(r => r.json())
      ]);
      subjects = subRes.subjects || [];
      allQuestions = qRes.questions || [];
      // カスタム問題を追加（サーバーにまだ反映されていないもの）
      const custom = Storage.getCustomQuestions();
      const serverIds = new Set(allQuestions.map(q => q.id));
      for (const cq of custom) {
        if (!serverIds.has(cq.id)) allQuestions.push(cq);
      }
    } catch (e) {
      console.error('データ読み込みエラー:', e);
      UI.showToast('データの読み込みに失敗しました', 'error');
    }
  }

  // バックグラウンド同期（起動時・保存時に自動実行）
  async function silentSync() {
    try {
      const customQs = Storage.getCustomQuestions();
      const res = await fetch('/api/questions/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ questions: customQs })
      });
      if (!res.ok) return;
      const data = await res.json();
      const serverQuestions = data.questions || [];
      const serverIds = new Set(serverQuestions.map(q => q.id));
      allQuestions = serverQuestions.slice();
      // ローカルにしかない問題も保持
      for (const cq of customQs) {
        if (!serverIds.has(cq.id)) allQuestions.push(cq);
      }
      if (data.added > 0) {
        console.log(`[Sync] サーバーに${data.added}問追加, 合計${data.total}問`);
      }
      renderSubjects();
    } catch (e) {
      // サーバー未接続時は無視
      console.log('[Sync] サーバーに接続できません（オフラインモード）');
    }
  }

  // カスタム問題をサーバーにプッシュ
  async function pushToServer(questions) {
    try {
      await fetch('/api/questions/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ questions })
      });
    } catch (e) { console.warn('[Sync] プッシュ失敗:', e); }
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

    // 教科別正答率
    renderSubjectAccuracy();

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
    questionEditMode = false;
    const editBtn = document.getElementById('btn-qlist-edit');
    if (editBtn) { editBtn.textContent = '🗑️ 編集'; editBtn.classList.remove('active'); }
    
    renderQuestionList(pool);
    UI.openModal('modal-question-list');
  }

  function renderQuestionList(pool) {
    if (!pool) {
      // 現在のフィルター条件で再取得
      const unitId = document.getElementById('setup-unit') ? document.getElementById('setup-unit').value : 'all';
      pool = allQuestions.filter(q => q.subjectId === selectedSubjectId);
      if (unitId && unitId !== 'all') pool = pool.filter(q => q.unitId === unitId);
      if (quizTypeFilter && quizTypeFilter !== 'all') pool = pool.filter(q => q.type === quizTypeFilter);
      if (difficultyFilter && difficultyFilter !== 'all') pool = pool.filter(q => q.difficulty === parseInt(difficultyFilter));
    }
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
        const deleteBtn = questionEditMode ? `<button class="btn-delete-question" onclick="event.stopPropagation();App.deleteQuestion('${escapeAttr(q.id)}')" title="この問題を削除">✕</button>` : '';
        const editBtn2 = questionEditMode ? `<button class="btn-edit-question" onclick="event.stopPropagation();App.openEditQuestion('${escapeAttr(q.id)}')" title="この問題を編集">✏️</button>` : '';
        return `<div class="qlist-item ${questionEditMode ? 'edit-mode' : ''}" data-qid="${escapeAttr(q.id)}">
            <div class="qlist-item-header">
              <div style="display:flex;align-items:center;gap:8px">
                <span class="qlist-type-badge">${q.type}</span>
                <span style="font-size:0.8rem;color:var(--text-muted)">難易度: ${q.difficulty}</span>
              </div>
              <div style="display:flex;gap:6px">${editBtn2}${deleteBtn}</div>
            </div>
            <div class="qlist-question">${escapeHtml(q.question)}</div>
            <div class="qlist-answer"><span style="font-weight:bold;color:var(--correct)">正解:</span> ${ansText}</div>
          </div>`;
      }).join('');
    }
  }

  function toggleQuestionEditMode() {
    questionEditMode = !questionEditMode;
    const editBtn = document.getElementById('btn-qlist-edit');
    if (editBtn) {
      editBtn.textContent = questionEditMode ? '✓ 完了' : '🗑️ 編集';
      if (questionEditMode) editBtn.classList.add('active');
      else editBtn.classList.remove('active');
    }
    renderQuestionList(null);
  }

  async function deleteQuestion(questionId) {
    if (!questionId) return;
    const q = allQuestions.find(qItem => qItem.id === questionId);
    const qText = q ? q.question.substring(0, 40) + (q.question.length > 40 ? '...' : '') : questionId;
    UI.confirm('「' + qText + '」を削除しますか？', async () => {
      // カスタム問題の場合はlocalStorageから削除
      const customQs = Storage.getCustomQuestions();
      const isCustom = customQs.some(cq => cq.id === questionId);
      if (isCustom) {
        Storage.deleteCustomQuestion(questionId);
      }
      // サーバーAPIで削除を試みる
      try {
        const res = await fetch('/api/questions/' + encodeURIComponent(questionId), { method: 'DELETE' });
        if (res.ok) {
          // サーバー側も削除成功
        }
      } catch (e) {
        // サーバーに接続できない場合は無視（ローカルのみ削除）
        console.warn('サーバー削除失敗（オフライン）:', e);
      }
      // メモリ上の問題リストから削除
      allQuestions = allQuestions.filter(qItem => qItem.id !== questionId);
      UI.showToast('問題を削除しました', 'success');
      renderQuestionList(null);
      updateFilterSummary();
    });
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

  // === 間違い復習（教科別） ===
  function openWrongReviewModal() {
    const wrongIds = Storage.getWrongQuestionIds();
    if (wrongIds.length === 0) { UI.showToast('間違えた問題はありません', 'info'); return; }
    const list = document.getElementById('wrong-review-list');
    // 教科ごとに間違い数を集計
    const wrongAnswers = Storage.getWrongAnswers();
    const subjectCounts = {};
    Object.values(wrongAnswers).forEach(w => {
      const sid = w.subjectId || 'unknown';
      subjectCounts[sid] = (subjectCounts[sid] || 0) + 1;
    });
    const subjectMap = {};
    subjects.forEach(s => subjectMap[s.id] = s);

    let html = '<button class="wrong-review-item" onclick="App.startWrongReview(null)">' +
      '<div class="wrong-review-icon" style="background:var(--accent)">\u2728</div>' +
      '<div class="wrong-review-info"><div class="wrong-review-name">すべての教科</div><div class="wrong-review-count">' + wrongIds.length + '問</div></div>' +
      '<div class="wrong-review-arrow">\u2192</div></button>';

    Object.keys(subjectCounts).sort((a, b) => subjectCounts[b] - subjectCounts[a]).forEach(sid => {
      const subj = subjectMap[sid];
      if (!subj) return;
      const color = getCategoryColor(subj.category);
      const emoji = getCategoryEmoji(subj.category);
      html += '<button class="wrong-review-item" onclick="App.startWrongReview(\'' + sid + '\')">' +
        '<div class="wrong-review-icon" style="background:' + color + '">' + emoji + '</div>' +
        '<div class="wrong-review-info"><div class="wrong-review-name">' + subj.name + '</div><div class="wrong-review-count">' + subjectCounts[sid] + '問</div></div>' +
        '<div class="wrong-review-arrow">\u2192</div></button>';
    });
    list.innerHTML = html;
    UI.openModal('modal-wrong-review');
  }

  function startWrongReview(subjectId) {
    UI.closeModal('modal-wrong-review');
    const wrongIds = subjectId ? Storage.getWrongQuestionIds(subjectId) : Storage.getWrongQuestionIds();
    if (wrongIds.length === 0) { UI.showToast('間違えた問題はありません', 'info'); return; }
    const pool = allQuestions.filter(q => wrongIds.includes(q.id));
    if (pool.length === 0) { UI.showToast('該当する問題が見つかりません', 'warning'); return; }
    const shuffled = shuffleArray(pool);
    currentQuiz = { questions: shuffled, currentIndex: 0, answers: [], subjectId: subjectId || 'review', config: {} };
    const subj = subjectId ? subjects.find(s => s.id === subjectId) : null;
    document.getElementById('quiz-subject-name').textContent = '間違い復習' + (subj ? ' - ' + subj.name : '');
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
    const tabIndex = mode === 'text' ? 0 : mode === 'file' ? 1 : 2;
    document.querySelectorAll('.gen-mode-tab')[tabIndex].classList.add('active');
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
    if (currentGenMode === 'web') {
      text = window._webSearchText || '';
      if (!text) { UI.showToast('まず検索を実行してください', 'warning'); return; }
    } else if (currentGenMode === 'text') {
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
    // サーバーに自動プッシュ（他デバイスでも使えるように）
    pushToServer(window._pendingGenerated);
    window._pendingGenerated = null;
    renderSubjects();
  }

  // === 設定 ===
  function initSettings() {
    const s = Storage.getSettings();
    document.getElementById('toggle-theme').classList.toggle('active', s.theme === 'dark');
    document.getElementById('toggle-explanation').classList.toggle('active', s.showExplanation !== false);
    const count = s.questionCount || 10;
    const numEl = document.getElementById('setting-count-num');
    const rangeEl = document.getElementById('setting-count-range');
    if (numEl) numEl.value = count;
    if (rangeEl) rangeEl.value = Math.min(count, 200);
    document.getElementById('storage-usage').textContent = Storage.getStorageUsage().formatted;
    renderApiKeyStatus();
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

  // === デバイス間同期 ===
  async function syncQuestions() {
    const statusEl = document.getElementById('sync-status');
    const syncBtn = document.getElementById('btn-sync');
    if (syncBtn) syncBtn.disabled = true;
    if (statusEl) statusEl.textContent = '🔄 同期中...';
    try {
      // 1. ローカルのカスタム問題をサーバーに送信
      const customQs = Storage.getCustomQuestions();
      const res = await fetch('/api/questions/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ questions: customQs })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || 'HTTP ' + res.status);
      }
      const data = await res.json();
      // 2. サーバーから最新の問題リストを取得して反映
      const serverQuestions = data.questions || [];
      allQuestions = serverQuestions.slice();
      // カスタム問題もマージ（サーバーにない場合の保険）
      const serverIds = new Set(serverQuestions.map(q => q.id));
      for (const cq of customQs) {
        if (!serverIds.has(cq.id)) {
          allQuestions.push(cq);
        }
      }
      if (statusEl) statusEl.textContent = `✅ 同期完了！ サーバーから${data.added || 0}問追加 / 合計${data.total}問`;
      UI.showToast(`同期完了: ${data.total}問`, 'success');
      renderSubjects();
    } catch (e) {
      console.error('同期エラー:', e);
      if (statusEl) statusEl.textContent = '❌ 同期失敗: ' + (e.message || String(e));
      // フォールバック: サーバーに接続できない場合、直接JSONを再読込
      try {
        const [qRes] = await Promise.all([
          fetch('data/questions.json?t=' + Date.now()).then(r => r.json())
        ]);
        const serverQs = qRes.questions || [];
        const custom = Storage.getCustomQuestions();
        const serverIds = new Set(serverQs.map(q => q.id));
        allQuestions = serverQs.slice();
        for (const cq of custom) {
          if (!serverIds.has(cq.id)) allQuestions.push(cq);
        }
        if (statusEl) statusEl.textContent = '⚠️ API未接続。ファイルから再読込しました（' + allQuestions.length + '問）';
        UI.showToast('ファイルから再読込しました', 'info');
        renderSubjects();
      } catch (e2) {
        UI.showToast('同期に失敗しました', 'error');
      }
    } finally {
      if (syncBtn) syncBtn.disabled = false;
    }
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

  // === 教科別正答率 ===
  function renderSubjectAccuracy() {
    const subjectStats = Storage.getSubjectStats();
    const el = document.getElementById('subject-accuracy-list');
    const statsEntries = subjects.map(s => {
      const st = subjectStats[s.id];
      if (!st || st.total === 0) return null;
      return { subject: s, stats: st };
    }).filter(Boolean);

    if (statsEntries.length === 0) {
      el.innerHTML = '<p class="text-muted" style="padding:20px;text-align:center">まだ学習記録がありません</p>';
      return;
    }

    el.innerHTML = statsEntries.map(e => {
      const color = getCategoryColor(e.subject.category);
      return '<div class="accuracy-item">' +
        '<div class="accuracy-header">' +
        '<span class="accuracy-name" style="color:' + color + '">' + e.subject.name + '</span>' +
        '<span class="accuracy-rate">' + e.stats.rate + '%</span>' +
        '</div>' +
        '<div class="accuracy-bar"><div class="accuracy-bar-fill" style="width:' + e.stats.rate + '%;background:' + color + '"></div></div>' +
        '<div class="accuracy-detail text-muted">' + e.stats.correct + ' / ' + e.stats.total + ' 正解</div>' +
        '</div>';
    }).join('');
  }

  // === Gemini API + Search Grounding 問題生成 ===
  const GEMINI_API_KEY_STORAGE = 'studyquest_geminiApiKey';
  const GEMINI_MODEL = 'gemini-2.5-flash';

  function getGeminiApiKey() {
    return localStorage.getItem(GEMINI_API_KEY_STORAGE) || '';
  }

  function setGeminiApiKey(key) {
    if (key) {
      localStorage.setItem(GEMINI_API_KEY_STORAGE, key.trim());
    } else {
      localStorage.removeItem(GEMINI_API_KEY_STORAGE);
    }
    renderApiKeyStatus();
  }

  function getGeminiEndpoint() {
    const key = getGeminiApiKey();
    if (!key) return null;
    return `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${key}`;
  }

  function renderApiKeyStatus() {
    const container = document.getElementById('api-key-status');
    if (!container) return;
    const key = getGeminiApiKey();
    if (key) {
      const masked = key.slice(0, 8) + '••••••••' + key.slice(-4);
      container.innerHTML = '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">' +
        '<span style="color:var(--correct);font-weight:600">✅ 設定済み</span>' +
        '<code style="font-size:0.8rem;background:rgba(255,255,255,0.05);padding:4px 10px;border-radius:6px;color:var(--text-muted)">' + escapeHtml(masked) + '</code>' +
        '<button class="btn btn-sm btn-danger" onclick="App.deleteApiKey()" style="padding:6px 14px;font-size:0.8rem">🗑️ 削除</button>' +
        '</div>';
    } else {
      container.innerHTML = '<span style="color:var(--warning);font-weight:600">⚠️ 未設定 — AI検索を使用するにはAPIキーを入力してください</span>';
    }
  }

  function saveApiKeyFromInput() {
    const input = document.getElementById('api-key-input');
    if (!input) return;
    const key = input.value.trim();
    if (!key) { UI.showToast('APIキーを入力してください', 'warning'); return; }
    if (!key.startsWith('AIza')) { UI.showToast('無効なAPIキー形式です', 'error'); return; }
    setGeminiApiKey(key);
    input.value = '';
    UI.showToast('APIキーを保存しました', 'success');
  }

  function deleteApiKey() {
    UI.confirm('Gemini APIキーを削除しますか？AI検索機能が使えなくなります。', () => {
      setGeminiApiKey(null);
      UI.showToast('APIキーを削除しました', 'info');
    });
  }
  const SEARCH_COUNT_KEY = 'studyquest_geminiSearchCount';
  const SEARCH_RPM_KEY = 'studyquest_geminiRPM';
  const DAILY_LIMIT = 1500;  // 無料枠: 1日1500リクエスト
  const RPM_LIMIT = 15;      // 無料枠: 1分間15リクエスト

  function getSearchCount() {
    const data = JSON.parse(localStorage.getItem(SEARCH_COUNT_KEY) || '{}');
    const today = new Date().toISOString().slice(0, 10);
    if (data.date !== today) return { date: today, count: 0 };
    return data;
  }

  function incrementSearchCount() {
    const data = getSearchCount();
    data.count++;
    localStorage.setItem(SEARCH_COUNT_KEY, JSON.stringify(data));
    // RPM追跡
    const now = Date.now();
    const rpmData = JSON.parse(localStorage.getItem(SEARCH_RPM_KEY) || '[]');
    rpmData.push(now);
    // 1分以上前のものを除去
    const filtered = rpmData.filter(t => now - t < 60000);
    localStorage.setItem(SEARCH_RPM_KEY, JSON.stringify(filtered));
    updateSearchRemaining();
  }

  function checkRPMLimit() {
    const now = Date.now();
    const rpmData = JSON.parse(localStorage.getItem(SEARCH_RPM_KEY) || '[]');
    const recent = rpmData.filter(t => now - t < 60000);
    return recent.length < RPM_LIMIT;
  }

  function getRPMWaitTime() {
    const now = Date.now();
    const rpmData = JSON.parse(localStorage.getItem(SEARCH_RPM_KEY) || '[]');
    const recent = rpmData.filter(t => now - t < 60000);
    if (recent.length < RPM_LIMIT) return 0;
    const oldest = Math.min(...recent);
    return Math.ceil((oldest + 60000 - now) / 1000);
  }

  function updateSearchRemaining() {
    const data = getSearchCount();
    const remaining = Math.max(0, DAILY_LIMIT - data.count);
    const el = document.getElementById('web-search-remaining');
    if (el) el.textContent = remaining;
    const rpmEl = document.getElementById('web-search-rpm');
    if (rpmEl) {
      const now = Date.now();
      const rpmData = JSON.parse(localStorage.getItem(SEARCH_RPM_KEY) || '[]');
      const recentCount = rpmData.filter(t => now - t < 60000).length;
      rpmEl.textContent = Math.max(0, RPM_LIMIT - recentCount);
    }
  }

  async function callGeminiAPI(prompt, useGrounding, statusEl) {
    const requestBody = {
      contents: [{
        role: 'user',
        parts: [{ text: prompt }]
      }],
      generationConfig: {
        temperature: 0.3,
        maxOutputTokens: 4096
      }
    };
    if (useGrounding) {
      requestBody.tools = [{ google_search: {} }];
    }

    const maxRetries = 3;
    const baseDelay = 5000; // 5秒

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      if (attempt > 0) {
        const delay = baseDelay * Math.pow(2, attempt - 1); // 5s, 10s, 20s
        const delaySec = Math.round(delay / 1000);
        if (statusEl) {
          statusEl.innerHTML = '<div class="web-search-loading"><div class="spinner"></div> レート制限中... ' + delaySec + '秒後にリトライします (試行 ' + (attempt + 1) + '/' + (maxRetries + 1) + ')</div>';
        }
        await new Promise(r => setTimeout(r, delay));
        if (statusEl) {
          statusEl.innerHTML = '<div class="web-search-loading"><div class="spinner"></div> リトライ中... (試行 ' + (attempt + 1) + '/' + (maxRetries + 1) + ')</div>';
        }
      }

      const endpoint = getGeminiEndpoint();
      if (!endpoint) throw { status: 0, message: 'APIキーが設定されていません。設定画面でAPIキーを入力してください。' };
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      if (res.ok) {
        return await res.json();
      }

      if (res.status === 429) {
        const errData = await res.json().catch(() => ({}));
        const detail = errData.error?.message || '';
        console.warn('Gemini 429 (attempt ' + (attempt + 1) + '):', detail);
        if (attempt === maxRetries) {
          throw { status: 429, message: detail || 'レート制限', retried: true };
        }
        continue;
      }

      // 429以外のエラー
      const errData = await res.json().catch(() => ({}));
      throw { status: res.status, message: errData.error?.message || 'HTTP ' + res.status };
    }
  }

  async function searchWeb() {
    const query = document.getElementById('web-search-query').value.trim();
    if (!query) { UI.showToast('検索キーワードを入力してください', 'warning'); return; }

    if (!getGeminiApiKey()) {
      UI.showToast('APIキーが設定されていません。設定画面で入力してください', 'error');
      return;
    }

    const searchData = getSearchCount();
    if (searchData.count >= DAILY_LIMIT) {
      UI.showToast('本日のAPI制限（' + DAILY_LIMIT + '件）に達しました。明日までお待ちください', 'error');
      return;
    }

    const statusEl = document.getElementById('web-search-status');
    const resultsEl = document.getElementById('web-search-results');
    const searchBtn = document.getElementById('btn-web-search');

    statusEl.classList.remove('hidden');
    statusEl.innerHTML = '<div class="web-search-loading"><div class="spinner"></div> Gemini AI が Google 検索中...</div>';
    resultsEl.classList.add('hidden');
    searchBtn.disabled = true;

    const prompt = `あなたは学習教材の専門家です。以下のトピックについて、最新かつ正確な情報を収集してください。

【検索トピック】
${query}

【指示】
1. 上記トピックについて詳しく調べてください
2. 試験対策に役立つ詳細な学習資料を作成してください
3. 以下の形式で回答してください：

【トピック概要】
（トピックの概要を2-3文で説明）

【重要ポイント】
- ポイント1: 詳細な説明
- ポイント2: 詳細な説明
- ポイント3: 詳細な説明
（できるだけ多くのポイントを列挙）

【重要用語】
- 用語1: 定義・説明
- 用語2: 定義・説明
（できるだけ多くの用語を列挙）

【よく出る問題パターン】
- パターン1: 具体的な問題例と答え
- パターン2: 具体的な問題例と答え

日本語で回答してください。高校生の定期試験対策として使える内容にしてください。`;

    try {
      let data = null;
      let usedGrounding = false;

      // まずSearch Grounding付きで試行
      try {
        statusEl.innerHTML = '<div class="web-search-loading"><div class="spinner"></div> Gemini AI が Google 検索中 (Search Grounding)...</div>';
        data = await callGeminiAPI(prompt, true, statusEl);
        usedGrounding = true;
      } catch (groundingErr) {
        if (groundingErr.status === 429 && groundingErr.retried) {
          // Search Groundingのレート制限 → Groundingなしで再試行
          console.warn('Search Grounding 429, falling back to non-grounding mode');
          statusEl.innerHTML = '<div class="web-search-loading"><div class="spinner"></div> Search Grounding制限中... AIの知識のみで回答を生成中...</div>';
          try {
            data = await callGeminiAPI(prompt, false, statusEl);
            usedGrounding = false;
          } catch (fallbackErr) {
            throw new Error('Gemini API エラー: ' + (fallbackErr.message || '不明なエラー'));
          }
        } else {
          throw new Error('Gemini API エラー: ' + (groundingErr.message || '不明なエラー'));
        }
      }

      incrementSearchCount();

      // レスポンスからテキストを抽出
      let responseText = '';
      if (data.candidates && data.candidates[0]) {
        const parts = data.candidates[0].content?.parts || [];
        responseText = parts.map(p => p.text || '').join('\n');
      }

      if (!responseText) {
        statusEl.innerHTML = '<div class="web-search-empty">⚠️ 検索結果を取得できませんでした。キーワードを変えてお試しください。</div>';
        searchBtn.disabled = false;
        return;
      }

      // Search Groundingのメタデータを取得
      const groundingMeta = data.candidates[0]?.groundingMetadata;
      const searchQueries = groundingMeta?.webSearchQueries || [];
      const searchResults = groundingMeta?.groundingChunks || [];

      window._webSearchText = responseText;

      // 結果表示
      let resultHtml = '<div class="web-result-item" style="white-space:pre-wrap;line-height:1.7">' + escapeHtml(responseText) + '</div>';

      // 検索クエリ情報を表示
      if (searchQueries.length > 0) {
        resultHtml = '<div style="margin-bottom:12px;padding:10px;background:rgba(108,99,255,0.1);border-radius:8px;font-size:0.8rem">' +
          '<strong>🔍 実行された検索:</strong> ' + searchQueries.map(q => escapeHtml(q)).join(', ') + '</div>' + resultHtml;
      }

      // 参照ソース情報を表示
      if (searchResults.length > 0) {
        resultHtml += '<div style="margin-top:12px;padding:10px;background:rgba(0,212,170,0.1);border-radius:8px;font-size:0.75rem">' +
          '<strong>📚 情報ソース:</strong><br>' +
          searchResults.slice(0, 5).map(chunk => {
            const web = chunk.web;
            if (web) return '<a href="' + escapeAttr(web.uri || '') + '" target="_blank" style="color:var(--accent);text-decoration:underline">' + escapeHtml(web.title || web.uri || '') + '</a>';
            return '';
          }).filter(Boolean).join('<br>') +
          '</div>';
      }

      const modeLabel = usedGrounding ? '✅ Gemini AI が Search Grounding で情報を取得しました' : '✅ Gemini AI の知識から情報を生成しました（Search Grounding 制限のためフォールバック）';
      statusEl.innerHTML = '<div class="web-search-success">' + modeLabel + '</div>';
      resultsEl.classList.remove('hidden');
      resultsEl.innerHTML = '<div class="web-results-header">🤖 AI検索結果プレビュー</div>' + resultHtml +
        '<div class="text-muted" style="font-size:0.8rem;margin-top:8px;text-align:center">↑ 上記のテキストから問題を生成します。下の「問題を生成」ボタンを押してください。</div>';
    } catch (err) {
      console.error('Gemini API Error:', err);
      statusEl.innerHTML = '<div class="web-search-error">❌ AI検索エラー: ' + escapeHtml(err.message || String(err)) + '</div>';
    } finally {
      searchBtn.disabled = false;
      updateSearchRemaining();
    }
  }

  // === 問題編集 ===
  let editingQuestionId = null;

  function openEditQuestion(questionId) {
    const q = allQuestions.find(item => item.id === questionId);
    if (!q) { UI.showToast('問題が見つかりません', 'error'); return; }
    editingQuestionId = questionId;
    document.getElementById('edit-q-text').value = q.question;
    document.getElementById('edit-q-answer').value = q.answer;
    document.getElementById('edit-q-explanation').value = q.explanation || '';
    document.getElementById('edit-q-type').value = q.type;
    document.getElementById('edit-q-diff').value = q.difficulty;
    const choicesGroup = document.getElementById('edit-q-choices-group');
    if (q.type === '選択' && q.choices) {
      choicesGroup.style.display = 'block';
      document.getElementById('edit-q-choices').value = q.choices.join(', ');
    } else {
      choicesGroup.style.display = q.type === '選択' ? 'block' : 'none';
      document.getElementById('edit-q-choices').value = '';
    }
    UI.openModal('modal-edit-question');
  }

  async function saveEditedQuestion() {
    if (!editingQuestionId) return;
    const q = allQuestions.find(item => item.id === editingQuestionId);
    if (!q) { UI.showToast('問題が見つかりません', 'error'); return; }
    const newText = document.getElementById('edit-q-text').value.trim();
    const newAnswer = document.getElementById('edit-q-answer').value.trim();
    if (!newText || !newAnswer) { UI.showToast('問題文と正解は必須です', 'warning'); return; }
    q.question = newText;
    q.answer = newAnswer;
    q.explanation = document.getElementById('edit-q-explanation').value.trim();
    q.type = document.getElementById('edit-q-type').value;
    q.difficulty = parseInt(document.getElementById('edit-q-diff').value);
    if (q.type === '選択') {
      const choicesText = document.getElementById('edit-q-choices').value;
      q.choices = choicesText.split(',').map(c => c.trim()).filter(c => c.length > 0);
      if (!q.choices.includes(q.answer)) q.choices.push(q.answer);
    } else {
      delete q.choices;
    }
    // カスタム問題の場合はlocalStorageも更新
    const customQs = Storage.getCustomQuestions();
    const customIdx = customQs.findIndex(cq => cq.id === editingQuestionId);
    if (customIdx >= 0) {
      customQs[customIdx] = { ...customQs[customIdx], ...q };
      Storage.addCustomQuestions([]); // 内部でconcatされるので代わりに直接書き換え
      localStorage.setItem('quizApp_customQuestions', JSON.stringify(customQs));
    }
    // サーバーAPIで更新を試みる
    try {
      await fetch('/api/questions/' + encodeURIComponent(editingQuestionId), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(q)
      });
    } catch (e) { console.warn('サーバー更新失敗:', e); }
    UI.closeModal('modal-edit-question');
    UI.showToast('問題を更新しました', 'success');
    renderQuestionList(null);
    editingQuestionId = null;
  }

  // === 教科別回答数 ===
  function openSubjectAnswerBreakdown() {
    const subjectStats = Storage.getSubjectStats();
    const subjectMap = {};
    subjects.forEach(s => subjectMap[s.id] = s);
    const entries = Object.keys(subjectStats)
      .map(sid => ({ subject: subjectMap[sid], stats: subjectStats[sid] }))
      .filter(e => e.subject && e.stats.total > 0)
      .sort((a, b) => b.stats.total - a.stats.total);
    const totalAll = entries.reduce((s, e) => s + e.stats.total, 0);
    const list = document.getElementById('answer-breakdown-list');
    if (entries.length === 0) {
      list.innerHTML = '<p class="text-muted" style="text-align:center;padding:20px">まだ回答記録がありません</p>';
    } else {
      list.innerHTML = '<div style="padding:12px 16px;margin-bottom:12px;background:rgba(139,92,246,0.1);border-radius:12px;display:flex;justify-content:space-between;font-weight:700"><span>合計</span><span>' + totalAll + ' 回答</span></div>' +
        entries.map(e => {
          const color = getCategoryColor(e.subject.category);
          const emoji = getCategoryEmoji(e.subject.category);
          const pct = Math.round(e.stats.total / totalAll * 100);
          return '<div class="accuracy-item"><div class="accuracy-header"><span class="accuracy-name" style="color:' + color + '">' + emoji + ' ' + e.subject.name + '</span><span style="font-weight:700">' + e.stats.total + '回答</span></div>' +
            '<div class="accuracy-bar"><div class="accuracy-bar-fill" style="width:' + pct + '%;background:' + color + '"></div></div>' +
            '<div class="accuracy-detail text-muted">正解 ' + e.stats.correct + ' / 不正解 ' + (e.stats.total - e.stats.correct) + ' (正答率 ' + e.stats.rate + '%)</div></div>';
        }).join('');
    }
    UI.openModal('modal-answer-breakdown');
  }

  return {
    quickStart, openWrongReviewModal, startWrongReview, openSubjectSetup, setQuizType, setDifficulty,
    startQuizFromSetup, openQuestionList, selectChoice, selectTF, submitAnswer, nextQuestion, quitQuiz,
    retryQuiz, retryWrong, generateQuestions, saveGeneratedQuestions,
    toggleTheme, toggleSetting, updateQuestionCount,
    exportData, importData, clearAllData, filterCategory, onNavigate,
    openVocabList, renderVocabUnit,
    switchGenMode, handleFileUpload, removeFile, searchWeb,
    toggleQuestionEditMode, deleteQuestion, syncQuestions,
    openEditQuestion, saveEditedQuestion, openSubjectAnswerBreakdown,
    saveApiKeyFromInput, deleteApiKey, renderApiKeyStatus
  };
})();
