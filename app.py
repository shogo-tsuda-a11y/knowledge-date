import streamlit as st
import pandas as pd
import pdfplumber
import google.generativeai as genai
import os
from dotenv import load_dotenv
import io
import extractor

# ページの基本設定
st.set_page_config(page_title="FAQ Extractor", page_icon="🤖", layout="wide", initial_sidebar_state="collapsed")

# --- 認証機能 ---
def check_password():
    """パスワードが正しいかチェックする"""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    # ログイン画面の表示
    st.title("🤖 FAQ Extractor ログイン")
    password = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
        if password == "gymdx_faq":  # 初期パスワード
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("パスワードが正しくありません")
    return False

if check_password():
    st.title("🤖 自動FAQ生成ツール")
    st.markdown("サポート履歴のCSVデータや、マニュアルのPDFファイルをアップロードして保存しておくと、Gemini APIが自動でFAQを抽出・生成します。")

    # サイドバー: 設定
    with st.sidebar:
        st.header("⚙️ 設定")
        load_dotenv()
        default_api_key = os.environ.get("GEMINI_API_KEY", "")
        api_key = st.text_input("Gemini API Key", value=default_api_key, type="password")
        model_name = st.selectbox(
            "使用するモデル",
            ("gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash")
        )
        st.markdown("---")
        if st.button("ログアウト"):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- ファイル管理セクション ---
    st.subheader("📁 アップロード済みのファイル")
    col_files, col_upload = st.columns([0.5, 0.5])

    with col_files:
        saved_files = extractor.list_uploaded_files()
        if saved_files:
            for f_name in saved_files:
                c1, c2 = st.columns([0.8, 0.2])
                c1.write(f"📄 {f_name}")
                if c2.button("削除", key=f"del_{f_name}"):
                    extractor.delete_uploaded_file(f_name)
                    st.rerun()
        else:
            st.info("保存されているファイルはありません。")

    with col_upload:
        new_files = st.file_uploader("新しいファイルを追加（自動保存）", type=["csv", "pdf"], accept_multiple_files=True)
        if new_files:
            for f in new_files:
                extractor.save_uploaded_file(f)
            st.success(f"{len(new_files)}個のファイルを保存しました。")
            st.rerun()

    st.markdown("---")

    # --- 実行セクション ---
    if st.button("🚀 保存済みファイルからFAQを生成する", type="primary"):
        all_extracted_text = extractor.get_all_context_text()
        
        if not all_extracted_text.strip():
            st.warning("処理対象のファイルがありません。ファイルをアップロードしてください。")
        else:
            with st.spinner("Gemini APIでFAQを生成しています..."):
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(model_name)
                
                prompt = f"""
                以下のテキストは、過去の問い合わせデータやマニュアルなどの非構造化データです。
                このテキストを分析し、ユーザーが疑問に思いそうな「よくある質問(FAQ)」とその「回答」のペアをできるだけ多く抽出・生成してください。
                出力は必ず以下のCSV形式（ヘッダー付き）にしてください。

                Question,Answer
                質問1,回答1
                質問2,回答2
                ...

                【対象テキスト】
                {all_extracted_text}
                """
                
                try:
                    response = model.generate_content(prompt)
                    faq_result = response.text
                    faq_result = faq_result.replace("```csv", "").replace("```", "").strip()
                    
                    st.success("FAQの生成が完了しました！")
                    st.subheader("生成されたFAQ (プレビュー)")
                    
                    try:
                        df_result = pd.read_csv(io.StringIO(faq_result))
                        edited_df = st.data_editor(df_result, use_container_width=True, num_rows="dynamic")
                        csv_data = edited_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 CSVをダウンロード",
                            data=csv_data,
                            file_name="extracted_faq.csv",
                            mime="text/csv"
                        )
                    except Exception as e:
                        st.text_area("生成結果", faq_result, height=300)
                        st.download_button(
                            label="📥 CSVをダウンロード",
                            data=faq_result.encode('utf-8'),
                            file_name="extracted_faq.csv",
                            mime="text/csv"
                        )
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
