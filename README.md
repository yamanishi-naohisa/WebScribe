# WebScribe

Webページに表示されているすべてのWeb要素を取得して保存するPythonツール

## 機能

- Webページのすべての表示要素を取得
- 各要素の詳細情報（タグ名、属性、テキスト、位置、サイズなど）を収集
- JSON形式で保存
- コマンドライン版とGUI版の両方を提供

## インストール

```bash
pip install -r requirements.txt
```

### 必要なパッケージ

- selenium >= 4.15.0
- webdriver-manager >= 4.0.0

## 使い方

### GUI版（推奨）

ダイアログでURLを指定して簡単にWeb要素を取得できます。

```bash
python webscribe_gui.py
```

**GUI版の機能:**
- URL入力フィールド
- 出力ファイルの指定（参照ボタンでファイル選択）
- ヘッドレスモードの選択
- 待機時間の設定
- リアルタイムログ表示
- 進捗バーの表示

### コマンドライン版

```bash
# 基本的な使用
python webscribe.py https://example.com

# 出力ファイルを指定
python webscribe.py https://example.com -o output.json

# ヘッドレスモード（ブラウザを表示しない）
python webscribe.py https://example.com --headless

# 待機時間を指定（秒）
python webscribe.py https://example.com --wait 15
```

### Pythonコードから使用

```python
from webscribe import WebScribe

with WebScribe(headless=False) as scribe:
    data = scribe.scrape_page("https://example.com")
    scribe.save_to_json(data, "output.json")
```

## 出力形式

JSON形式で以下の情報が保存されます：

```json
{
  "page_info": {
    "url": "https://example.com/",
    "title": "Example Domain",
    "timestamp": "2025-12-06T21:39:40.112648",
    "viewport_size": {
      "width": 780,
      "height": 580
    }
  },
  "elements": [
    {
      "index": 0,
      "tag_name": "body",
      "text": "...",
      "attributes": {},
      "location": {"x": 153, "y": 65},
      "size": {"width": 458, "height": 127},
      "is_displayed": true,
      "is_enabled": true,
      "xpath": "/html/body",
      "css_selector": "html > body",
      "children": [...],
      "children_count": 1
    }
  ],
  "total_elements": 5
}
```

## 取得される情報

各要素について以下の情報が取得されます：

- **tag_name**: HTMLタグ名
- **text**: 要素内のテキスト
- **attributes**: すべてのHTML属性
- **location**: 画面上の位置（x, y座標）
- **size**: サイズ（width, height）
- **is_displayed**: 表示されているかどうか
- **is_enabled**: 有効かどうか
- **xpath**: 要素のXPath
- **css_selector**: CSSセレクタ
- **children**: 子要素のリスト
- **children_count**: 子要素の数

## ファイル構成

```
WebScribe/
├── webscribe.py          # メインスクリプト（コマンドライン版）
├── webscribe_gui.py      # GUIアプリケーション
├── example_usage.py      # 使用例
├── requirements.txt      # 依存パッケージ
├── DEVELOPMENT.md        # 開発状況まとめ
└── README.md            # このファイル
```

## 動作環境

- Python 3.x
- Chromeブラウザ
- Windows / macOS / Linux

## ライセンス

このプロジェクトはオープンソースです。

## 作者

yamanishi-naohisa

## リポジトリ

https://github.com/yamanishi-naohisa/WebScribe

