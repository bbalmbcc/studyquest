import { db, ref, onValue, set, update } from "./firebase-config.js";

const quizRef = ref(db, "quizData/questions");

/**
 * リアルタイム同期を開始する
 * @param {Function} renderCallback データ受信時にUIを再描画する関数
 */
export function startQuizSync(renderCallback) {
  // onValueでデータの変更をリアルタイムに検知
  onValue(quizRef, (snapshot) => {
    const data = snapshot.val();
    
    // データがない場合（初期状態など）
    if (!data) {
      renderCallback([]);
      return;
    }
    
    // オブジェクトから配列に変換
    const questionsArray = Object.values(data);
    
    // ローカルストレージにキャッシュを保存
    try {
      localStorage.setItem("quizDataCache", JSON.stringify(questionsArray));
    } catch (e) {
      console.warn("キャッシュの保存に失敗しました", e);
    }
    
    // UI側にデータを渡して再描画
    renderCallback(questionsArray);
  }, (error) => {
    console.error("Firebase同期エラー:", error);
    updateSyncStatus("offline");
  });
  
  // 接続状態の監視
  const connectedRef = ref(db, ".info/connected");
  onValue(connectedRef, (snap) => {
    if (snap.val() === true) {
      updateSyncStatus("online");
    } else {
      updateSyncStatus("offline");
    }
  });
}

/**
 * ローカルキャッシュを読み込む（オフライン用）
 */
export function loadLocalQuizCache() {
  const cache = localStorage.getItem("quizDataCache");
  if (!cache) return null;
  try {
    return JSON.parse(cache);
  } catch (e) {
    return null;
  }
}

/**
 * 問題をFirebaseに書き込む
 * （追加・更新・削除兼用）
 */
export async function pushQuestionsToFirebase(questions) {
  try {
    const updates = {};
    const now = Date.now();
    for (const q of questions) {
      q.updatedAt = q.updatedAt || now;
      updates[q.id] = q;
    }
    await update(quizRef, updates);
    return true;
  } catch (error) {
    console.error("Firebase書き込みエラー:", error);
    return false;
  }
}

/**
 * 単一問題の削除 (null代入)
 */
export async function deleteQuestionFromFirebase(questionId) {
  try {
    await set(ref(db, `quizData/questions/${questionId}`), null);
    return true;
  } catch (error) {
    console.error("Firebase削除エラー:", error);
    return false;
  }
}

/**
 * 同期ステータスバッジの更新
 */
function updateSyncStatus(status) {
  const badge = document.getElementById("syncStatus");
  if (!badge) return;
  
  if (status === "online") {
    badge.innerHTML = '<span style="color:#10B981;">●</span> 最新同期済み';
    badge.title = "Firebaseと接続されています";
  } else if (status === "offline") {
    badge.innerHTML = '<span style="color:#EF4444;">●</span> オフライン';
    badge.title = "接続が切れています。キャッシュを使用中です。";
  } else {
    badge.innerHTML = '<span style="color:#F59E0B;">●</span> 同期中...';
  }
}
