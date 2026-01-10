
import React, { useState, useRef } from 'react';
import { Mic, MicOff } from 'lucide-react';
import TopicMapEditor from '@/components/TopicMapEditor';

const DiscussionViewSimplified: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const [analysisData, setAnalysisData] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const recognitionRef = useRef<any>(null);

  const handleSend = () => {
    if (inputText.trim()) {
      setMessages(prev => {
        const newMessages = [...prev, { speaker: '自分', text: inputText }];
        return newMessages;
      });
      setInputText('');
    }
  };
  // messagesが更新されたら自動で解析
  React.useEffect(() => {
    if (messages.length === 0) return;
    handleAnalyze(messages);
  }, [messages]);

  // 音声認識開始/停止
  const handleMicClick = () => {
    if (isRecording) {
      recognitionRef.current?.stop();
      setIsRecording(false);
      return;
    }
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('音声認識APIが利用できません');
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'ja-JP';
    recognition.onresult = (event: any) => {
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      setInputText(prev => prev + transcript);
      // transcriptを即座に送信
      setTimeout(() => {
        if ((inputText + transcript).trim()) {
          setMessages(prev => [...prev, { speaker: '自分', text: inputText + transcript }]);
          setInputText('');
        }
      }, 100);
    };
    recognition.onend = () => {
      setIsRecording(false);
      // 自動再開（連続認識）
      setTimeout(() => {
        if (!isRecording) handleMicClick();
      }, 300);
    };
    recognitionRef.current = recognition;
    recognition.start();
    setIsRecording(true);
  };

  const handleAnalyze = (customMessages?: any[]) => {
    // ダミー解析結果: 全発言をトピックノードとして反映
    const msgs = customMessages || messages;
    console.log('解析対象messages:', msgs);
    const dummy = {
      base_analysis: { Q: msgs.length, M: 0.5, T: 0.3 },
      topic_map: {
        nodes: msgs.map((m, idx) => ({ id: String(idx + 1), label: m.text })),
        edges: msgs.length > 1 ? Array.from({ length: msgs.length - 1 }, (_, i) => ({ from: String(i + 1), to: String(i + 2) })) : [],
        clusters: []
      },
      intervention: { message: '議論の停滞が検出されました。' },
      participant_states: msgs.map((m: any) => ({ speaker: m.speaker, text: m.text }))
    };
    setAnalysisData(dummy);
  };


  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <div className="max-w-6xl mx-auto flex gap-10">
        {/* 会話ログ（左） */}
        <div className="w-1/3 bg-white rounded-xl shadow p-6 flex flex-col">
          <h2 className="font-bold mb-4 text-lg">会話ログ</h2>
          <div className="flex-1 h-80 overflow-y-auto border rounded p-3 mb-4 bg-gray-50">
            {messages.length === 0 ? (
              <div className="text-gray-400 text-center">発言はまだありません</div>
            ) : (
              messages.map((msg, idx) => (
                <div key={idx} className="mb-2">
                  <span className="font-semibold mr-2">{msg.speaker}:</span>
                  <span>{msg.text}</span>
                </div>
              ))
            )}
          </div>
          <div className="flex gap-2 items-center">
            <input
              type="text"
              className="flex-1 border rounded px-3 py-2"
              value={inputText}
              onChange={e => setInputText(e.target.value)}
              placeholder="発言を入力..."
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  handleSend();
                }
              }}
            />
            <button
              className={`px-3 py-2 rounded ${isRecording ? 'bg-red-500' : 'bg-blue-500'} text-white flex items-center`}
              onClick={handleMicClick}
              title={isRecording ? '録音停止' : '音声入力'}
            >
              {isRecording ? <MicOff size={20} /> : <Mic size={20} />}
            </button>
            <button
              className="px-4 py-2 rounded bg-green-500 text-white"
              onClick={handleSend}
            >送信</button>
          </div>
        </div>

        {/* トピックマップ（中央） */}
        <div className="flex-1 bg-white rounded-xl shadow p-6 flex flex-col">
          <h2 className="font-bold mb-4 text-lg">トピックマップ</h2>
          <div className="border rounded-lg bg-gray-50 p-4 min-h-[200px] mb-6">
            {analysisData && analysisData.topic_map ? (
              <TopicMapEditor mapData={analysisData.topic_map} />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center">
                  <p className="text-sm">トピックマップはまだ生成されていません</p>
                  <p className="text-xs mt-1">「解析を実行」をクリックしてください</p>
                </div>
              </div>
            )}
          </div>

          {/* 解析ボタン（音声入力なし解析用） */}
          <div className="mb-4 text-center">
            <button
              className="px-6 py-2 rounded bg-indigo-600 text-white font-bold shadow"
              onClick={() => handleAnalyze()}
            >音声入力なしで解析</button>
          </div>

          {/* 解析結果（以前のようなカード形式で表示） */}
          {analysisData && (
            <div className="mt-2 bg-white rounded-xl shadow p-8 border-2 border-indigo-400">
              <h3 className="text-2xl font-extrabold mb-6 text-indigo-700 text-center">解析結果</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {analysisData.base_analysis && (
                  <div className="bg-blue-50 border-2 border-blue-400 p-6 rounded-xl flex flex-col items-center">
                    <h4 className="font-bold text-lg mb-4 text-blue-800">基本分析指標</h4>
                    <div className="flex flex-col gap-3 items-center">
                      <div className="text-base text-gray-700">発言数 (Q)</div>
                      <div className="text-3xl font-extrabold text-blue-700">{analysisData.base_analysis.Q || 0}</div>
                      <div className="text-base text-gray-700 mt-4">多様性 (M)</div>
                      <div className="text-3xl font-extrabold text-blue-700">{analysisData.base_analysis.M || 0}</div>
                      <div className="text-base text-gray-700 mt-4">転換度 (T)</div>
                      <div className="text-3xl font-extrabold text-blue-700">{analysisData.base_analysis.T || 0}</div>
                    </div>
                  </div>
                )}
                {analysisData.intervention && (
                  <div className="bg-yellow-50 border-2 border-yellow-400 p-6 rounded-xl flex flex-col items-center">
                    <h4 className="font-bold text-lg text-yellow-800 mb-4">介入提案</h4>
                    <p className="text-xl font-semibold text-yellow-700">{analysisData.intervention.message}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>

  );
}

export default DiscussionViewSimplified;
