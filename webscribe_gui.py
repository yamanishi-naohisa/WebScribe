"""
WebScribe GUI - ダイアログでURLを指定してWeb要素を取得するGUIアプリケーション
"""
import sys
import json
import threading
import io
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from tkinter import (
    Tk, Label, Entry, Button, Checkbutton, BooleanVar,
    StringVar, Text, Scrollbar, messagebox, filedialog,
    ttk, Frame
)
from tkinter.scrolledtext import ScrolledText

from webscribe import WebScribe


class WebScribeGUI:
    """WebScribeのGUIアプリケーション"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("WebScribe - Webページ要素取得ツール")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        
        # 変数の初期化
        self.url_var = StringVar(value="https://example.com")
        self.output_var = StringVar(value="output.json")
        self.headless_var = BooleanVar(value=True)
        self.wait_time_var = StringVar(value="10")
        self.need_login_var = BooleanVar(value=False)
        self.login_url_var = StringVar(value="")
        self.username_var = StringVar(value="")
        self.password_var = StringVar(value="")
        self.username_selector_var = StringVar(value="")
        self.password_selector_var = StringVar(value="")
        self.submit_selector_var = StringVar(value="")
        self.is_running = False
        self.current_element_count = 0
        self.max_elements = 10000
        
        # 設定ファイルのパス
        self.settings_file = Path(__file__).parent / "webscribe_settings.json"
        
        self._create_widgets()
        
        # 起動時に設定を読み込む
        self.load_settings()
        
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        main_frame = Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill='both', expand=True)
        
        # URL入力セクション
        url_frame = Frame(main_frame)
        url_frame.pack(fill='x', pady=(0, 10))
        
        Label(url_frame, text="URL:", font=('Arial', 10, 'bold')).pack(anchor='w')
        url_entry = Entry(url_frame, textvariable=self.url_var, font=('Arial', 10))
        url_entry.pack(fill='x', pady=(5, 0))
        url_entry.bind('<Return>', lambda e: self.start_scraping())
        
        # 出力ファイルセクション
        output_frame = Frame(main_frame)
        output_frame.pack(fill='x', pady=(0, 10))
        
        Label(output_frame, text="出力ファイル:", font=('Arial', 10, 'bold')).pack(anchor='w')
        output_inner_frame = Frame(output_frame)
        output_inner_frame.pack(fill='x', pady=(5, 0))
        
        output_entry = Entry(output_inner_frame, textvariable=self.output_var, font=('Arial', 10))
        output_entry.pack(side='left', fill='x', expand=True)
        
        browse_button = Button(
            output_inner_frame,
            text="参照...",
            command=self.browse_output_file,
            width=10
        )
        browse_button.pack(side='right', padx=(5, 0))
        
        # オプションセクション
        options_frame = Frame(main_frame)
        options_frame.pack(fill='x', pady=(0, 10))
        
        Label(options_frame, text="オプション:", font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        
        # ヘッドレスモード
        headless_check = Checkbutton(
            options_frame,
            text="ヘッドレスモード（ブラウザを表示しない）",
            variable=self.headless_var,
            font=('Arial', 9)
        )
        headless_check.pack(anchor='w')
        
        # 待機時間
        wait_frame = Frame(options_frame)
        wait_frame.pack(anchor='w', pady=(5, 0))
        
        Label(wait_frame, text="待機時間（秒）:", font=('Arial', 9)).pack(side='left')
        wait_entry = Entry(wait_frame, textvariable=self.wait_time_var, width=10, font=('Arial', 9))
        wait_entry.pack(side='left', padx=(5, 0))
        
        # ログイン情報セクション
        login_frame = Frame(main_frame)
        login_frame.pack(fill='x', pady=(0, 10))
        
        login_check = Checkbutton(
            login_frame,
            text="ログインが必要なページ",
            variable=self.need_login_var,
            font=('Arial', 10, 'bold'),
            command=self._toggle_login_fields
        )
        login_check.pack(anchor='w', pady=(0, 5))
        
        # ログイン情報の入力フィールド（初期状態では非表示）
        self.login_details_frame = Frame(login_frame)
        
        Label(self.login_details_frame, text="ログインURL:", font=('Arial', 9)).pack(anchor='w')
        Entry(self.login_details_frame, textvariable=self.login_url_var, font=('Arial', 9)).pack(fill='x', pady=(2, 5))
        
        login_input_frame = Frame(self.login_details_frame)
        login_input_frame.pack(fill='x', pady=(0, 5))
        
        Label(login_input_frame, text="ユーザー名:", font=('Arial', 9), width=12).pack(side='left')
        Entry(login_input_frame, textvariable=self.username_var, font=('Arial', 9)).pack(side='left', fill='x', expand=True, padx=(5, 0))
        
        Label(login_input_frame, text="パスワード:", font=('Arial', 9), width=12).pack(side='left', padx=(10, 0))
        password_entry = Entry(login_input_frame, textvariable=self.password_var, font=('Arial', 9), show='*')
        password_entry.pack(side='left', fill='x', expand=True, padx=(5, 0))
        
        Label(self.login_details_frame, text="セレクタ（省略可、自動検出を試みます）:", font=('Arial', 8), fg='gray').pack(anchor='w', pady=(5, 2))
        
        selector_frame = Frame(self.login_details_frame)
        selector_frame.pack(fill='x')
        
        Label(selector_frame, text="ユーザー名:", font=('Arial', 8), width=12).pack(side='left')
        Entry(selector_frame, textvariable=self.username_selector_var, font=('Arial', 8)).pack(side='left', fill='x', expand=True, padx=(2, 5))
        
        Label(selector_frame, text="パスワード:", font=('Arial', 8), width=12).pack(side='left')
        Entry(selector_frame, textvariable=self.password_selector_var, font=('Arial', 8)).pack(side='left', fill='x', expand=True, padx=(2, 5))
        
        Label(self.login_details_frame, text="ログインボタン:", font=('Arial', 8), width=12).pack(anchor='w', pady=(2, 0))
        Entry(self.login_details_frame, textvariable=self.submit_selector_var, font=('Arial', 8)).pack(fill='x', pady=(2, 0))
        
        # 実行ボタン
        button_frame = Frame(main_frame)
        button_frame.pack(fill='x', pady=(10, 10))
        
        self.execute_button = Button(
            button_frame,
            text="実行",
            command=self.start_scraping,
            font=('Arial', 11, 'bold'),
            bg='#4CAF50',
            fg='white',
            padx=20,
            pady=10,
            cursor='hand2'
        )
        self.execute_button.pack(side='left')
        
        self.stop_button = Button(
            button_frame,
            text="停止",
            command=self.stop_scraping,
            font=('Arial', 11),
            bg='#f44336',
            fg='white',
            padx=20,
            pady=10,
            state='disabled',
            cursor='hand2'
        )
        self.stop_button.pack(side='left', padx=(10, 0))
        
        # 設定ボタン
        settings_frame = Frame(button_frame)
        settings_frame.pack(side='right')
        
        save_settings_button = Button(
            settings_frame,
            text="設定を保存",
            command=self.save_settings,
            font=('Arial', 9),
            bg='#2196F3',
            fg='white',
            padx=10,
            pady=5,
            cursor='hand2'
        )
        save_settings_button.pack(side='left', padx=(10, 0))
        
        load_settings_button = Button(
            settings_frame,
            text="設定を読み込み",
            command=lambda: self.load_settings(show_message=True),
            font=('Arial', 9),
            bg='#FF9800',
            fg='white',
            padx=10,
            pady=5,
            cursor='hand2'
        )
        load_settings_button.pack(side='left', padx=(5, 0))
        
        # 進捗表示セクション
        progress_frame = Frame(main_frame)
        progress_frame.pack(fill='x', pady=(0, 10))
        
        Label(progress_frame, text="進捗状況:", font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        
        # 進捗バー
        self.progress = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=400,
            maximum=100
        )
        self.progress.pack(fill='x', pady=(0, 5))
        
        # 進捗情報表示（要素数、メッセージなど）
        progress_info_frame = Frame(progress_frame)
        progress_info_frame.pack(fill='x')
        
        self.progress_label = Label(
            progress_info_frame,
            text="待機中...",
            font=('Arial', 9),
            fg='#666666',
            anchor='w'
        )
        self.progress_label.pack(side='left', fill='x', expand=True)
        
        self.element_count_label = Label(
            progress_info_frame,
            text="",
            font=('Arial', 9, 'bold'),
            fg='#2196F3',
            anchor='e'
        )
        self.element_count_label.pack(side='right')
        
        # ログ表示エリア
        log_label_frame = Frame(main_frame)
        log_label_frame.pack(fill='x', pady=(0, 5))
        
        Label(log_label_frame, text="ログ:", font=('Arial', 10, 'bold')).pack(side='left')
        
        clear_button = Button(
            log_label_frame,
            text="クリア",
            command=self.clear_log,
            font=('Arial', 8),
            width=8
        )
        clear_button.pack(side='right')
        
        # ログテキストエリア（スクロール可能）
        log_frame = Frame(main_frame)
        log_frame.pack(fill='both', expand=True)
        
        self.log_text = ScrolledText(
            log_frame,
            wrap='word',
            font=('Consolas', 9),
            bg='#f5f5f5',
            state='disabled'
        )
        self.log_text.pack(fill='both', expand=True)
        
        # 初期メッセージ
        self.log("WebScribe GUIを起動しました。")
        if self.settings_file.exists():
            self.log("前回の設定を読み込みました。")
        self.log("URLを入力して「実行」ボタンをクリックしてください。\n")
        
    def _toggle_login_fields(self):
        """ログイン情報入力フィールドの表示/非表示を切り替え"""
        if self.need_login_var.get():
            self.login_details_frame.pack(fill='x', pady=(5, 0))
        else:
            self.login_details_frame.pack_forget()
    
    def update_progress(self, current: int, total: int, message: str):
        """進捗情報を更新"""
        self.current_element_count = current
        self.max_elements = total
        
        # 進捗率を計算
        if total > 0:
            progress_percent = min(100, int((current / total) * 100))
            self.progress['value'] = progress_percent
        else:
            self.progress['value'] = 0
        
        # ラベルを更新
        self.progress_label.config(text=message)
        self.element_count_label.config(text=f"{current} / {total} 要素" if total > 0 else f"{current} 要素")
        
        # GUIを更新
        self.root.update_idletasks()
        
    def log(self, message: str):
        """ログメッセージを表示"""
        self.log_text.config(state='normal')
        self.log_text.insert('end', f"{message}\n")
        self.log_text.see('end')
        self.log_text.config(state='disabled')
        self.root.update_idletasks()
        
    def clear_log(self):
        """ログをクリア"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, 'end')
        self.log_text.config(state='disabled')
        
    def browse_output_file(self):
        """出力ファイルの保存先を選択"""
        filename = filedialog.asksaveasfilename(
            title="出力ファイルを保存",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.output_var.set(filename)
    
    def save_settings(self):
        """現在の設定をファイルに保存"""
        try:
            settings = {
                'url': self.url_var.get(),
                'output_file': self.output_var.get(),
                'headless': self.headless_var.get(),
                'wait_time': self.wait_time_var.get(),
                'need_login': self.need_login_var.get(),
                'login_url': self.login_url_var.get(),
                'username': self.username_var.get(),
                'password': self.password_var.get(),  # 注意: 平文で保存されます
                'username_selector': self.username_selector_var.get(),
                'password_selector': self.password_selector_var.get(),
                'submit_selector': self.submit_selector_var.get(),
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("成功", f"設定を保存しました。\n{self.settings_file}")
            self.log(f"設定を保存しました: {self.settings_file}")
        except Exception as e:
            messagebox.showerror("エラー", f"設定の保存に失敗しました:\n{e}")
            self.log(f"設定の保存エラー: {e}")
    
    def load_settings(self, show_message: bool = False):
        """保存された設定をファイルから読み込み
        
        Args:
            show_message: メッセージを表示するかどうか（デフォルト: False）
        """
        try:
            if not self.settings_file.exists():
                if show_message:
                    messagebox.showinfo("情報", "設定ファイルが見つかりません。")
                return  # 設定ファイルが存在しない場合は何もしない
            
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            # 設定を復元
            if 'url' in settings:
                self.url_var.set(settings.get('url', ''))
            if 'output_file' in settings:
                self.output_var.set(settings.get('output_file', 'output.json'))
            if 'headless' in settings:
                self.headless_var.set(settings.get('headless', True))
            if 'wait_time' in settings:
                self.wait_time_var.set(str(settings.get('wait_time', '10')))
            if 'need_login' in settings:
                need_login = settings.get('need_login', False)
                self.need_login_var.set(need_login)
                if need_login:
                    self._toggle_login_fields()
            if 'login_url' in settings:
                self.login_url_var.set(settings.get('login_url', ''))
            if 'username' in settings:
                self.username_var.set(settings.get('username', ''))
            if 'password' in settings:
                self.password_var.set(settings.get('password', ''))
            if 'username_selector' in settings:
                self.username_selector_var.set(settings.get('username_selector', ''))
            if 'password_selector' in settings:
                self.password_selector_var.set(settings.get('password_selector', ''))
            if 'submit_selector' in settings:
                self.submit_selector_var.set(settings.get('submit_selector', ''))
            
            if show_message:
                messagebox.showinfo("成功", "設定を読み込みました。")
            self.log("設定を読み込みました")
        except Exception as e:
            if show_message:
                messagebox.showerror("エラー", f"設定の読み込みに失敗しました:\n{e}")
            # 起動時の自動読み込み時はエラーをログに記録しない
            
    def validate_inputs(self) -> bool:
        """入力値の検証"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("エラー", "URLを入力してください。")
            return False
            
        if not url.startswith(('http://', 'https://')):
            messagebox.showerror("エラー", "URLは http:// または https:// で始まる必要があります。")
            return False
            
        try:
            wait_time = int(self.wait_time_var.get())
            if wait_time < 1:
                raise ValueError("待機時間は1秒以上である必要があります。")
        except ValueError as e:
            messagebox.showerror("エラー", f"待機時間の値が不正です: {e}")
            return False
            
        return True
        
    def start_scraping(self):
        """スクレイピングを開始"""
        if self.is_running:
            messagebox.showwarning("警告", "既に実行中です。")
            return
            
        if not self.validate_inputs():
            return
            
        # UIを無効化
        self.is_running = True
        self.execute_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.progress['value'] = 0
        self.progress_label.config(text="処理を開始しています...")
        self.element_count_label.config(text="")
        self.current_element_count = 0
        
        # 別スレッドで実行
        thread = threading.Thread(target=self._run_scraping, daemon=True)
        thread.start()
        
    def stop_scraping(self):
        """スクレイピングを停止"""
        if not self.is_running:
            return
            
        self.is_running = False
        self.log("\nユーザーによって停止が要求されました...")
        # 実際の停止処理は、スレッド側で処理される
        
    def _run_scraping(self):
        """スクレイピングを実行（別スレッド）"""
        url = self.url_var.get().strip()
        output_path = self.output_var.get().strip()
        headless = self.headless_var.get()
        
        try:
            wait_time = int(self.wait_time_var.get())
        except ValueError:
            wait_time = 10
            
        scribe = None
        
        try:
            self.log("=" * 50)
            self.log("WebScribe - Webページ要素取得ツール")
            self.log("=" * 50)
            self.log(f"\nURL: {url}")
            self.log(f"出力ファイル: {output_path}")
            self.log(f"ヘッドレスモード: {'有効' if headless else '無効'}")
            self.log(f"待機時間: {wait_time}秒")
            self.log("\n処理を開始します...\n")
            
            # 標準出力をキャプチャするためのストリーム
            class LogStream:
                def __init__(self, log_func):
                    self.log_func = log_func
                    self.buffer = ""
                    
                def write(self, text):
                    self.buffer += text
                    # 改行が来たらログに出力
                    while '\n' in self.buffer:
                        line, self.buffer = self.buffer.split('\n', 1)
                        if line.strip():
                            self.log_func(line)
                        
                def flush(self):
                    if self.buffer.strip():
                        self.log_func(self.buffer.rstrip())
                        self.buffer = ""
            
            log_stream = LogStream(self.log)
            
            # 進捗コールバック関数を定義
            def progress_callback(current, total, message):
                self.root.after(0, lambda: self.update_progress(current, total, message))
            
            # WebScribeのインスタンスを作成
            self.log("ChromeDriverを初期化中...")
            with redirect_stdout(log_stream), redirect_stderr(log_stream):
                scribe = WebScribe(headless=headless, wait_time=wait_time, progress_callback=progress_callback)
            log_stream.flush()
            
            if not self.is_running:
                if scribe:
                    scribe.close()
                return
                
            # ログイン情報を準備
            login_info = None
            if self.need_login_var.get():
                login_url = self.login_url_var.get().strip()
                username = self.username_var.get().strip()
                password = self.password_var.get().strip()
                
                if login_url and username and password:
                    login_info = {
                        'login_url': login_url,
                        'username': username,
                        'password': password,
                    }
                    
                    # セレクタが指定されている場合は追加
                    username_selector = self.username_selector_var.get().strip()
                    password_selector = self.password_selector_var.get().strip()
                    submit_selector = self.submit_selector_var.get().strip()
                    
                    if username_selector:
                        login_info['username_selector'] = username_selector
                    if password_selector:
                        login_info['password_selector'] = password_selector
                    if submit_selector:
                        login_info['submit_selector'] = submit_selector
                    
                    self.log(f"ログイン情報が設定されています")
                    self.log(f"ログインURL: {login_url}")
                else:
                    self.log("警告: ログインが必要とマークされていますが、必要な情報が不足しています")
            
            # ページをスクレイピング
            self.log(f"ページにアクセス中: {url}")
            with redirect_stdout(log_stream), redirect_stderr(log_stream):
                data = scribe.scrape_page(url, login_info=login_info, max_elements=self.max_elements)
            log_stream.flush()
            
            if not self.is_running:
                if scribe:
                    scribe.close()
                return
                
            # 結果を表示
            self.log(f"ページタイトル: {data['page_info']['title']}")
            
            # ファイルに保存
            self.log(f"データを保存中: {output_path}")
            with redirect_stdout(log_stream), redirect_stderr(log_stream):
                scribe.save_to_json(data, output_path)
            log_stream.flush()
            
            if not self.is_running:
                return
                
            # 完了メッセージ
            self.log("\n" + "=" * 50)
            self.log("完了しました！")
            self.log(f"出力ファイル: {output_path}")
            self.log("=" * 50)
            
            # 成功ダイアログ
            self.root.after(0, lambda: messagebox.showinfo(
                "完了",
                f"スクレイピングが完了しました。\n\n"
                f"出力ファイル: {output_path}\n"
                f"取得要素数: {data['total_elements']}個"
            ))
            
        except KeyboardInterrupt:
            self.log("\n中断されました")
            self.root.after(0, lambda: messagebox.showwarning("中断", "処理が中断されました。"))
            
        except Exception as e:
            error_msg = f"エラーが発生しました: {str(e)}"
            self.log(f"\n{error_msg}")
            import traceback
            self.log(traceback.format_exc())
            self.root.after(0, lambda: messagebox.showerror("エラー", error_msg))
            
        finally:
            # クリーンアップ
            if scribe:
                try:
                    scribe.close()
                except:
                    pass
                    
            # UIを有効化
            self.root.after(0, self._scraping_finished)
            
    def _scraping_finished(self):
        """スクレイピング終了時の処理"""
        self.is_running = False
        self.execute_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.progress['value'] = 100
        if self.max_elements > 0:
            self.progress_label.config(text="完了")
            self.element_count_label.config(text=f"{self.current_element_count} / {self.max_elements} 要素")
        else:
            self.progress_label.config(text="完了")
            self.element_count_label.config(text="")


def main():
    """メイン関数"""
    root = Tk()
    app = WebScribeGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()

