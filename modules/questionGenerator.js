/**
 * Question Generator Module - テキストから問題を自動生成
 * v3: アスタリスク除去 + 問題文の自己完結化
 */
window.QuestionGenerator = (function () {

  function generateId() {
    return 'gen_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
  }

  /**
   * テキストからMarkdown記法のアスタリスク等を除去
   */
  function sanitizeText(text) {
    if (!text) return '';
    return text
      .replace(/\*{1,3}([^*]+)\*{1,3}/g, '$1')  // **bold**, *italic*, ***both***
      .replace(/^\s*[\*\-]\s+/gm, '')             // リスト記号 * - を除去
      .replace(/#{1,6}\s*/g, '')                   // 見出し # を除去
      .replace(/`([^`]+)`/g, '$1')                 // `code` を除去
      .replace(/\*+/g, '')                         // 残りのアスタリスクを除去
      .trim();
  }

  /**
   * テキストから問題セットを自動生成
   * @param {string} text - 入力テキスト
   * @param {string} subjectId - 教科ID
   * @param {string} unitId - 単元ID
   * @param {object} options - { types: ['選択','記述','○×'], count: 5 }
   */
  function generateFromText(text, subjectId, unitId, options) {
    options = options || {};
    const types = options.types || ['選択', '記述', '○×'];
    const maxCount = options.count || 10;
    // 入力テキストもサニタイズ
    text = sanitizeText(text);
    const lines = parseText(text);
    if (lines.length === 0) return [];

    let questions = [];

    // キーワードペア抽出（「A は B」「A：B」形式）
    const pairs = extractKeyValuePairs(lines);

    // 各タイプで問題生成
    if (types.includes('○×')) {
      questions = questions.concat(generateTrueFalse(pairs, subjectId, unitId));
    }
    if (types.includes('選択')) {
      questions = questions.concat(generateMultipleChoice(pairs, subjectId, unitId));
    }
    if (types.includes('記述')) {
      questions = questions.concat(generateFillBlank(pairs, subjectId, unitId));
    }

    // 全問題テキストをサニタイズ
    questions = questions.map(q => {
      q.question = sanitizeText(q.question);
      q.answer = sanitizeText(q.answer);
      if (q.explanation) q.explanation = sanitizeText(q.explanation);
      if (q.choices) q.choices = q.choices.map(c => sanitizeText(c));
      return q;
    });

    // シャッフルして制限数に切り詰め
    questions = shuffle(questions).slice(0, maxCount);
    return questions;
  }

  function parseText(text) {
    return text
      .split(/[\n\r]+/)
      .map(line => line.trim())
      .filter(line => line.length > 2);
  }

  function extractKeyValuePairs(lines) {
    const pairs = [];
    const patterns = [
      /^(.+?)\s*[はがを]\s*(.+?)[。．.]?\s*$/,
      /^(.+?)\s*[:：]\s*(.+?)\s*$/,
      /^(.+?)\s*[=＝]\s*(.+?)\s*$/,
      /^(.+?)\s*[-ー→]\s*(.+?)\s*$/,
      /^(.+?)\s*[（(](.+?)[)）]\s*$/,
      /^「(.+?)」\s*(.+?)\s*$/
    ];

    lines.forEach(line => {
      for (const pattern of patterns) {
        const match = line.match(pattern);
        if (match && match[1].length > 1 && match[2].length > 1 && match[1].length < 50 && match[2].length < 100) {
          pairs.push({ term: match[1].trim(), definition: match[2].trim(), original: line });
          break;
        }
      }
    });

    // パターンに一致しなかった行もそのまま文として使う
    lines.forEach(line => {
      const exists = pairs.some(p => p.original === line);
      if (!exists && line.length > 5 && line.length < 150) {
        pairs.push({ term: null, definition: line, original: line });
      }
    });

    return pairs;
  }

  function generateTrueFalse(pairs, subjectId, unitId) {
    const questions = [];
    const termPairs = pairs.filter(p => p.term);

    termPairs.forEach((pair, i) => {
      // 正しい文（○）— 問題文に判断材料を十分に含める
      questions.push({
        id: generateId(),
        subjectId: subjectId,
        unitId: unitId,
        type: '○×',
        difficulty: 1,
        question: '次の文は正しいか。「' + pair.term + '」とは「' + pair.definition + '」のことである。',
        answer: '○',
        explanation: 'この記述は正しいです。' + pair.term + 'は' + pair.definition + 'です。',
        generated: true
      });

      // 誤った文を作成（×）- 他のペアの定義と入れ替え
      if (termPairs.length > 1) {
        const otherIdx = (i + 1) % termPairs.length;
        const wrongDef = termPairs[otherIdx].definition;
        questions.push({
          id: generateId(),
          subjectId: subjectId,
          unitId: unitId,
          type: '○×',
          difficulty: 2,
          question: '次の文は正しいか。「' + pair.term + '」とは「' + wrongDef + '」のことである。',
          answer: '×',
          explanation: '誤りです。「' + pair.term + '」は「' + pair.definition + '」のことです。「' + wrongDef + '」は「' + termPairs[otherIdx].term + '」の説明です。',
          generated: true
        });
      }
    });
    return questions;
  }

  function generateMultipleChoice(pairs, subjectId, unitId) {
    const questions = [];
    const termPairs = pairs.filter(p => p.term);
    if (termPairs.length < 3) return questions;

    termPairs.forEach((pair, i) => {
      const wrongChoices = termPairs
        .filter((_, idx) => idx !== i)
        .map(p => p.definition);
      const shuffledWrong = shuffle(wrongChoices).slice(0, 3);

      if (shuffledWrong.length < 2) return;

      const allChoices = shuffle([pair.definition, ...shuffledWrong]);

      // 問題文に十分な文脈を含める
      questions.push({
        id: generateId(),
        subjectId: subjectId,
        unitId: unitId,
        type: '選択',
        difficulty: 2,
        question: '「' + pair.term + '」の意味・説明として最も適切なものを選べ。',
        choices: allChoices,
        answer: pair.definition,
        explanation: '「' + pair.term + '」は「' + pair.definition + '」です。',
        generated: true
      });

      // 逆引き問題（定義→用語）も生成
      const wrongTermChoices = termPairs
        .filter((_, idx) => idx !== i)
        .map(p => p.term);
      const shuffledWrongTerms = shuffle(wrongTermChoices).slice(0, 3);
      if (shuffledWrongTerms.length >= 2) {
        const allTermChoices = shuffle([pair.term, ...shuffledWrongTerms]);
        questions.push({
          id: generateId(),
          subjectId: subjectId,
          unitId: unitId,
          type: '選択',
          difficulty: 2,
          question: '次の説明に該当する用語はどれか。「' + pair.definition + '」',
          choices: allTermChoices,
          answer: pair.term,
          explanation: '正解は「' + pair.term + '」です。' + pair.term + 'は' + pair.definition + 'です。',
          generated: true
        });
      }
    });
    return questions;
  }

  function generateFillBlank(pairs, subjectId, unitId) {
    const questions = [];
    const termPairs = pairs.filter(p => p.term);

    termPairs.forEach(pair => {
      // 用語を答えさせる（定義を問題文に含める）
      questions.push({
        id: generateId(),
        subjectId: subjectId,
        unitId: unitId,
        type: '記述',
        difficulty: 2,
        question: '次の説明に該当する用語を答えよ。「' + pair.definition + '」',
        answer: pair.term,
        explanation: '答えは「' + pair.term + '」です。' + pair.term + 'は' + pair.definition + 'です。',
        generated: true
      });

      // 定義を答えさせる（用語を問題文に含める）
      if (pair.definition.length <= 30) {
        questions.push({
          id: generateId(),
          subjectId: subjectId,
          unitId: unitId,
          type: '記述',
          difficulty: 2,
          question: '「' + pair.term + '」の意味を答えよ。',
          answer: pair.definition,
          explanation: '「' + pair.term + '」は「' + pair.definition + '」です。',
          generated: true
        });
      }
    });
    return questions;
  }

  function shuffle(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  /**
   * CSVテキストから問題をインポート
   * 形式: question,answer,type,explanation
   */
  function importFromCSV(csvText, subjectId, unitId) {
    const lines = csvText.split('\n').filter(l => l.trim());
    if (lines.length < 2) return [];
    const questions = [];
    for (let i = 1; i < lines.length; i++) {
      const cols = lines[i].split(',').map(c => c.trim().replace(/^"|"$/g, ''));
      if (cols.length < 2) continue;
      questions.push({
        id: generateId(),
        subjectId: subjectId,
        unitId: unitId,
        type: cols[2] || '記述',
        difficulty: 1,
        question: sanitizeText(cols[0]),
        answer: sanitizeText(cols[1]),
        explanation: sanitizeText(cols[3] || ''),
        generated: true
      });
    }
    return questions;
  }

  return { generateFromText, importFromCSV, shuffle, sanitizeText };
})();
