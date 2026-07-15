import { useEffect, useRef, useState } from 'react';
import { api, streamChat } from '../api';
import type { ChatMessage, Citation } from '../types';

const prompts = ['最近工作上的选择让我犹豫', '我该如何面对一段关系的变化', '总是焦虑，怎样把心安定下来'];

export function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState('');
  const [answer, setAnswer] = useState('');
  const [citation, setCitation] = useState<Citation | null>(null);
  const [streaming, setStreaming] = useState(false);
  const cancelRef = useRef<(() => void) | null>(null);

  useEffect(() => { void api.chatHistory().then(setMessages).catch(() => undefined); return () => cancelRef.current?.(); }, []);

  const send = (value = text) => {
    const content = value.trim();
    if (!content || streaming) return;
    setText(''); setAnswer(''); setCitation(null); setStreaming(true);
    setMessages((items) => [...items, { id: `local-${Date.now()}`, role: 'user', text: content, citation: null, createdAt: new Date().toISOString() }]);
    cancelRef.current = streamChat({ text: content }, (event) => {
      if (event.type === 'delta') setAnswer((current) => current + event.text);
      if (event.type === 'citation') setCitation(event.citation);
      if (event.type === 'done' || event.type === 'error') {
        if (event.type === 'error') setAnswer((current) => current || event.message);
        setStreaming(false);
      }
    });
  };

  const visible = messages.slice(-8);
  return (
    <div className="inner-page consultation-page">
      <div className="consultation-shell">
        <aside className="chat-history">
          <div><span className="mini-seal">问</span><p>问天殿</p><small>一念起，万象生</small></div>
          <button className="new-chat" onClick={() => { setMessages([]); setAnswer(''); }}>＋　新问一卦</button>
          <p className="aside-label">近日问卦</p>
          {visible.filter((item) => item.role === 'user').map((item) => <button key={item.id} className="history-item"><i />{item.text}</button>)}
          {visible.length === 0 ? <p className="aside-empty">还没有问卦记录</p> : null}
          <p className="chat-disclaimer">解读用于传统文化娱乐与自我观察，不构成现实决策建议。</p>
        </aside>

        <section className="chat-scroll">
          <header className="chat-title"><div><span>与天机对谈</span><small>AI CONSULTATION · 古籍旁证</small></div><i className={streaming ? 'is-live' : ''}>{streaming ? '推演中' : '静候一问'}</i></header>
          <div className="conversation">
            {visible.length === 0 ? (
              <div className="chat-welcome"><span className="oracle-mark">卦</span><p className="eyebrow dark">先说困惑，不必先找答案</p><h1>此刻，什么事情<br />最牵动你的心？</h1><p>把事情的来龙去脉说清楚。天机会从古籍中寻找可供参照的文字，但最终的选择仍在你手中。</p><div className="prompt-list">{prompts.map((prompt) => <button key={prompt} onClick={() => send(prompt)}>{prompt}<span>↗</span></button>)}</div></div>
            ) : (
              <div className="message-list">
                {visible.map((message) => <article key={message.id} className={`message ${message.role}`}><small>{message.role === 'user' ? '你问' : '天机答'}</small><p>{message.text}</p></article>)}
                {answer ? <article className="message assistant"><small>天机答</small><p>{answer}{streaming ? <span className="cursor" /> : null}</p></article> : null}
              </div>
            )}
          </div>
          <div className="chat-composer"><textarea value={text} onChange={(event) => setText(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="把此刻的困惑写下来…" rows={2} /><button onClick={() => send()} disabled={!text.trim() || streaming}>问</button><small>Enter 发送 · Shift + Enter 换行</small></div>
        </section>

        <aside className="citation-panel">
          <p className="aside-label">古籍旁证</p>
          {citation ? <div className="citation-card"><span>{citation.book.slice(0, 1)}</span><small>{citation.book}</small><h3>{citation.chapter}</h3><blockquote>{citation.text}</blockquote><p>{citation.plain}</p><em>文本来源可追溯</em></div> : <div className="citation-empty"><div className="book-lines" /><b>有据可考</b><p>天机回答时，相关古籍原文会在这里展开。</p></div>}
          <div className="citation-principle"><b>这里如何回答</b><p>先理解你的处境，再检索古籍原文，最后给出不夸大、不宿命的解释。</p></div>
        </aside>
      </div>
    </div>
  );
}
