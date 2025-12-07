"""
WebScribe GUI - ダイアログでURLを指定してWeb要素を取得するGUIアプリケーション
"""
import sys
import json
import threading
import io
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Dict, Any
from tkinter import (
    Tk, Label, Entry, Button, Checkbutton, BooleanVar,
    StringVar, Text, Scrollbar, messagebox, filedialog,
    ttk, Frame
)
from tkinter.scrolledtext import ScrolledText
from tkinter.ttk import Combobox, Treeview

from webscribe import WebScribe


class WebScribeGUI:
    """WebScribeのGUIアプリケーション"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("WebScribe - Webページ要素取得ツール")
        self.root.geometry("1200x700")
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
        
        # 設定ファイルのパス（複数設定対応）
        self.settings_dir = Path(__file__).parent / "settings"
        self.settings_dir.mkdir(exist_ok=True)
        self.settings_file = self.settings_dir / "webscribe_settings.json"
        self.current_settings_profile = None
        
        # 取得した要素データ
        self.current_elements_data = None
        
        self._create_widgets()
        
        # 保存された設定リストを読み込み
        self.load_settings_list()
        
    def _create_widgets(self):
        """ウィジェットを作成"""
        # ttkウィジェットのスタイルを設定
        style = ttk.Style()
        style.configure('Treeview', font=('Consolas', 9))
        # メインフレーム
        main_frame = Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill='both', expand=True)
        
        # URL入力セクション
        url_frame = Frame(main_frame)
        url_frame.pack(fill='x', pady=(0, 10))
        
        url_label_frame = Frame(url_frame)
        url_label_frame.pack(fill='x', pady=(0, 5))
        
        Label(url_label_frame, text="URL:", font=('Arial', 10, 'bold')).pack(side='left')
        
        # 保存された設定を選択するCombobox
        settings_select_frame = Frame(url_label_frame)
        settings_select_frame.pack(side='right')
        
        Label(settings_select_frame, text="保存された設定:", font=('Arial', 9)).pack(side='left', padx=(10, 5))
        self.settings_combo = Combobox(
            settings_select_frame,
            width=25,
            state='readonly',
            font=('Arial', 9)
        )
        self.settings_combo.pack(side='left')
        self.settings_combo.bind('<<ComboboxSelected>>', self.on_settings_selected)
        
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
            text="選択した設定を読み込み",
            command=self.load_selected_settings,
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
        
        # ログと要素表示エリア（左右分割）
        bottom_frame = Frame(main_frame)
        bottom_frame.pack(fill='both', expand=True)
        
        # 左側: ログ表示エリア
        log_container = Frame(bottom_frame)
        log_container.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        log_label_frame = Frame(log_container)
        log_label_frame.pack(fill='x', pady=(0, 5))
        
        Label(log_label_frame, text="ログ:", font=('Arial', 10, 'bold')).pack(side='left')
        
        clear_log_button = Button(
            log_label_frame,
            text="クリア",
            command=self.clear_log,
            font=('Arial', 8),
            width=8
        )
        clear_log_button.pack(side='right')
        
        # ログテキストエリア（スクロール可能）
        self.log_text = ScrolledText(
            log_container,
            wrap='word',
            font=('Consolas', 9),
            bg='#f5f5f5',
            state='disabled'
        )
        self.log_text.pack(fill='both', expand=True)
        
        # 右側: 取得した要素表示エリア
        elements_container = Frame(bottom_frame)
        elements_container.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        elements_label_frame = Frame(elements_container)
        elements_label_frame.pack(fill='x', pady=(0, 5))
        
        Label(elements_label_frame, text="取得した要素:", font=('Arial', 10, 'bold')).pack(side='left')
        
        elements_button_frame = Frame(elements_label_frame)
        elements_button_frame.pack(side='right')
        
        open_json_button = Button(
            elements_button_frame,
            text="JSONファイルを開く",
            command=self.open_json_file,
            font=('Arial', 8),
            width=12
        )
        open_json_button.pack(side='right', padx=(0, 5))
        
        clear_elements_button = Button(
            elements_button_frame,
            text="クリア",
            command=self.clear_elements,
            font=('Arial', 8),
            width=8
        )
        clear_elements_button.pack(side='right')
        
        # 要素表示用のTreeview
        elements_tree_frame = Frame(elements_container)
        elements_tree_frame.pack(fill='both', expand=True)
        
        # スクロールバー
        elements_scrollbar_y = Scrollbar(elements_tree_frame, orient='vertical')
        elements_scrollbar_y.pack(side='right', fill='y')
        
        elements_scrollbar_x = Scrollbar(elements_tree_frame, orient='horizontal')
        elements_scrollbar_x.pack(side='bottom', fill='x')
        
        # Treeview
        self.elements_tree = Treeview(
            elements_tree_frame,
            columns=('tag', 'text_preview', 'children'),
            show='tree headings',
            yscrollcommand=elements_scrollbar_y.set,
            xscrollcommand=elements_scrollbar_x.set
        )
        self.elements_tree.pack(side='left', fill='both', expand=True)
        
        elements_scrollbar_y.config(command=self.elements_tree.yview)
        elements_scrollbar_x.config(command=self.elements_tree.xview)
        
        # カラムの設定
        self.elements_tree.heading('#0', text='要素', anchor='w')
        self.elements_tree.heading('tag', text='タグ', anchor='w')
        self.elements_tree.heading('text_preview', text='テキスト（プレビュー）', anchor='w')
        self.elements_tree.heading('children', text='子要素数', anchor='w')
        
        self.elements_tree.column('#0', width=150)
        self.elements_tree.column('tag', width=100)
        self.elements_tree.column('text_preview', width=300)
        self.elements_tree.column('children', width=80)
        
        # 要素をクリックしたときの詳細表示
        self.elements_tree.bind('<Double-1>', self.on_element_selected)
        
        # 初期メッセージ
        self.log("WebScribe GUIを起動しました。")
        settings_files = list(self.settings_dir.glob("*.json"))
        if settings_files:
            self.log(f"{len(settings_files)}個の設定プロファイルが見つかりました。")
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
    
    def clear_elements(self):
        """要素表示をクリア"""
        for item in self.elements_tree.get_children():
            self.elements_tree.delete(item)
        self.current_elements_data = None
    
    def display_elements(self, elements_data: Dict[str, Any]):
        """取得した要素を表示
        
        Args:
            elements_data: scrape_page()で取得したデータ
        """
        try:
            self.current_elements_data = elements_data
            
            # 既存の要素をクリア
            self.clear_elements()
            
            if not elements_data:
                self.log("警告: 要素データが空です")
                return
            
            if 'elements' not in elements_data:
                self.log("警告: 要素データに'elements'キーがありません")
                return
            
            elements = elements_data.get('elements', [])
            page_info = elements_data.get('page_info', {})
            
            if not elements:
                self.log("警告: 要素が0個です")
                return
            
            # ページ情報をルートアイテムとして追加
            root_text = f"ページ: {page_info.get('title', 'Unknown')}"
            root_item = self.elements_tree.insert(
                '', 'end',
                text=root_text,
                values=('', f"URL: {page_info.get('url', '')}", f"合計: {len(elements)}要素"),
                open=True
            )
            
            # 要素を再帰的に追加
            for element in elements:
                try:
                    self._add_element_to_tree(root_item, element)
                except Exception as e:
                    self.log(f"要素の表示エラー: {e}")
                    continue
            
            self.log(f"取得した {len(elements)} 個の要素を表示しました")
        except Exception as e:
            self.log(f"要素表示のエラー: {e}")
            import traceback
            self.log(traceback.format_exc())
    
    def _add_element_to_tree(self, parent_item, element: Dict[str, Any], depth: int = 0):
        """要素をTreeviewに追加（再帰的）
        
        Args:
            parent_item: 親アイテム
            element: 要素データ
            depth: 現在の深度
        """
        try:
            if depth > 10:  # 深度制限
                return
            
            if not isinstance(element, dict):
                return
            
            tag_name = element.get('tag_name', '')
            text_content = element.get('text', '')
            if not isinstance(text_content, str):
                text_content = str(text_content) if text_content else ''
            text_preview = text_content[:50]  # 最初の50文字
            if len(text_content) > 50:
                text_preview += '...'
            children_count = element.get('children_count', 0)
            
            # アイテムテキスト（インデックスとタグ名）
            item_text = f"[{element.get('index', 0)}] {tag_name}"
            
            item = self.elements_tree.insert(
                parent_item,
                'end',
                text=item_text,
                values=(tag_name, text_preview, children_count),
                tags=(tag_name,)
            )
            
            # 子要素を追加
            children = element.get('children', [])
            if not isinstance(children, list):
                children = []
            
            for child in children:
                if isinstance(child, dict):
                    self._add_element_to_tree(item, child, depth + 1)
        except Exception as e:
            # エラーが発生しても処理を続行
            pass
    
    def on_element_selected(self, event):
        """要素が選択されたときの詳細表示"""
        selection = self.elements_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        item_text = self.elements_tree.item(item, 'text')
        
        # 詳細情報を表示（簡易版）
        messagebox.showinfo("要素情報", f"選択された要素: {item_text}")
    
    def open_json_file(self):
        """既存のJSONファイルを開いて要素を表示"""
        filename = filedialog.askopenfilename(
            title="JSONファイルを開く",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            return
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # JSONデータが正しい形式か確認
            if not isinstance(data, dict):
                messagebox.showerror("エラー", "JSONファイルの形式が正しくありません。")
                return
            
            if 'elements' not in data:
                messagebox.showerror("エラー", "このJSONファイルには要素データが含まれていません。")
                return
            
            # 要素を表示
            self.display_elements(data)
            self.log(f"JSONファイルを読み込みました: {filename}")
            
            # ページ情報をログに表示
            page_info = data.get('page_info', {})
            if page_info:
                self.log(f"  ページ: {page_info.get('title', 'Unknown')}")
                self.log(f"  URL: {page_info.get('url', 'Unknown')}")
                if 'timestamp' in page_info:
                    self.log(f"  取得日時: {page_info['timestamp']}")
            
        except json.JSONDecodeError as e:
            messagebox.showerror("エラー", f"JSONファイルの解析に失敗しました:\n{e}")
            self.log(f"JSONファイルの読み込みエラー: {e}")
        except Exception as e:
            messagebox.showerror("エラー", f"ファイルの読み込みに失敗しました:\n{e}")
            self.log(f"ファイル読み込みエラー: {e}")
        
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
        """現在の設定をファイルに保存（複数プロファイル対応）"""
        # プロファイル名を入力
        profile_name = messagebox.askstring(
            "設定を保存",
            "プロファイル名を入力してください:",
            initialvalue=self.url_var.get().replace('https://', '').replace('http://', '').split('/')[0][:30]
        )
        
        if not profile_name:
            return  # キャンセルされた場合
        
        profile_name = profile_name.strip()
        if not profile_name:
            messagebox.showerror("エラー", "プロファイル名を入力してください。")
            return
        
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
            
            # プロファイルファイル名（安全なファイル名に変換）
            safe_name = "".join(c for c in profile_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')
            profile_file = self.settings_dir / f"{safe_name}.json"
            
            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("成功", f"設定を保存しました。\nプロファイル: {profile_name}\nファイル: {profile_file}")
            self.log(f"設定を保存しました: {profile_name}")
            
            # 設定リストを更新
            self.load_settings_list()
        except Exception as e:
            messagebox.showerror("エラー", f"設定の保存に失敗しました:\n{e}")
            self.log(f"設定の保存エラー: {e}")
    
    def load_settings_list(self):
        """保存された設定ファイルのリストを取得してComboboxに設定"""
        try:
            profile_names = []
            
            # settings/ディレクトリ内のJSONファイルを読み込む
            settings_files = list(self.settings_dir.glob("*.json"))
            
            # ルートディレクトリのwebscribe_settings.jsonも読み込む（後方互換性のため）
            root_settings_file = Path(__file__).parent / "webscribe_settings.json"
            if root_settings_file.exists():
                settings_files.append(root_settings_file)
            
            for settings_file in sorted(settings_files):
                try:
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                    url = settings.get('url', '')
                    profile_name = settings_file.stem
                    if url:
                        profile_names.append(f"{profile_name} ({url})")
                    else:
                        profile_names.append(profile_name)
                except Exception as e:
                    self.log(f"設定ファイルの読み込みエラー ({settings_file}): {e}")
                    continue
            
            self.settings_combo['values'] = profile_names
            if profile_names:
                self.settings_combo.current(0)
        except Exception as e:
            self.log(f"設定リストの読み込みエラー: {e}")
    
    def on_settings_selected(self, event):
        """設定が選択されたときの処理（自動読み込み）"""
        selected = self.settings_combo.get()
        if not selected:
            return
        
        # プロファイル名を抽出（URL部分を除去）
        profile_name = selected.split(' (')[0]
        
        # まずsettings/ディレクトリ内を探す
        profile_file = self.settings_dir / f"{profile_name}.json"
        
        # 見つからない場合はルートディレクトリを探す
        if not profile_file.exists():
            profile_file = Path(__file__).parent / f"{profile_name}.json"
        
        if profile_file.exists():
            self.load_settings_from_file(profile_file, show_message=False)
    
    def load_settings_from_file(self, settings_file: Path, show_message: bool = False):
        """設定ファイルから読み込み
        
        Args:
            settings_file: 設定ファイルのパス
            show_message: メッセージを表示するかどうか
        """
        try:
            if not settings_file.exists():
                if show_message:
                    messagebox.showinfo("情報", "設定ファイルが見つかりません。")
                return
            
            with open(settings_file, 'r', encoding='utf-8') as f:
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
            self.log(f"設定を読み込みました: {settings_file.stem}")
        except Exception as e:
            if show_message:
                messagebox.showerror("エラー", f"設定の読み込みに失敗しました:\n{e}")
    
    def load_selected_settings(self):
        """Comboboxで選択された設定を読み込み"""
        selected = self.settings_combo.get()
        if not selected:
            messagebox.showwarning("警告", "設定を選択してください。")
            return
        
        # プロファイル名を抽出（URL部分を除去）
        profile_name = selected.split(' (')[0]
        profile_file = self.settings_dir / f"{profile_name}.json"
        
        if not profile_file.exists():
            messagebox.showerror("エラー", f"設定ファイルが見つかりません: {profile_file}")
            return
        
        self.load_settings_from_file(profile_file, show_message=True)
    
    def load_settings(self, show_message: bool = False):
        """保存された設定を読み込み（後方互換性のため）"""
        # 最初の設定ファイルがあれば読み込む
        settings_files = sorted(list(self.settings_dir.glob("*.json")))
        if settings_files:
            self.load_settings_from_file(settings_files[0], show_message)
            
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
            
            # 取得した要素を表示エリアに表示
            self.root.after(0, lambda: self.display_elements(data))
            
            # ファイルに保存
            self.log(f"データを保存中: {output_path}")
            with redirect_stdout(log_stream), redirect_stderr(log_stream):
                scribe.save_to_json(data, output_path)
            log_stream.flush()
            
            if not self.is_running:
                return
            
            # HTMLファイルも保存
            html_output_path = str(Path(output_path).with_suffix('.html'))
            self.log(f"HTMLデータを保存中: {html_output_path}")
            with redirect_stdout(log_stream), redirect_stderr(log_stream):
                scribe.save_to_html(data, html_output_path)
            log_stream.flush()
            
            if not self.is_running:
                return
                
            # 完了メッセージ
            self.log("\n" + "=" * 50)
            self.log("完了しました！")
            self.log(f"出力ファイル (JSON): {output_path}")
            self.log(f"出力ファイル (HTML): {html_output_path}")
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
    try:
        root = Tk()
        app = WebScribeGUI(root)
        # ウィンドウを前面に表示
        root.lift()
        root.attributes('-topmost', True)
        root.after_idle(root.attributes, '-topmost', False)
        root.focus_force()
        print("GUIウィンドウを起動しました...")
        root.mainloop()
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

