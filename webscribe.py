"""
WebScribe - Webページのすべての要素を取得して保存するツール
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

try:
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False


class WebScribe:
    """Webページの要素を取得して保存するクラス"""
    
    def __init__(self, headless: bool = False, wait_time: int = 10):
        """
        初期化
        
        Args:
            headless: ヘッドレスモードで実行するかどうか
            wait_time: ページ読み込み待機時間（秒）
        """
        self.wait_time = wait_time
        self.driver = None
        self._setup_driver(headless)
    
    def _setup_driver(self, headless: bool):
        """Seleniumドライバーをセットアップ"""
        options = webdriver.ChromeOptions()
        if headless:
            # 新しいヘッドレスモードを使用（Chrome 109+）
            options.add_argument('--headless=new')
        
        # 自動化検出を回避するための設定
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # より完全なユーザーエージェント（実際のChromeブラウザに近いもの）
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        options.add_argument(f'user-agent={user_agent}')
        
        # ウィンドウサイズを設定（モバイルサイト対策）
        options.add_argument('--window-size=1920,1080')
        
        try:
            sys.stdout.flush()
            print("ChromeDriverを初期化中...")
            sys.stdout.flush()
            
            if WEBDRIVER_MANAGER_AVAILABLE:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)
            
            # 自動化検出を回避するためのJavaScript実行
            try:
                self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": user_agent
                })
            except Exception:
                # CDPコマンドが使えない場合はスキップ
                pass
            
            try:
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception:
                pass
            
            self.driver.implicitly_wait(self.wait_time)
            print("ChromeDriverの初期化が完了しました")
            sys.stdout.flush()
        except Exception as e:
            print(f"Chromeドライバーの初期化に失敗しました: {e}", file=sys.stderr)
            sys.stderr.flush()
            if not WEBDRIVER_MANAGER_AVAILABLE:
                print("webdriver-managerをインストールすると、ChromeDriverが自動的に管理されます。", file=sys.stderr)
                print("pip install webdriver-manager", file=sys.stderr)
            sys.stderr.flush()
            raise
    
    def _get_element_info(self, element: WebElement, index: int = 0) -> Dict[str, Any]:
        """
        Web要素から情報を抽出
        
        Args:
            element: SeleniumのWebElementオブジェクト
            index: 要素のインデックス
            
        Returns:
            要素情報の辞書
        """
        try:
            info = {
                'index': index,
                'tag_name': element.tag_name,
                'text': element.text.strip() if element.text else '',
                'attributes': {},
                'location': {},
                'size': {},
                'is_displayed': element.is_displayed(),
                'is_enabled': element.is_enabled(),
                'children_count': 0,
                'xpath': self._get_xpath(element),
                'css_selector': self._get_css_selector(element)
            }
            
            # 属性を取得
            try:
                attributes = self.driver.execute_script(
                    'var items = {}; '
                    'for (index = 0; index < arguments[0].attributes.length; ++index) { '
                    '  items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value '
                    '}; '
                    'return items;',
                    element
                )
                info['attributes'] = attributes
            except Exception as e:
                print(f"属性の取得に失敗しました: {e}")
            
            # 位置情報を取得
            try:
                location = element.location
                info['location'] = {'x': location['x'], 'y': location['y']}
            except Exception:
                pass
            
            # サイズ情報を取得
            try:
                size = element.size
                info['size'] = {'width': size['width'], 'height': size['height']}
            except Exception:
                pass
            
            return info
        except Exception as e:
            print(f"要素情報の取得中にエラーが発生しました: {e}")
            return {'index': index, 'error': str(e)}
    
    def _get_xpath(self, element: WebElement) -> str:
        """要素のXPathを取得"""
        try:
            return self.driver.execute_script(
                'function getElementXPath(element) {'
                '  if (element.id !== "") {'
                '    return "//*[@id=\'" + element.id + "\']";'
                '  }'
                '  if (element === document.body) {'
                '    return "/html/body";'
                '  }'
                '  var ix = 0;'
                '  var siblings = element.parentNode.childNodes;'
                '  for (var i = 0; i < siblings.length; i++) {'
                '    var sibling = siblings[i];'
                '    if (sibling === element) {'
                '      return getElementXPath(element.parentNode) + "/" + element.tagName.toLowerCase() + "[" + (ix + 1) + "]";'
                '    }'
                '    if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {'
                '      ix++;'
                '    }'
                '  }'
                '}'
                'return getElementXPath(arguments[0]);',
                element
            )
        except Exception:
            return ''
    
    def _get_css_selector(self, element: WebElement) -> str:
        """要素のCSSセレクタを取得"""
        try:
            return self.driver.execute_script(
                'function getElementCSSSelector(element) {'
                '  if (element.id) {'
                '    return "#" + element.id;'
                '  }'
                '  var path = [];'
                '  while (element && element.nodeType === Node.ELEMENT_NODE) {'
                '    var selector = element.nodeName.toLowerCase();'
                '    if (element.className) {'
                '      selector += "." + element.className.split(" ").join(".");'
                '    }'
                '    path.unshift(selector);'
                '    element = element.parentNode;'
                '  }'
                '  return path.join(" > ");'
                '}'
                'return getElementCSSSelector(arguments[0]);',
                element
            )
        except Exception:
            return ''
    
    def _collect_all_elements(self, parent: Optional[WebElement] = None) -> List[Dict[str, Any]]:
        """
        すべての表示されている要素を再帰的に収集
        
        Args:
            parent: 親要素（Noneの場合はbody要素）
            
        Returns:
            要素情報のリスト
        """
        elements_data = []
        index = 0
        
        try:
            if parent is None:
                # body要素から開始
                try:
                    body = self.driver.find_element(By.TAG_NAME, "body")
                except NoSuchElementException:
                    body = self.driver.find_element(By.XPATH, "//body")
                elements = [body]
            else:
                try:
                    elements = parent.find_elements(By.XPATH, "./*")
                except Exception:
                    elements = []
            
            for element in elements:
                try:
                    # 表示されている要素のみを収集
                    if element.is_displayed():
                        element_info = self._get_element_info(element, index)
                        index += 1
                        
                        # 子要素を再帰的に収集
                        try:
                            children = self._collect_all_elements(element)
                            element_info['children'] = children
                            element_info['children_count'] = len(children)
                        except Exception:
                            element_info['children'] = []
                            element_info['children_count'] = 0
                        
                        elements_data.append(element_info)
                except Exception as e:
                    # 要素が無効になった場合はスキップ
                    continue
            
        except Exception as e:
            print(f"要素の収集中にエラーが発生しました: {e}")
        
        return elements_data
    
    def _wait_for_page_load(self, additional_wait: int = 5):
        """ページとJavaScriptの読み込み完了を待機"""
        # DOMContentLoadedを待つ
        WebDriverWait(self.driver, self.wait_time).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        
        # JavaScriptの実行完了を待つ（複数回チェック）
        for i in range(additional_wait):
            time.sleep(1)
            try:
                # ページの変更がないことを確認
                old_height = self.driver.execute_script('return document.body.scrollHeight')
                time.sleep(0.5)
                new_height = self.driver.execute_script('return document.body.scrollHeight')
                if old_height == new_height:
                    # さらに少し待機してJavaScriptの実行を確実にする
                    time.sleep(1)
                    break
            except Exception:
                pass
        
        # スクロールして遅延読み込みコンテンツを読み込む
        try:
            total_height = self.driver.execute_script('return document.body.scrollHeight')
            viewport_height = self.driver.execute_script('return window.innerHeight')
            
            # 少しずつスクロール
            for scroll in range(0, total_height, viewport_height):
                self.driver.execute_script(f'window.scrollTo(0, {scroll});')
                time.sleep(0.3)
            
            # トップに戻る
            self.driver.execute_script('window.scrollTo(0, 0);')
            time.sleep(0.5)
        except Exception as e:
            print(f"スクロール処理中にエラー: {e}")
    
    def login(
        self,
        login_url: str,
        username: str,
        password: str,
        username_selector: str = None,
        password_selector: str = None,
        submit_selector: str = None,
        wait_after_login: int = 3
    ) -> bool:
        """
        ログイン処理を実行
        
        Args:
            login_url: ログインページのURL
            username: ユーザー名
            password: パスワード
            username_selector: ユーザー名入力フィールドのセレクタ（XPathまたはCSSセレクタ）
            password_selector: パスワード入力フィールドのセレクタ（XPathまたはCSSセレクタ）
            submit_selector: ログインボタンのセレクタ（XPathまたはCSSセレクタ）
            wait_after_login: ログイン後の待機時間（秒）
            
        Returns:
            ログインが成功したかどうか
        """
        try:
            print(f"ログインページにアクセス中: {login_url}")
            sys.stdout.flush()
            self.driver.get(login_url)
            
            # ページの読み込みを待機
            WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(1)
            
            # セレクタが指定されていない場合は自動検出を試みる
            if not username_selector:
                # よくあるユーザー名フィールドのセレクタを試す
                possible_selectors = [
                    "input[type='email']",
                    "input[type='text'][name*='user']",
                    "input[type='text'][name*='login']",
                    "input[type='text'][name*='account']",
                    "input[name='username']",
                    "input[id*='user']",
                    "input[id*='login']",
                ]
                username_selector = self._find_element_selector(possible_selectors)
            
            if not password_selector:
                # よくあるパスワードフィールドのセレクタを試す
                possible_selectors = [
                    "input[type='password']",
                    "input[name='password']",
                    "input[id*='pass']",
                ]
                password_selector = self._find_element_selector(possible_selectors)
            
            if not submit_selector:
                # よくあるログインボタンのセレクタを試す
                possible_selectors = [
                    "button[type='submit']",
                    "input[type='submit']",
                    "button:contains('ログイン')",
                    "button:contains('Login')",
                    "input[value*='ログイン']",
                    "input[value*='Login']",
                ]
                submit_selector = self._find_element_selector(possible_selectors)
            
            # ユーザー名を入力
            if username_selector:
                try:
                    username_field = self._find_element(username_selector)
                    username_field.clear()
                    username_field.send_keys(username)
                    print("ユーザー名を入力しました")
                    sys.stdout.flush()
                    time.sleep(0.5)
                except Exception as e:
                    print(f"ユーザー名フィールドが見つかりません: {e}")
                    sys.stderr.flush()
                    return False
            else:
                print("エラー: ユーザー名フィールドのセレクタを指定してください")
                sys.stderr.flush()
                return False
            
            # パスワードを入力
            if password_selector:
                try:
                    password_field = self._find_element(password_selector)
                    password_field.clear()
                    password_field.send_keys(password)
                    print("パスワードを入力しました")
                    sys.stdout.flush()
                    time.sleep(0.5)
                except Exception as e:
                    print(f"パスワードフィールドが見つかりません: {e}")
                    sys.stderr.flush()
                    return False
            else:
                print("エラー: パスワードフィールドのセレクタを指定してください")
                sys.stderr.flush()
                return False
            
            # ログインボタンをクリック
            if submit_selector:
                try:
                    submit_button = self._find_element(submit_selector)
                    submit_button.click()
                    print("ログインボタンをクリックしました")
                    sys.stdout.flush()
                except Exception as e:
                    print(f"ログインボタンが見つかりません: {e}")
                    sys.stderr.flush()
                    return False
            else:
                # セレクタが見つからない場合、Enterキーで送信を試みる
                print("ログインボタンのセレクタが見つからないため、Enterキーで送信を試みます")
                sys.stdout.flush()
                from selenium.webdriver.common.keys import Keys
                password_field.send_keys(Keys.RETURN)
            
            # ログイン後の遷移を待機
            print(f"ログイン後の遷移を待機中...（{wait_after_login}秒）")
            sys.stdout.flush()
            time.sleep(wait_after_login)
            
            # ログインページから遷移したか確認
            current_url = self.driver.current_url
            if current_url != login_url and 'login' not in current_url.lower() and 'signin' not in current_url.lower():
                print(f"ログイン成功: {current_url}")
                sys.stdout.flush()
                return True
            else:
                print(f"警告: ログインページから遷移していない可能性があります: {current_url}")
                sys.stdout.flush()
                # 遷移していなくても成功とする（サイトによってはリダイレクトしない場合がある）
                return True
                
        except Exception as e:
            print(f"ログイン処理中にエラーが発生しました: {e}")
            sys.stderr.flush()
            import traceback
            traceback.print_exc()
            return False
    
    def _find_element_selector(self, selectors: List[str]) -> Optional[str]:
        """複数のセレクタを試して、最初に見つかったものを返す"""
        for selector in selectors:
            try:
                if selector.startswith('//') or selector.startswith('(//'):
                    # XPath
                    elements = self.driver.find_elements(By.XPATH, selector)
                else:
                    # CSSセレクタ
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and any(e.is_displayed() for e in elements):
                    return selector
            except Exception:
                continue
        return None
    
    def _find_element(self, selector: str):
        """セレクタから要素を見つける（XPathまたはCSSセレクタ）"""
        if selector.startswith('//') or selector.startswith('(//'):
            # XPath
            return self.driver.find_element(By.XPATH, selector)
        else:
            # CSSセレクタ
            return self.driver.find_element(By.CSS_SELECTOR, selector)
    
    def scrape_page(
        self,
        url: str,
        wait_for_load: bool = True,
        wait_javascript: bool = True,
        login_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Webページをスクレイピングして要素を取得
        
        Args:
            url: スクレイピングするURL
            wait_for_load: ページの読み込みを待つかどうか
            wait_javascript: JavaScriptの実行完了を待つかどうか
            login_info: ログイン情報（辞書形式）
                - login_url: ログインページのURL
                - username: ユーザー名
                - password: パスワード
                - username_selector: ユーザー名フィールドのセレクタ（省略可）
                - password_selector: パスワードフィールドのセレクタ（省略可）
                - submit_selector: ログインボタンのセレクタ（省略可）
            
        Returns:
            ページ情報と要素データを含む辞書
        """
        # ログインが必要な場合
        if login_info:
            login_url = login_info.get('login_url')
            username = login_info.get('username')
            password = login_info.get('password')
            username_selector = login_info.get('username_selector')
            password_selector = login_info.get('password_selector')
            submit_selector = login_info.get('submit_selector')
            wait_after_login = login_info.get('wait_after_login', 3)
            
            if login_url and username and password:
                print("ログイン処理を開始します...")
                sys.stdout.flush()
                login_success = self.login(
                    login_url=login_url,
                    username=username,
                    password=password,
                    username_selector=username_selector,
                    password_selector=password_selector,
                    submit_selector=submit_selector,
                    wait_after_login=wait_after_login
                )
                
                if not login_success:
                    raise Exception("ログインに失敗しました")
                
                print(f"ログイン成功。目的のページにアクセス中: {url}")
                sys.stdout.flush()
        
        print(f"ページにアクセス中: {url}")
        sys.stdout.flush()
        self.driver.get(url)
        
        if wait_for_load:
            # ページが完全に読み込まれるまで待機
            try:
                WebDriverWait(self.driver, self.wait_time).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                print("ページの基本構造が読み込まれました")
                sys.stdout.flush()
                
                if wait_javascript:
                    print("JavaScriptの実行完了を待機中...")
                    sys.stdout.flush()
                    self._wait_for_page_load(additional_wait=5)
                    print("JavaScriptの実行が完了しました")
                    sys.stdout.flush()
                else:
                    # 最小限の待機
                    time.sleep(2)
            except TimeoutException:
                print("警告: ページの読み込みがタイムアウトしました")
                sys.stdout.flush()
        
        # ページ情報を取得
        page_info = {
            'url': self.driver.current_url,
            'title': self.driver.title,
            'timestamp': datetime.now().isoformat(),
            'viewport_size': {
                'width': self.driver.get_window_size()['width'],
                'height': self.driver.get_window_size()['height']
            }
        }
        
        print("要素を収集中...")
        sys.stdout.flush()
        elements = self._collect_all_elements()
        
        result = {
            'page_info': page_info,
            'elements': elements,
            'total_elements': len(elements)
        }
        
        print(f"合計 {len(elements)} 個の要素を収集しました")
        sys.stdout.flush()
        return result
    
    def save_to_json(self, data: Dict[str, Any], output_path: str):
        """
        データをJSONファイルに保存
        
        Args:
            data: 保存するデータ
            output_path: 出力ファイルパス
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"データを保存しました: {output_path}")
        sys.stdout.flush()
    
    def close(self):
        """ブラウザを閉じる"""
        if self.driver:
            self.driver.quit()
    
    def __enter__(self):
        """コンテキストマネージャー用"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー用"""
        self.close()


def main():
    """メイン関数 - 使用例"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Webページのすべての要素を取得して保存します')
    parser.add_argument('url', help='スクレイピングするURL')
    parser.add_argument('-o', '--output', default='output.json', help='出力ファイルパス（デフォルト: output.json）')
    parser.add_argument('--headless', action='store_true', help='ヘッドレスモードで実行')
    parser.add_argument('--wait', type=int, default=10, help='ページ読み込み待機時間（秒、デフォルト: 10）')
    
    args = parser.parse_args()
    
    try:
        print("=" * 50)
        print("WebScribe - Webページ要素取得ツール")
        print("=" * 50)
        sys.stdout.flush()
        
        with WebScribe(headless=args.headless, wait_time=args.wait) as scribe:
            data = scribe.scrape_page(args.url)
            scribe.save_to_json(data, args.output)
            print("\n完了しました！")
            print(f"出力ファイル: {args.output}")
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n中断されました")
        sys.stdout.flush()
    except Exception as e:
        print(f"\nエラーが発生しました: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.stderr.flush()


if __name__ == '__main__':
    main()

