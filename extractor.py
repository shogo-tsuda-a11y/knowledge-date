import os
import pandas as pd
import pdfplumber
import google.generativeai as genai
from dotenv import load_dotenv

# 環境変数の読み込み (.envファイルからAPIキーなどを取得)
load_dotenv()

# Gemini APIのセットアップ
# APIキーは環境変数 'GEMINI_API_KEY' に設定されていることを前提とします
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# 使用するモデルを指定
model = genai.GenerativeModel('gemini-2.5-flash')

UPLOAD_DIR = "uploaded_files"

def save_uploaded_file(uploaded_file):
    """アップロードされたファイルをローカルディレクトリに保存する"""
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
    
    file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def list_uploaded_files():
    """保存されているファイルの一覧を返す"""
    if not os.path.exists(UPLOAD_DIR):
        return []
    return [f for f in os.listdir(UPLOAD_DIR) if os.path.isfile(os.path.join(UPLOAD_DIR, f))]

def delete_uploaded_file(file_name):
    """指定されたファイルを削除する"""
    file_path = os.path.join(UPLOAD_DIR, file_name)
    if os.path.exists(file_path):
        os.remove(file_path)

def get_all_context_text():
    """保存されているすべてのファイルからテキストを抽出して結合する"""
    files = list_uploaded_files()
    all_text = ""
    for file_name in files:
        file_path = os.path.join(UPLOAD_DIR, file_name)
        if file_name.endswith(".csv"):
            all_text += f"\n[{file_name}]\n" + extract_text_from_csv(file_path)
        elif file_name.endswith(".pdf"):
            all_text += f"\n[{file_name}]\n" + extract_text_from_pdf(file_path)
    return all_text

def extract_text_from_csv(file_path):
    """CSVファイルからテキストを読み込む（例として全テキストを結合）"""
    try:
        df = pd.read_csv(file_path)
        # すべての列と行のデータを結合して1つのテキストにする
        text_data = df.to_string(index=False)
        return text_data
    except Exception as e:
        print(f"CSVファイルの読み込みエラー: {e}")
        return ""

def extract_text_from_pdf(file_path):
    """PDFファイルからテキストを抽出する"""
    text_data = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_data += page_text + "\n"
        return text_data
    except Exception as e:
        print(f"PDFファイルの読み込みエラー: {e}")
        return ""

def generate_faq_pairs(text_data):
    """抽出したテキストから、Gemini APIを使ってFAQペアを生成する"""
    if not text_data.strip():
        return "入力テキストが空です。"

    prompt = f"""
    以下のテキストは、過去の問い合わせデータやマニュアルなどの非構造化データです。
    このテキストを分析し、ユーザーが疑問に思いそうな「よくある質問(FAQ)」とその「回答」のペアをできるだけ多く抽出・生成してください。
    出力は必ず以下のCSV形式（ヘッダー付き）にしてください。

    Question,Answer
    質問1,回答1
    質問2,回答2
    ...

    【対象テキスト】
    {text_data}
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini APIの実行エラー: {e}")
        return ""

def main():
    # 対象ファイル（例）
    csv_file = "sample_data.csv"
    pdf_file = "sample_manual.pdf"
    output_file = "extracted_faq.csv"

    all_extracted_text = ""

    print("データの読み込みを開始します...")
    
    if os.path.exists(csv_file):
        print(f"{csv_file} を処理中...")
        csv_text = extract_text_from_csv(csv_file)
        all_extracted_text += "\n[CSVデータ]\n" + csv_text
    
    if os.path.exists(pdf_file):
        print(f"{pdf_file} を処理中...")
        pdf_text = extract_text_from_pdf(pdf_file)
        all_extracted_text += "\n[PDFデータ]\n" + pdf_text

    if not all_extracted_text:
        print("処理対象のテキストデータが見つかりませんでした。")
        return

    print("Gemini APIを使用してFAQを抽出中...")
    faq_csv_format = generate_faq_pairs(all_extracted_text)

    # Markdownのコードブロック表現（```csv ... ```）が含まれる場合があるため除去
    faq_csv_format = faq_csv_format.replace("```csv", "").replace("```", "").strip()

    print("抽出結果をファイルに保存します...")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(faq_csv_format)

    print(f"完了しました。抽出結果は {output_file} に保存されました。")

if __name__ == "__main__":
    main()
