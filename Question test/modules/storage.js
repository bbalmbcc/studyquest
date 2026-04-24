/**
 * Storage Module - ローカルストレージ管理
 * 学習履歴・正答率・設定の保存と読み込み
 */
window.Storage = (function () {
  const KEYS = {
    HISTORY: 'quizApp_history',
    SETTINGS: 'quizApp_settings',
    CUSTOM_QUESTIONS: 'quizApp_customQuestions',
    WRONG_ANSWERS: 'quizApp_wrongAnswers'
  };

  function _get(key) {
    try {
      const data = localStorage.getItem(key);
      return data ? JSON.parse(data) : null;
    } catch (e) {
      console.error('Storage read error:', e);
      return null;
    }
  }

  function _set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (e) {
      console.error('Storage write error:', e);
      return false;
    }
  }

  // --- 学習履歴 ---
  function getHistory() {
    return _get(KEYS.HISTORY) || [];
  }

  function addHistoryEntry(entry) {
    const history = getHistory();
    entry.timestamp = Date.now();
    entry.id = 'h_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
    history.unshift(entry);
    // 最大500件保持
    if (history.length > 500) history.length = 500;
    _set(KEYS.HISTORY, history);
    return entry;
  }

  function clearHistory() {
    _set(KEYS.HISTORY, []);
  }

  // --- 正答率 ---
  function getStats(subjectId) {
    const history = getHistory();
    const filtered = subjectId
      ? history.filter(h => h.subjectId === subjectId)
      : history;
    if (filtered.length === 0) return { total: 0, correct: 0, rate: 0 };
    const correct = filtered.filter(h => h.correct).length;
    return {
      total: filtered.length,
      correct: correct,
      rate: Math.round((correct / filtered.length) * 100)
    };
  }

  function getSubjectStats() {
    const history = getHistory();
    const stats = {};
    history.forEach(h => {
      if (!stats[h.subjectId]) {
        stats[h.subjectId] = { total: 0, correct: 0 };
      }
      stats[h.subjectId].total++;
      if (h.correct) stats[h.subjectId].correct++;
    });
    Object.keys(stats).forEach(key => {
      stats[key].rate = stats[key].total > 0
        ? Math.round((stats[key].correct / stats[key].total) * 100) : 0;
    });
    return stats;
  }

  // --- 間違えた問題 ---
  function getWrongAnswers() {
    return _get(KEYS.WRONG_ANSWERS) || {};
  }

  function addWrongAnswer(questionId, subjectId) {
    const wrong = getWrongAnswers();
    if (!wrong[questionId]) {
      wrong[questionId] = { count: 0, subjectId: subjectId, lastWrong: 0 };
    }
    wrong[questionId].count++;
    wrong[questionId].lastWrong = Date.now();
    _set(KEYS.WRONG_ANSWERS, wrong);
  }

  function removeWrongAnswer(questionId) {
    const wrong = getWrongAnswers();
    delete wrong[questionId];
    _set(KEYS.WRONG_ANSWERS, wrong);
  }

  function getWrongQuestionIds(subjectId) {
    const wrong = getWrongAnswers();
    return Object.keys(wrong).filter(id => !subjectId || wrong[id].subjectId === subjectId);
  }

  // --- 設定 ---
  function getSettings() {
    return _get(KEYS.SETTINGS) || {
      theme: 'dark',
      questionCount: 10,
      showExplanation: true,
      fontSize: 'medium'
    };
  }

  function saveSettings(settings) {
    _set(KEYS.SETTINGS, settings);
  }

  // --- カスタム問題 ---
  function getCustomQuestions() {
    return _get(KEYS.CUSTOM_QUESTIONS) || [];
  }

  function addCustomQuestions(questions) {
    const existing = getCustomQuestions();
    const combined = existing.concat(questions);
    _set(KEYS.CUSTOM_QUESTIONS, combined);
    return combined;
  }

  function deleteCustomQuestion(questionId) {
    const questions = getCustomQuestions();
    const filtered = questions.filter(q => q.id !== questionId);
    _set(KEYS.CUSTOM_QUESTIONS, filtered);
    return filtered;
  }

  function clearCustomQuestions() {
    _set(KEYS.CUSTOM_QUESTIONS, []);
  }

  // --- データ管理 ---
  function exportData() {
    return {
      history: getHistory(),
      settings: getSettings(),
      customQuestions: getCustomQuestions(),
      wrongAnswers: getWrongAnswers(),
      exportDate: new Date().toISOString()
    };
  }

  function importData(data) {
    if (data.history) _set(KEYS.HISTORY, data.history);
    if (data.settings) _set(KEYS.SETTINGS, data.settings);
    if (data.customQuestions) _set(KEYS.CUSTOM_QUESTIONS, data.customQuestions);
    if (data.wrongAnswers) _set(KEYS.WRONG_ANSWERS, data.wrongAnswers);
    return true;
  }

  function clearAllData() {
    Object.values(KEYS).forEach(key => localStorage.removeItem(key));
  }

  function getStorageUsage() {
    let total = 0;
    Object.values(KEYS).forEach(key => {
      const item = localStorage.getItem(key);
      if (item) total += item.length * 2; // UTF-16
    });
    return { bytes: total, formatted: (total / 1024).toFixed(1) + ' KB' };
  }

  return {
    getHistory, addHistoryEntry, clearHistory,
    getStats, getSubjectStats,
    getWrongAnswers, addWrongAnswer, removeWrongAnswer, getWrongQuestionIds,
    getSettings, saveSettings,
    getCustomQuestions, addCustomQuestions, deleteCustomQuestion, clearCustomQuestions,
    exportData, importData, clearAllData, getStorageUsage
  };
})();
