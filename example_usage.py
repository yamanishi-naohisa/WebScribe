"""
WebScribeの使用例
"""
from webscribe import WebScribe


def example_basic():
    """基本的な使用例"""
    url = "https://example.com"
    output_file = "example_output.json"
    
    # WebScribeを使用
    scribe = WebScribe(headless=False)
    
    try:
        # ページをスクレイピング
        data = scribe.scrape_page(url)
        
        # JSONファイルに保存
        scribe.save_to_json(data, output_file)
        
        print(f"\n保存された要素の数: {data['total_elements']}")
        print(f"ページタイトル: {data['page_info']['title']}")
        
    finally:
        scribe.close()


def example_context_manager():
    """コンテキストマネージャーを使用した例"""
    url = "https://example.com"
    output_file = "example_output2.json"
    
    with WebScribe(headless=True) as scribe:
        data = scribe.scrape_page(url)
        scribe.save_to_json(data, output_file)
        
        # 保存されたデータの構造を確認
        print("\n=== ページ情報 ===")
        print(f"URL: {data['page_info']['url']}")
        print(f"タイトル: {data['page_info']['title']}")
        print(f"タイムスタンプ: {data['page_info']['timestamp']}")
        
        print("\n=== 最初の5つの要素 ===")
        for i, element in enumerate(data['elements'][:5], 1):
            print(f"\n要素 {i}:")
            print(f"  タグ名: {element['tag_name']}")
            print(f"  テキスト: {element['text'][:50]}..." if len(element['text']) > 50 else f"  テキスト: {element['text']}")
            print(f"  表示状態: {element['is_displayed']}")
            print(f"  子要素数: {element['children_count']}")


if __name__ == '__main__':
    print("=== 基本的な使用例 ===")
    example_basic()
    
    print("\n=== コンテキストマネージャーの使用例 ===")
    example_context_manager()

