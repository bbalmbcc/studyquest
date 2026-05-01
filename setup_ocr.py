"""
ndlocr-lite セットアップスクリプト
国立国会図書館のOCRエンジンをインストールします。

使い方:
  python setup_ocr.py
"""

import subprocess
import sys
import os
import shutil

NDLOCR_LITE_REPO = "https://github.com/ndl-lab/ndlocr-lite.git"
INSTALL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ndlocr-lite")


def check_python_version():
    """Python 3.10以上か確認"""
    if sys.version_info < (3, 10):
        print(f"❌ Python 3.10以上が必要です。現在のバージョン: {sys.version}")
        print("   https://www.python.org/downloads/ から最新版をインストールしてください。")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True


def check_git():
    """gitが使えるか確認"""
    try:
        result = subprocess.run(['git', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    print("❌ git がインストールされていません。")
    print("   https://git-scm.com/downloads からインストールしてください。")
    return False


def clone_ndlocr_lite():
    """ndlocr-lite をクローン"""
    if os.path.isdir(INSTALL_DIR):
        print(f"📁 ndlocr-lite は既にインストールされています: {INSTALL_DIR}")
        answer = input("   再インストールしますか？ (y/N): ").strip().lower()
        if answer != 'y':
            print("   スキップしました。")
            return True
        print("   既存のディレクトリを削除中...")
        shutil.rmtree(INSTALL_DIR)

    print(f"\n📥 ndlocr-lite をクローン中...")
    print(f"   リポジトリ: {NDLOCR_LITE_REPO}")
    print(f"   インストール先: {INSTALL_DIR}")
    result = subprocess.run(
        ['git', 'clone', NDLOCR_LITE_REPO, INSTALL_DIR],
        capture_output=False
    )
    if result.returncode != 0:
        print("❌ クローンに失敗しました。")
        return False
    print("✅ クローン完了")
    return True


def install_dependencies():
    """依存関係をインストール"""
    req_file = os.path.join(INSTALL_DIR, 'requirements.txt')
    if not os.path.isfile(req_file):
        print("❌ requirements.txt が見つかりません。")
        return False

    print("\n📦 依存関係をインストール中...")
    print("   (これには数分かかる場合があります)")
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '-r', req_file],
        capture_output=False
    )
    if result.returncode != 0:
        print("❌ 依存関係のインストールに失敗しました。")
        print("   手動で実行してみてください:")
        print(f"   pip install -r {req_file}")
        return False
    print("✅ 依存関係のインストール完了")
    return True


def verify_installation():
    """インストールを検証"""
    ocr_script = os.path.join(INSTALL_DIR, 'src', 'ocr.py')
    if not os.path.isfile(ocr_script):
        print("❌ ocr.py が見つかりません。")
        return False

    print("\n🔍 インストールを検証中...")
    try:
        result = subprocess.run(
            [sys.executable, ocr_script, '--help'],
            capture_output=True, text=True, timeout=30,
            cwd=INSTALL_DIR
        )
        if result.returncode == 0:
            print("✅ ndlocr-lite は正常に動作しています！")
            return True
        else:
            print(f"⚠️  ocr.py の実行時にエラーが発生しました:")
            print(f"   {result.stderr[:200] if result.stderr else result.stdout[:200]}")
            print("   依存関係に問題がある可能性があります。")
            return False
    except subprocess.TimeoutExpired:
        print("⚠️  検証がタイムアウトしました（初回はモデルのダウンロードが必要な場合があります）")
        return True
    except Exception as e:
        print(f"⚠️  検証中にエラー: {e}")
        return False


def main():
    print("=" * 60)
    print("  🔧 ndlocr-lite OCR セットアップ")
    print("  国立国会図書館 日本語OCRエンジン")
    print("=" * 60)
    print()

    # 前提条件チェック
    print("📋 前提条件の確認:")
    if not check_python_version():
        sys.exit(1)
    if not check_git():
        sys.exit(1)

    # クローン
    if not clone_ndlocr_lite():
        sys.exit(1)

    # 依存関係インストール
    if not install_dependencies():
        sys.exit(1)

    # 検証
    verify_installation()

    print()
    print("=" * 60)
    print("  ✅ セットアップ完了！")
    print("=" * 60)
    print()
    print("  サーバーを起動するには:")
    print("    python server.py")
    print()
    print("  画像OCR機能が有効になります。")
    print("  対応形式: JPG, PNG, BMP, TIFF")
    print()


if __name__ == '__main__':
    main()
