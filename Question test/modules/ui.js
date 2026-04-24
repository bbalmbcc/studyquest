/**
 * UI Module - 画面遷移・テーマ・通知・モーダル制御
 */
window.UI = (function () {
  let currentScreen = 'home';
  const screens = ['home', 'subjects', 'quiz', 'results', 'settings'];

  function init() {
    applyTheme(window.Storage.getSettings().theme);
    setupNavigation();
  }

  // --- 画面遷移 ---
  function navigateTo(screenId, options) {
    if (!screens.includes(screenId)) return;
    const current = document.querySelector('.screen.active');
    const next = document.getElementById('screen-' + screenId);
    if (!next) return;

    if (current) {
      current.classList.add('fade-out');
      setTimeout(() => {
        current.classList.remove('active', 'fade-out');
      }, 300);
    }

    setTimeout(() => {
      next.classList.add('active', 'fade-in');
      setTimeout(() => next.classList.remove('fade-in'), 300);
    }, current ? 300 : 0);

    currentScreen = screenId;
    updateNavActive(screenId);

    if (options && options.onEnter) {
      setTimeout(options.onEnter, current ? 350 : 50);
    }
  }

  function setupNavigation() {
    document.querySelectorAll('[data-nav]').forEach(el => {
      el.addEventListener('click', (e) => {
        e.preventDefault();
        navigateTo(el.dataset.nav);
        if (typeof window.App !== 'undefined' && window.App.onNavigate) {
          window.App.onNavigate(el.dataset.nav);
        }
      });
    });
  }

  function updateNavActive(screenId) {
    document.querySelectorAll('[data-nav]').forEach(el => {
      el.classList.toggle('active', el.dataset.nav === screenId);
    });
  }

  // --- テーマ ---
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const settings = window.Storage.getSettings();
    settings.theme = theme;
    window.Storage.saveSettings(settings);
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    return next;
  }

  function getTheme() {
    return document.documentElement.getAttribute('data-theme') || 'dark';
  }

  // --- トースト通知 ---
  function showToast(message, type, duration) {
    type = type || 'info';
    duration = duration || 3000;
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    const icons = { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' };
    toast.innerHTML = '<span class="toast-icon">' + (icons[type] || '') + '</span><span class="toast-message">' + message + '</span>';
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
      toast.classList.remove('show');
      toast.classList.add('hide');
      setTimeout(() => toast.remove(), 400);
    }, duration);
  }

  // --- モーダル ---
  function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    modal.classList.add('active');
    document.body.classList.add('modal-open');
  }

  function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    modal.classList.remove('active');
    document.body.classList.remove('modal-open');
  }

  function closeAllModals() {
    document.querySelectorAll('.modal.active').forEach(m => m.classList.remove('active'));
    document.body.classList.remove('modal-open');
  }

  // --- 確認ダイアログ ---
  function confirm(message, onConfirm, onCancel) {
    const modal = document.getElementById('modal-confirm');
    if (!modal) { if (window.confirm(message)) { onConfirm && onConfirm(); } else { onCancel && onCancel(); } return; }
    modal.querySelector('.confirm-message').textContent = message;
    const btnOk = modal.querySelector('.btn-confirm-ok');
    const btnCancel = modal.querySelector('.btn-confirm-cancel');
    const cleanup = () => { closeModal('modal-confirm'); btnOk.replaceWith(btnOk.cloneNode(true)); btnCancel.replaceWith(btnCancel.cloneNode(true)); };
    btnOk.addEventListener('click', () => { cleanup(); onConfirm && onConfirm(); }, { once: true });
    btnCancel.addEventListener('click', () => { cleanup(); onCancel && onCancel(); }, { once: true });
    openModal('modal-confirm');
  }

  // --- プログレスバー ---
  function updateProgress(current, total) {
    const bar = document.getElementById('quiz-progress-fill');
    const text = document.getElementById('quiz-progress-text');
    if (bar) bar.style.width = (current / total * 100) + '%';
    if (text) text.textContent = current + ' / ' + total;
  }

  // --- ユーティリティ ---
  function formatDate(timestamp) {
    const d = new Date(timestamp);
    return d.getFullYear() + '/' + String(d.getMonth() + 1).padStart(2, '0') + '/' + String(d.getDate()).padStart(2, '0') + ' ' + String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
  }

  function animateCounter(element, target, duration) {
    duration = duration || 1000;
    const start = parseInt(element.textContent) || 0;
    const diff = target - start;
    const startTime = performance.now();
    function step(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = Math.round(start + diff * eased);
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  return {
    init, navigateTo, applyTheme, toggleTheme, getTheme,
    showToast, openModal, closeModal, closeAllModals, confirm,
    updateProgress, formatDate, animateCounter, currentScreen: () => currentScreen
  };
})();
