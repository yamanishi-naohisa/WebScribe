"""
WebScribe - Webページのすべての要素を取得して保存するツール
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

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


class TimingStats:
    """時間計測統計クラス"""
    def __init__(self):
        self.timings = defaultdict(list)  # 処理名 -> [時間のリスト]
        self.element_timings = []  # 各要素の処理時間
        self.total_start_time = None
        self.total_end_time = None
    
    def start_total(self):
        """全体の計測開始"""
        self.total_start_time = time.time()
    
    def end_total(self):
        """全体の計測終了"""
        self.total_end_time = time.time()
    
    def record(self, operation_name: str, duration: float):
        """処理時間を記録"""
        self.timings[operation_name].append(duration)
    
    def record_element(self, element_index: int, tag_name: str, total_time: float, breakdown: Dict[str, float]):
        """要素ごとの処理時間を記録"""
        self.element_timings.append({
            'index': element_index,
            'tag_name': tag_name,
            'total_time': total_time,
            'breakdown': breakdown
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """統計サマリーを取得"""
        summary = {}
        
        # 各処理の統計
        for operation, times in self.timings.items():
            if times:
                summary[operation] = {
                    'count': len(times),
                    'total': sum(times),
                    'average': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times)
                }
        
        # 全体の時間
        if self.total_start_time and self.total_end_time:
            summary['total_time'] = self.total_end_time - self.total_start_time
        
        # 要素ごとの統計
        if self.element_timings:
            element_times = [e['total_time'] for e in self.element_timings]
            summary['elements'] = {
                'count': len(self.element_timings),
                'total_time': sum(element_times),
                'average_time': sum(element_times) / len(element_times) if element_times else 0,
                'min_time': min(element_times) if element_times else 0,
                'max_time': max(element_times) if element_times else 0
            }
        
        return summary
    
    def print_summary(self):
        """統計を出力"""
        summary = self.get_summary()
        
        print("\n" + "=" * 60)
        print("処理時間統計")
        print("=" * 60)
        
        if 'total_time' in summary:
            print(f"全体処理時間: {summary['total_time']:.3f}秒")
        
        if 'elements' in summary:
            elem = summary['elements']
            print(f"\n要素処理統計:")
            print(f"  処理した要素数: {elem['count']}")
            print(f"  合計時間: {elem['total_time']:.3f}秒")
            print(f"  平均時間: {elem['average_time']:.4f}秒/要素")
            print(f"  最小時間: {elem['min_time']:.4f}秒")
            print(f"  最大時間: {elem['max_time']:.4f}秒")
        
        print(f"\n処理別統計:")
        for operation, stats in summary.items():
            if operation in ['total_time', 'elements']:
                continue
            print(f"  {operation}:")
            print(f"    実行回数: {stats['count']}")
            print(f"    合計時間: {stats['total']:.3f}秒")
            print(f"    平均時間: {stats['average']:.4f}秒")
            print(f"    最小時間: {stats['min']:.4f}秒")
            print(f"    最大時間: {stats['max']:.4f}秒")
        
        print("=" * 60)
        sys.stdout.flush()


class WebScribe:
    """Webページの要素を取得して保存するクラス"""
    
    def __init__(self, headless: bool = False, wait_time: int = 10, progress_callback=None, enable_timing: bool = True):
        """
        初期化
        
        Args:
            headless: ヘッドレスモードで実行するかどうか
            wait_time: ページ読み込み待機時間（秒）
            progress_callback: 進捗コールバック関数（current, total, message）を受け取る
            enable_timing: 時間計測を有効にするかどうか
        """
        self.wait_time = wait_time
        self.driver = None
        self.progress_callback = progress_callback
        self.enable_timing = enable_timing
        self.timing_stats = TimingStats() if enable_timing else None
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
    
    def _get_element_info(
        self,
        element: WebElement,
        index: int = 0,
        include_xpath: bool = True,
        include_css_selector: bool = True
    ) -> Dict[str, Any]:
        """
        Web要素から情報を抽出
        
        Args:
            element: SeleniumのWebElementオブジェクト
            index: 要素のインデックス
            include_xpath: XPathを取得するかどうか
            include_css_selector: CSSセレクタを取得するかどうか
            
        Returns:
            要素情報の辞書
        """
        element_start_time = time.time()
        breakdown = {}
        
        try:
            # タグ名取得
            t0 = time.time()
            tag_name = element.tag_name
            breakdown['tag_name'] = time.time() - t0
            if self.timing_stats:
                self.timing_stats.record('tag_name', breakdown['tag_name'])
            
            # テキスト取得
            t0 = time.time()
            text = element.text.strip() if element.text else ''
            breakdown['text'] = time.time() - t0
            if self.timing_stats:
                self.timing_stats.record('text', breakdown['text'])
            
            # 表示状態チェック
            t0 = time.time()
            is_displayed = element.is_displayed()
            breakdown['is_displayed'] = time.time() - t0
            if self.timing_stats:
                self.timing_stats.record('is_displayed', breakdown['is_displayed'])
            
            # 有効状態チェック
            t0 = time.time()
            is_enabled = element.is_enabled()
            breakdown['is_enabled'] = time.time() - t0
            if self.timing_stats:
                self.timing_stats.record('is_enabled', breakdown['is_enabled'])
            
            info = {
                'index': index,
                'tag_name': tag_name,
                'text': text,
                'attributes': {},
                'location': {},
                'size': {},
                'is_displayed': is_displayed,
                'is_enabled': is_enabled,
                'children_count': 0,
            }
            
            # XPathとCSSセレクタの取得は時間がかかるため、オプション化
            if include_xpath:
                t0 = time.time()
                try:
                    info['xpath'] = self._get_xpath(element)
                except Exception:
                    info['xpath'] = ''
                breakdown['xpath'] = time.time() - t0
                if self.timing_stats:
                    self.timing_stats.record('xpath', breakdown['xpath'])
            else:
                info['xpath'] = ''
                breakdown['xpath'] = 0
            
            if include_css_selector:
                t0 = time.time()
                try:
                    info['css_selector'] = self._get_css_selector(element)
                except Exception:
                    info['css_selector'] = ''
                breakdown['css_selector'] = time.time() - t0
                if self.timing_stats:
                    self.timing_stats.record('css_selector', breakdown['css_selector'])
            else:
                info['css_selector'] = ''
                breakdown['css_selector'] = 0
            
            # 属性を取得
            t0 = time.time()
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
            breakdown['attributes'] = time.time() - t0
            if self.timing_stats:
                self.timing_stats.record('attributes', breakdown['attributes'])
            
            # 位置情報を取得
            t0 = time.time()
            try:
                location = element.location
                info['location'] = {'x': location['x'], 'y': location['y']}
            except Exception:
                pass
            breakdown['location'] = time.time() - t0
            if self.timing_stats:
                self.timing_stats.record('location', breakdown['location'])
            
            # サイズ情報を取得
            t0 = time.time()
            try:
                size = element.size
                info['size'] = {'width': size['width'], 'height': size['height']}
            except Exception:
                pass
            breakdown['size'] = time.time() - t0
            if self.timing_stats:
                self.timing_stats.record('size', breakdown['size'])
            
            total_time = time.time() - element_start_time
            if self.timing_stats:
                self.timing_stats.record_element(index, tag_name, total_time, breakdown)
            
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
    
    def _collect_all_elements(
        self,
        parent: Optional[WebElement] = None,
        max_depth: int = 50,
        current_depth: int = 0,
        max_elements: int = 10000,
        element_count: List[int] = None,
        include_xpath: bool = True,
        include_css_selector: bool = True
    ) -> List[Dict[str, Any]]:
        """
        すべての表示されている要素を再帰的に収集
        
        Args:
            parent: 親要素（Noneの場合はbody要素）
            max_depth: 最大再帰深度
            current_depth: 現在の深度
            max_elements: 最大要素数（制限）
            element_count: 要素数のカウント用リスト（参照渡し）
            include_xpath: XPathを取得するかどうか
            include_css_selector: CSSセレクタを取得するかどうか
            
        Returns:
            要素情報のリスト
        """
        if element_count is None:
            element_count = [0]
        
        # 深度制限チェック
        if current_depth >= max_depth:
            return []
        
        # 要素数制限チェック
        if element_count[0] >= max_elements:
            print(f"\n警告: 要素数が上限（{max_elements}）に達しました。処理を中断します。")
            sys.stdout.flush()
            return []
        
        elements_data = []
        index = element_count[0]
        
        try:
            # 親要素の検索時間を計測
            t0 = time.time()
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
            find_time = time.time() - t0
            if self.timing_stats and find_time > 0:
                self.timing_stats.record('find_elements', find_time)
            
            for element in elements:
                # 要素数制限チェック
                if element_count[0] >= max_elements:
                    break
                
                try:
                    # 表示チェック時間を計測
                    t0 = time.time()
                    is_displayed = element.is_displayed()
                    display_check_time = time.time() - t0
                    if self.timing_stats:
                        self.timing_stats.record('display_check', display_check_time)
                    
                    # 表示されている要素のみを収集
                    if is_displayed:
                        # 進捗表示（コールバックがある場合は毎回、ない場合は100要素ごと）
                        if self.progress_callback:
                            # コールバックがある場合は、10要素ごとに更新（頻繁すぎると重くなるため）
                            if element_count[0] % 10 == 0 or element_count[0] == 0:
                                self.progress_callback(
                                    current=element_count[0],
                                    total=max_elements,
                                    message=f"要素を収集中... {element_count[0]}個処理済み"
                                )
                        elif element_count[0] % 100 == 0 and element_count[0] > 0:
                            print(f"要素を収集中... {element_count[0]}個処理済み", end='\r')
                            sys.stdout.flush()
                        
                        element_info = self._get_element_info(
                            element,
                            element_count[0],
                            include_xpath=include_xpath,
                            include_css_selector=include_css_selector
                        )
                        element_count[0] += 1
                        
                        # 子要素を再帰的に収集
                        t0 = time.time()
                        try:
                            children = self._collect_all_elements(
                                element,
                                max_depth=max_depth,
                                current_depth=current_depth + 1,
                                max_elements=max_elements,
                                element_count=element_count,
                                include_xpath=include_xpath,
                                include_css_selector=include_css_selector
                            )
                            element_info['children'] = children
                            element_info['children_count'] = len(children)
                        except Exception as e:
                            element_info['children'] = []
                            element_info['children_count'] = 0
                        children_time = time.time() - t0
                        if self.timing_stats:
                            self.timing_stats.record('collect_children', children_time)
                        
                        elements_data.append(element_info)
                except Exception as e:
                    # 要素が無効になった場合はスキップ
                    continue
            
        except Exception as e:
            print(f"\n要素の収集中にエラーが発生しました: {e}")
            sys.stdout.flush()
        
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
        login_info: Optional[Dict[str, Any]] = None,
        max_elements: int = 10000
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
        
        if self.progress_callback:
            self.progress_callback(current=0, total=max_elements, message="要素を収集中...")
        else:
            print("要素を収集中...")
        sys.stdout.flush()
        
        # 要素収集の開始時刻を記録
        start_time = time.time()
        if self.timing_stats:
            self.timing_stats.start_total()
        
        # 要素収集（XPathとCSSセレクタの取得は時間がかかるため、大量の要素がある場合は無効化を推奨）
        # TimeTreeのような複雑なページでは、XPath/CSSセレクタの取得を無効化すると大幅に高速化
        elements = self._collect_all_elements(
            max_depth=50,
            max_elements=max_elements,
            include_xpath=False,  # 高速化のためデフォルトで無効化（必要に応じてTrueに変更可能）
            include_css_selector=False  # 高速化のためデフォルトで無効化（必要に応じてTrueに変更可能）
        )
        
        elapsed_time = time.time() - start_time
        if self.timing_stats:
            self.timing_stats.end_total()
        
        result = {
            'page_info': page_info,
            'elements': elements,
            'total_elements': len(elements)
        }
        
        print(f"\n合計 {len(elements)} 個の要素を収集しました（処理時間: {elapsed_time:.2f}秒）")
        sys.stdout.flush()
        
        # 時間統計を出力
        if self.timing_stats:
            self.timing_stats.print_summary()
        
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
    
    def save_to_html(self, data: Dict[str, Any], output_path: str):
        """
        データをHTMLファイルに保存（ブラウザで表示可能）
        
        Args:
            data: 保存するデータ
            output_path: 出力ファイルパス
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        page_info = data.get('page_info', {})
        elements = data.get('elements', [])
        total_elements = data.get('total_elements', len(elements))
        
        html_content = self._generate_html(data, page_info, elements, total_elements)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTMLデータを保存しました: {output_path}")
        sys.stdout.flush()
    
    def _generate_html(self, data: Dict[str, Any], page_info: Dict[str, Any], 
                       elements: List[Dict[str, Any]], total_elements: int) -> str:
        """HTMLコンテンツを生成"""
        url = page_info.get('url', 'Unknown')
        title = page_info.get('title', 'Unknown')
        timestamp = page_info.get('timestamp', '')
        viewport = page_info.get('viewport_size', {})
        
        html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebScribe - {title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }}
        .header h1 {{
            font-size: 24px;
            margin-bottom: 10px;
        }}
        .header-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 15px;
            font-size: 14px;
        }}
        .header-info-item {{
            background: rgba(255,255,255,0.1);
            padding: 10px;
            border-radius: 4px;
        }}
        .header-info-label {{
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .content {{
            padding: 20px;
        }}
        .element {{
            margin: 10px 0;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            background: #fafafa;
        }}
        .element-header {{
            padding: 12px 15px;
            background: #fff;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #e0e0e0;
            user-select: none;
        }}
        .element-header:hover {{
            background: #f0f0f0;
        }}
        .element-header.active {{
            background: #e3f2fd;
        }}
        .element-title {{
            display: flex;
            align-items: center;
            gap: 10px;
            flex: 1;
        }}
        .element-tag {{
            background: #667eea;
            color: white;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
        }}
        .element-index {{
            color: #666;
            font-size: 12px;
        }}
        .element-toggle {{
            color: #666;
            font-size: 18px;
            transition: transform 0.2s;
        }}
        .element-toggle.expanded {{
            transform: rotate(90deg);
        }}
        .element-details {{
            display: none;
            padding: 15px;
            background: white;
            border-top: 1px solid #e0e0e0;
        }}
        .element-details.show {{
            display: block;
        }}
        .detail-row {{
            margin: 8px 0;
            padding: 8px;
            background: #f9f9f9;
            border-left: 3px solid #667eea;
        }}
        .detail-label {{
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }}
        .detail-value {{
            color: #666;
            word-break: break-word;
        }}
        .detail-value pre {{
            background: #f5f5f5;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 12px;
            margin-top: 5px;
        }}
        .children-container {{
            margin-left: 20px;
            margin-top: 10px;
            border-left: 2px solid #ddd;
            padding-left: 15px;
        }}
        .stats {{
            background: #e8f5e9;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .stats-number {{
            font-size: 32px;
            font-weight: bold;
            color: #2e7d32;
        }}
        .empty {{
            text-align: center;
            padding: 40px;
            color: #999;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>WebScribe - ページ要素一覧</h1>
            <div class="header-info">
                <div class="header-info-item">
                    <div class="header-info-label">ページタイトル</div>
                    <div>{self._escape_html(title)}</div>
                </div>
                <div class="header-info-item">
                    <div class="header-info-label">URL</div>
                    <div><a href="{self._escape_html(url)}" target="_blank" style="color: white; text-decoration: underline;">{self._escape_html(url)}</a></div>
                </div>
                <div class="header-info-item">
                    <div class="header-info-label">取得日時</div>
                    <div>{self._escape_html(timestamp)}</div>
                </div>
                <div class="header-info-item">
                    <div class="header-info-label">ビューポートサイズ</div>
                    <div>{viewport.get('width', 'N/A')} × {viewport.get('height', 'N/A')}</div>
                </div>
            </div>
        </div>
        <div class="content">
            <div class="stats">
                <div class="stats-number">{total_elements}</div>
                <div>個の要素を取得</div>
            </div>
"""
        
        if elements:
            html += self._generate_elements_html(elements, depth=0)
        else:
            html += '<div class="empty">要素がありません</div>'
        
        html += """
        </div>
    </div>
    <script>
        document.querySelectorAll('.element-header').forEach(header => {
            header.addEventListener('click', function() {
                const details = this.nextElementSibling;
                const toggle = this.querySelector('.element-toggle');
                const isExpanded = details.classList.contains('show');
                
                if (isExpanded) {
                    details.classList.remove('show');
                    toggle.classList.remove('expanded');
                    this.classList.remove('active');
                } else {
                    details.classList.add('show');
                    toggle.classList.add('expanded');
                    this.classList.add('active');
                }
            });
        });
    </script>
</body>
</html>"""
        
        return html
    
    def _generate_elements_html(self, elements: List[Dict[str, Any]], depth: int = 0) -> str:
        """要素のHTMLを再帰的に生成"""
        if depth > 10:  # 深度制限
            return ""
        
        html = ""
        for element in elements:
            if not isinstance(element, dict):
                continue
            
            tag_name = element.get('tag_name', '')
            index = element.get('index', 0)
            text = element.get('text', '')
            attributes = element.get('attributes', {})
            location = element.get('location', {})
            size = element.get('size', {})
            is_displayed = element.get('is_displayed', False)
            is_enabled = element.get('is_enabled', False)
            children = element.get('children', [])
            children_count = element.get('children_count', 0)
            xpath = element.get('xpath', '')
            css_selector = element.get('css_selector', '')
            
            # テキストのプレビュー（長すぎる場合は切り詰め）
            text_preview = text[:100] if len(text) > 100 else text
            if len(text) > 100:
                text_preview += '...'
            
            html += f"""
            <div class="element">
                <div class="element-header">
                    <div class="element-title">
                        <span class="element-tag">{self._escape_html(tag_name)}</span>
                        <span class="element-index">[{index}]</span>
                        {f'<span style="color: #666; font-size: 12px;">{self._escape_html(text_preview)}</span>' if text_preview else ''}
                    </div>
                    <span class="element-toggle">▶</span>
                </div>
                <div class="element-details">
                    <div class="detail-row">
                        <div class="detail-label">タグ名</div>
                        <div class="detail-value">{self._escape_html(tag_name)}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">インデックス</div>
                        <div class="detail-value">{index}</div>
                    </div>
"""
            
            if text:
                html += f"""
                    <div class="detail-row">
                        <div class="detail-label">テキスト</div>
                        <div class="detail-value"><pre>{self._escape_html(text)}</pre></div>
                    </div>
"""
            
            if attributes:
                html += f"""
                    <div class="detail-row">
                        <div class="detail-label">属性</div>
                        <div class="detail-value"><pre>{self._escape_html(json.dumps(attributes, ensure_ascii=False, indent=2))}</pre></div>
                    </div>
"""
            
            if location:
                html += f"""
                    <div class="detail-row">
                        <div class="detail-label">位置</div>
                        <div class="detail-value">x: {location.get('x', 'N/A')}, y: {location.get('y', 'N/A')}</div>
                    </div>
"""
            
            if size:
                html += f"""
                    <div class="detail-row">
                        <div class="detail-label">サイズ</div>
                        <div class="detail-value">width: {size.get('width', 'N/A')}, height: {size.get('height', 'N/A')}</div>
                    </div>
"""
            
            html += f"""
                    <div class="detail-row">
                        <div class="detail-label">表示状態</div>
                        <div class="detail-value">表示: {'はい' if is_displayed else 'いいえ'}, 有効: {'はい' if is_enabled else 'いいえ'}</div>
                    </div>
"""
            
            if xpath:
                html += f"""
                    <div class="detail-row">
                        <div class="detail-label">XPath</div>
                        <div class="detail-value"><pre>{self._escape_html(xpath)}</pre></div>
                    </div>
"""
            
            if css_selector:
                html += f"""
                    <div class="detail-row">
                        <div class="detail-label">CSSセレクタ</div>
                        <div class="detail-value"><pre>{self._escape_html(css_selector)}</pre></div>
                    </div>
"""
            
            if children_count > 0:
                html += f"""
                    <div class="detail-row">
                        <div class="detail-label">子要素数</div>
                        <div class="detail-value">{children_count}</div>
                    </div>
"""
            
            if children:
                html += """
                    <div class="detail-row">
                        <div class="detail-label">子要素</div>
                        <div class="detail-value">
                            <div class="children-container">
"""
                html += self._generate_elements_html(children, depth + 1)
                html += """
                            </div>
                        </div>
                    </div>
"""
            
            html += """
                </div>
            </div>
"""
        
        return html
    
    def _escape_html(self, text: str) -> str:
        """HTMLエスケープ"""
        if not isinstance(text, str):
            text = str(text)
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
    
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
            # HTMLファイルも保存
            html_output = str(Path(args.output).with_suffix('.html'))
            scribe.save_to_html(data, html_output)
            print("\n完了しました！")
            print(f"出力ファイル (JSON): {args.output}")
            print(f"出力ファイル (HTML): {html_output}")
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

