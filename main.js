import { startQuizSync, loadLocalQuizCache, pushQuestionsToFirebase, deleteQuestionFromFirebase } from "./firebase/firebase-sync.js";

// === ブリッジ関数の定義 ===
// script.js (非モジュール) の window.App と連携するための関数群をグローバルに公開します

window.FirebaseSyncModule = {
  pushQuestions: async (questions) => {
    return await pushQuestionsToFirebase(questions);
  },
  deleteQuestion: async (questionId) => {
    return await deleteQuestionFromFirebase(questionId);
  }
};

/**
 * 初回起動時のデータ移行と同期のセットアップ
 */
function initializeSync() {
  // 1. オフラインキャッシュの読み込み（Firebaseより先に表示させる）
  const cached = loadLocalQuizCache();
  if (cached && typeof window.App !== 'undefined' && window.App.updateAppQuizData) {
    console.log("[Sync] ローカルキャッシュから読み込みました", cached.length, "問");
    window.App.updateAppQuizData(cached);
  }

  // 2. 過去のローカル「カスタム問題」が存在する場合、Firebaseへ移行する
  migrateOldCustomQuestions();

  // 3. Firebaseリアルタイム同期の開始
  startQuizSync((data) => {
    if (typeof window.App !== 'undefined' && window.App.updateAppQuizData) {
      window.App.updateAppQuizData(data);
    }
  });
}

function migrateOldCustomQuestions() {
  try {
    const oldCustomQsStr = localStorage.getItem("quizApp_customQuestions");
    if (oldCustomQsStr) {
      const oldCustomQs = JSON.parse(oldCustomQsStr);
      if (oldCustomQs && oldCustomQs.length > 0) {
        console.log("[Sync] 古いカスタム問題をFirebaseに移行します...", oldCustomQs.length, "問");
        // Firebaseにプッシュ
        pushQuestionsToFirebase(oldCustomQs).then((success) => {
          if (success) {
            console.log("[Sync] 移行完了。ローカルの古いカスタム問題をクリアします。");
            localStorage.removeItem("quizApp_customQuestions");
          }
        });
      }
    }
  } catch (e) {
    console.error("古いデータの移行中にエラーが発生しました:", e);
  }
}

// ページ読み込み完了時に同期を初期化
document.addEventListener('DOMContentLoaded', () => {
  initializeSync();
});
