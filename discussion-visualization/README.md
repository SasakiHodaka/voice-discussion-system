# 理解のずれ可視化サンプルの使い方

1. 必要なPythonパッケージをインストール
   ```
   pip install streamlit pandas
   ```

2. 議事録テキストから理解のずれを抽出
   ```
   python misalignment_extractor.py
   ```
   → misalignment_result.json が生成されます

3. Streamlitで可視化
   ```
   streamlit run visualize_misalignment.py
   ```
   → ブラウザでグラフ＆リスト表示

---

- sample_transcript.txt を編集すれば自分の議事録でも試せます
- misalignment_extractor.py のキーワードやロジックも自由に拡張可能
- さらに高度なUIや分析もご要望に応じて追加できます
