"""CLI版議論システム - Webブラウザ不要."""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from datetime import datetime
from typing import List, Dict, Any
import json

from app.services.analysis import AnalysisService
from app.config import settings


class CLIDiscussionSystem:
    """コマンドライン版議論システム."""

    def __init__(self):
        self.analysis_service = AnalysisService()
        self.messages: List[Dict[str, Any]] = []
        self.session_id = f"cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def add_message(self, speaker: str, text: str):
        """メッセージを追加."""
        msg = {
            "speaker": speaker,
            "text": text,
            "timestamp": datetime.now().isoformat()
        }
        self.messages.append(msg)
        print(f"\n[{speaker}] {text}")
        
    def analyze(self):
        """現在の会話を分析."""
        if len(self.messages) < 2:
            print("\n⚠️  分析には最低2つのメッセージが必要です")
            return
            
        print("\n🔍 分析中...")
        
        # セグメント分析
        utterances = [
            {
                "speaker": msg["speaker"],
                "text": msg["text"],
                "start": i * 10,
                "end": (i + 1) * 10,
            }
            for i, msg in enumerate(self.messages)
        ]
        
        result = self.analysis_service.analyze_segment(
            session_id=self.session_id,
            segment_id=1,
            start_sec=0,
            end_sec=len(self.messages) * 10,
            utterances=utterances,
        )
        
        # 結果表示
        print("\n" + "=" * 60)
        print("📊 分析結果")
        print("=" * 60)
        
        if hasattr(result, 'dict'):
            result = result.dict()
        elif hasattr(result, 'model_dump'):
            result = result.model_dump()
            
        # 主要メトリクス
        print(f"\n【メトリクス】")
        print(f"  質問数 (Q): {result.get('Q', 0)}")
        print(f"  回答数 (A): {result.get('A', 0)}")
        print(f"  反論数 (R): {result.get('R', 0)}")
        print(f"  支持数 (S): {result.get('S', 0)}")
        print(f"  その他 (X): {result.get('X', 0)}")
        
        print(f"\n【評価スコア】")
        print(f"  混乱度 (M): {result.get('M', 0):.2f}")
        print(f"  停滞度 (T): {result.get('T', 0):.2f}")
        print(f"  理解度 (L): {result.get('L', 0):.2f}")
        
        # イベント
        events = result.get('events', [])
        if events:
            print(f"\n【検出されたイベント】")
            for event in events[:5]:  # 最大5件
                print(f"  - {event.get('type', 'N/A')}: {event.get('text', '')[:50]}...")
                
        print("\n" + "=" * 60)
        
    def save_transcript(self, filename: str = None):
        """議事録を保存."""
        if not filename:
            filename = f"議事録_{self.session_id}.txt"
            
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"議事録 - {self.session_id}\n")
            f.write(f"作成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            
            for msg in self.messages:
                time = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M:%S')
                f.write(f"[{time}] {msg['speaker']}: {msg['text']}\n")
                
        print(f"\n💾 議事録を保存しました: {filename}")
        
    def interactive_mode(self):
        """対話モード."""
        print("\n" + "=" * 60)
        print("🎤 CLI議論システム")
        print("=" * 60)
        print("\nコマンド:")
        print("  話者名: テキスト  - メッセージを追加")
        print("  /analyze         - 分析を実行")
        print("  /save [filename] - 議事録を保存")
        print("  /quit            - 終了")
        print("=" * 60 + "\n")
        
        while True:
            try:
                user_input = input("> ").strip()
                
                if not user_input:
                    continue
                    
                if user_input == "/quit":
                    print("\n👋 終了します")
                    break
                    
                elif user_input == "/analyze":
                    self.analyze()
                    
                elif user_input.startswith("/save"):
                    parts = user_input.split(maxsplit=1)
                    filename = parts[1] if len(parts) > 1 else None
                    self.save_transcript(filename)
                    
                elif ":" in user_input:
                    # メッセージ追加
                    speaker, text = user_input.split(":", 1)
                    self.add_message(speaker.strip(), text.strip())
                    
                else:
                    print("⚠️  フォーマット: 話者名: テキスト")
                    
            except KeyboardInterrupt:
                print("\n\n👋 終了します")
                break
            except Exception as e:
                print(f"❌ エラー: {e}")


def main():
    """メイン関数."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CLI議論システム")
    parser.add_argument("--file", "-f", help="入力ファイル (各行: 話者名: テキスト)")
    parser.add_argument("--output", "-o", help="出力ファイル名")
    
    args = parser.parse_args()
    
    system = CLIDiscussionSystem()
    
    if args.file:
        # ファイルから読み込み
        print(f"📄 ファイルから読み込み: {args.file}")
        with open(args.file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and ":" in line:
                    speaker, text = line.split(":", 1)
                    system.add_message(speaker.strip(), text.strip())
                    
        system.analyze()
        
        if args.output:
            system.save_transcript(args.output)
    else:
        # 対話モード
        system.interactive_mode()


if __name__ == "__main__":
    main()
