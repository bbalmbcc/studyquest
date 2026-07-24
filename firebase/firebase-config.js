import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import {
  getDatabase,
  ref,
  onValue,
  set,
  push,
  update
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-database.js";

// TODO: 後ほどご自身のプロジェクト設定で上書きしてください
const firebaseConfig = {
  apiKey: "AIzaSyCP886GjRgpQ5bi8oBCUKZb4y7perBBJPc",
  authDomain: "studyquest-971b6.firebaseapp.com",
  databaseURL: "https://studyquest-971b6-default-rtdb.asia-southeast1.firebasedatabase.app",
  projectId: "studyquest-971b6",
  storageBucket: "studyquest-971b6.firebasestorage.app",
  messagingSenderId: "465813850375",
  appId: "1:465813850375:web:aa1d864f0cbebac25b9da2",
  measurementId: "G-TKJY3QD9K6"
};

// LocalStorageに以前の設定(v1)が残っている場合はそれを優先して読み込む（互換性用）
const savedConfig = localStorage.getItem('studyquest_firebaseConfig');
const finalConfig = savedConfig ? JSON.parse(savedConfig) : firebaseConfig;

const app = initializeApp(finalConfig);

export const db = getDatabase(app);
export {
  ref,
  onValue,
  set,
  push,
  update
};
