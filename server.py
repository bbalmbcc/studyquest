"""
StudyQuest バックエンドサーバー
- 静的ファイル配信 (python -m http.server の代替)
- /api/ocr エンドポイント: ndlocr-lite を使用した画像OCR

使い方:
  python server.py

ndlocr-lite がインストールされていない場合でも、
静的ファイル配信は正常に動作します。
画像OCR機能のみが無効になります。
"""

import http.server
import socketserver
import json
import os
import sys
import tempfile
import shutil
import subprocess
import traceback
from urllib.parse import urlparse
from pathlib import Path

PORT = 3000
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))

# Windows コンソールのエンコーディング対策
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# ndlocr-lite のパスを検出
NDLOCR_LITE_DIR = None
NDLOCR_LITE_AVAILABLE = False


def find_ndlocr_lite():
    """ndlocr-lite のインストール場所を検索"""
    global NDLOCR_LITE_DIR, NDLOCR_LITE_AVAILABLE

    # 1. 同じディレクトリ内の ndlocr-lite
    local_path = os.path.join(STATIC_DIR, 'ndlocr-lite')
    if os.path.isdir(local_path) and os.path.isfile(os.path.join(local_path, 'src', 'ocr.py')):
        NDLOCR_LITE_DIR = local_path
        NDLOCR_LITE_AVAILABLE = True
        return

    # 2. 親ディレクトリ
    parent_path = os.path.join(os.path.dirname(STATIC_DIR), 'ndlocr-lite')
    if os.path.isdir(parent_path) and os.path.isfile(os.path.join(parent_path, 'src', 'ocr.py')):
        NDLOCR_LITE_DIR = parent_path
        NDLOCR_LITE_AVAILABLE = True
        return

    # 3. コマンドとして使用可能か確認
    try:
        result = subprocess.run(
            ['ndlocr-lite', '--help'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            NDLOCR_LITE_AVAILABLE = True
            NDLOCR_LITE_DIR = '__command__'
            return
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    print("[INFO] ndlocr-lite not found. Image OCR is disabled.")
    print("[INFO] Setup: run 'python setup_ocr.py'")


def run_ndlocr_ocr(image_path):
    """ndlocr-lite を使って画像からテキストを抽出"""
    if not NDLOCR_LITE_AVAILABLE:
        return None, "ndlocr-lite がインストールされていません。setup_ocr.py を実行してセットアップしてください。"

    output_dir = tempfile.mkdtemp(prefix='studyquest_ocr_')
    try:
        if NDLOCR_LITE_DIR == '__command__':
            # uv tool install 経由でインストールされている場合
            cmd = ['ndlocr-lite', '--sourceimg', image_path, '--output', output_dir, '--json-only']
        else:
            # ソースコードから直接実行
            ocr_script = os.path.join(NDLOCR_LITE_DIR, 'src', 'ocr.py')
            cmd = [sys.executable, ocr_script, '--sourceimg', image_path, '--output', output_dir, '--json-only']

        print(f"[OCR] 実行中: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=120,
            cwd=NDLOCR_LITE_DIR if NDLOCR_LITE_DIR != '__command__' else None
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or "不明なエラー"
            return None, f"OCR処理エラー: {error_msg}"

        # JSON結果を読み取り
        text = extract_text_from_ocr_output(output_dir)
        if text:
            return text, None
        else:
            return None, "OCR結果からテキストを抽出できませんでした"

    except subprocess.TimeoutExpired:
        return None, "OCR処理がタイムアウトしました（120秒）"
    except Exception as e:
        return None, f"OCR実行エラー: {str(e)}"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def extract_text_from_ocr_output(output_dir):
    """ndlocr-lite の出力ディレクトリからテキストを抽出"""
    texts = []

    # JSON ファイルを探す
    for root, dirs, files in os.walk(output_dir):
        for fname in sorted(files):
            fpath = os.path.join(root, fname)
            if fname.endswith('.json'):
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # ndlocr-lite の JSON 形式からテキストを抽出
                    texts.extend(extract_text_from_json(data))
                except Exception as e:
                    print(f"[OCR] JSON読み取りエラー: {fpath}: {e}")
            elif fname.endswith('.txt'):
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    if content:
                        texts.append(content)
                except Exception:
                    pass
            elif fname.endswith('.xml'):
                try:
                    texts.extend(extract_text_from_xml(fpath))
                except Exception:
                    pass

    return '\n'.join(texts)


def extract_text_from_json(data):
    """ndlocr-lite JSON出力からテキスト行を抽出"""
    texts = []
    if isinstance(data, dict):
        # "contents" フィールドにテキストブロックがある形式
        if 'contents' in data:
            for block in data['contents']:
                if isinstance(block, dict) and 'body' in block:
                    texts.append(block['body'])
                elif isinstance(block, dict) and 'text' in block:
                    texts.append(block['text'])
                elif isinstance(block, str):
                    texts.append(block)
        # "results" フィールド
        if 'results' in data:
            for r in data['results']:
                if isinstance(r, dict) and 'text' in r:
                    texts.append(r['text'])
        # "text" フィールド直接
        if 'text' in data and isinstance(data['text'], str):
            texts.append(data['text'])
        # "lines" フィールド
        if 'lines' in data:
            for line in data['lines']:
                if isinstance(line, dict) and 'text' in line:
                    texts.append(line['text'])
                elif isinstance(line, str):
                    texts.append(line)
    elif isinstance(data, list):
        for item in data:
            texts.extend(extract_text_from_json(item))
    return texts


def extract_text_from_xml(xml_path):
    """XML出力からテキストを抽出"""
    import xml.etree.ElementTree as ET
    texts = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        # すべてのテキストノードを抽出
        for elem in root.iter():
            if elem.text and elem.text.strip():
                texts.append(elem.text.strip())
    except Exception:
        pass
    return texts


class StudyQuestHandler(http.server.SimpleHTTPRequestHandler):
    """静的ファイル配信 + OCR API"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/ocr':
            self.handle_ocr()
        else:
            self.send_error(404, 'Not Found')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def handle_ocr(self):
        """画像OCRエンドポイント"""
        try:
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                self.send_json_error(400, 'Content-Type must be multipart/form-data')
                return

            # multipart データを解析
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_json_error(400, 'リクエストボディが空です')
                return
            if content_length > 50 * 1024 * 1024:  # 50MB制限
                self.send_json_error(413, 'ファイルサイズが大きすぎます (上限: 50MB)')
                return

            # 一時ファイルに保存して処理
            import cgi
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    'REQUEST_METHOD': 'POST',
                    'CONTENT_TYPE': content_type
                }
            )

            if 'image' not in form:
                self.send_json_error(400, '画像ファイルが見つかりません')
                return

            file_item = form['image']
            if not file_item.filename:
                self.send_json_error(400, 'ファイル名が不明です')
                return

            # 一時ファイルに書き出し
            ext = os.path.splitext(file_item.filename)[1].lower() or '.png'
            tmp_file = tempfile.NamedTemporaryFile(
                delete=False, suffix=ext, prefix='studyquest_'
            )
            try:
                tmp_file.write(file_item.file.read())
                tmp_file.close()

                if not NDLOCR_LITE_AVAILABLE:
                    self.send_json_error(
                        503,
                        'ndlocr-lite がインストールされていません。\n'
                        'セットアップ方法:\n'
                        '1. python setup_ocr.py を実行\n'
                        '2. サーバーを再起動'
                    )
                    return

                print(f"[OCR] 処理開始: {file_item.filename}")
                text, error = run_ndlocr_ocr(tmp_file.name)

                if error:
                    self.send_json_error(500, error)
                else:
                    self.send_json_response({'text': text, 'filename': file_item.filename})
                    print(f"[OCR] 完了: {file_item.filename} ({len(text)}文字)")
            finally:
                os.unlink(tmp_file.name)

        except Exception as e:
            traceback.print_exc()
            self.send_json_error(500, f'サーバーエラー: {str(e)}')

    def send_json_response(self, data, status=200):
        response = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response)

    def send_json_error(self, status, message):
        self.send_json_response({'error': message}, status)

    def log_message(self, format, *args):
        # 静的ファイルアクセスログを簡略化
        if '/api/' in (args[0] if args else ''):
            super().log_message(format, *args)
        elif '.map' not in (args[0] if args else ''):
            super().log_message(format, *args)


def main():
    find_ndlocr_lite()

    print("=" * 60)
    print("  [StudyQuest Server]")
    print("=" * 60)
    print(f"  URL: http://localhost:{PORT}")
    print(f"  Static: {STATIC_DIR}")
    if NDLOCR_LITE_AVAILABLE:
        print(f"  OCR: ndlocr-lite ENABLED ({NDLOCR_LITE_DIR})")
    else:
        print(f"  OCR: DISABLED (run setup_ocr.py to enable)")
    print("=" * 60)
    print("  Press Ctrl+C to stop\n")

    with socketserver.TCPServer(("", PORT), StudyQuestHandler) as httpd:
        httpd.allow_reuse_address = True
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[INFO] サーバーを停止しました。")
            httpd.server_close()


if __name__ == '__main__':
    main()
