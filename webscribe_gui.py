"""
WebScribe GUI - ダイアログでURLを指定してWeb要素を取得するGUIアプリケーション
"""
import sys
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
        
        self._create_widgets()
        
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
        
        # 進捗バー
        self.progress = ttk.Progressbar(
            main_frame,
            mode='indeterminate',
            length=400
        )
        self.progress.pack(fill='x', pady=(0, 10))
        
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
        self.log("URLを入力して「実行」ボタンをクリックしてください。\n")
        
    def _toggle_login_fields(self):
        """ログイン情報入力フィールドの表示/非表示を切り替え"""
        if self.need_login_var.get():
            self.login_details_frame.pack(fill='x', pady=(5, 0))
        else:
            self.login_details_frame.pack_forget()
        
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
        self.progress.start(10)
        
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
            
            # WebScribeのインスタンスを作成
            self.log("ChromeDriverを初期化中...")
            with redirect_stdout(log_stream), redirect_stderr(log_stream):
                scribe = WebScribe(headless=headless, wait_time=wait_time)
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
                data = scribe.scrape_page(url, login_info=login_info)
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
        self.progress.stop()


def main():
    """メイン関数"""
    root = Tk()
    app = WebScribeGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()

