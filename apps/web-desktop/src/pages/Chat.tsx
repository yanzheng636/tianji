import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api, streamChat } from '../api';
import type { ChatMessage, ChatSession, Citation } from '../types';

const prompts = ['最近工作上的选择让我犹豫', '我该如何面对一段关系的变化', '总是焦虑，怎样把心安定下来'];

const lastCitation = (items: ChatMessage[]): Citation | null => {
  for (let i = items.length - 1; i >= 0; i -= 1) {
    if (items[i].role === 'assistant' && items[i].citation) return items[i].citation;
  }
  return null;
};

export function Chat() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState(() => searchParams.get('prompt') ?? '');
  const [answer, setAnswer] = useState('');
  const [citation, setCitation] = useState<Citation | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [pendingQian, setPendingQian] = useState<string | null>(null);
  const cancelRef = useRef<(() => void) | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    void (async () => {
      const qianId = searchParams.get('qian');
      if (qianId) {
        // 从签室「带此签去问卦」而来：开一条新会话，把签面挂到首轮发送。
        const session = await api.createChatSession().catch(() => null);
        const list = await api.chatSessions().catch(() => [] as ChatSession[]);
        setSessions(list);
        setActiveId(session?.id ?? list[0]?.id ?? null);
        setMessages([]); setCitation(null); setPendingQian(qianId);
        setText((current) => current || '帮我解这支签');
        return;
      }
      const list = await api.chatSessions().catch(() => [] as ChatSession[]);
      setSessions(list);
      if (list.length) {
        setActiveId(list[0].id);
        const msgs = await api.sessionMessages(list[0].id).catch(() => [] as ChatMessage[]);
        setMessages(msgs);
        setCitation(lastCitation(msgs));
      }
    })();
    return () => cancelRef.current?.();
  }, []);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, answer]);

  const refreshSessions = () => { void api.chatSessions().then(setSessions).catch(() => undefined); };

  const openSession = async (id: string) => {
    if (streaming || id === activeId) return;
    setActiveId(id); setAnswer(''); setCitation(null); setPendingQian(null);
    const msgs = await api.sessionMessages(id).catch(() => [] as ChatMessage[]);
    setMessages(msgs);
    setCitation(lastCitation(msgs));
  };

  const newChat = async () => {
    if (streaming) return;
    const session = await api.createChatSession().catch(() => null);
    setMessages([]); setAnswer(''); setCitation(null); setText(''); setPendingQian(null);
    if (session) { setActiveId(session.id); setSessions((items) => [session, ...items.filter((s) => s.id !== session.id)]); }
    else setActiveId(null);
  };

  const removeSession = async (event: React.MouseEvent, id: string) => {
    event.stopPropagation();
    if (streaming) return;
    await api.deleteChatSession(id).catch(() => undefined);
    const rest = sessions.filter((s) => s.id !== id);
    setSessions(rest);
    if (id === activeId) {
      if (rest.length) void openSession(rest[0].id);
      else { setActiveId(null); setMessages([]); setAnswer(''); setCitation(null); }
    }
  };

  const send = (value = text) => {
    const content = value.trim();
    if (!content || streaming) return;
    const qianId = pendingQian ?? undefined;
    setText(''); setAnswer(''); setCitation(null); setStreaming(true); setPendingQian(null);
    setMessages((items) => [...items, { id: `local-${Date.now()}`, role: 'user', text: content, citation: null, createdAt: new Date().toISOString() }]);
    let acc = '';
    let cit: Citation | null = null;
    cancelRef.current = streamChat({ text: content, sessionId: activeId, qianId }, (event) => {
      if (event.type === 'session') setActiveId((current) => current ?? event.sessionId);
      if (event.type === 'delta') { acc += event.text; setAnswer(acc); }
      if (event.type === 'citation') { cit = event.citation; setCitation(event.citation); }
      if (event.type === 'done' || event.type === 'error') {
        if (event.type === 'error') { setAnswer((current) => current || event.message); }
        else {
          const id = event.messageId;
          setMessages((items) => [...items, { id, role: 'assistant', text: acc, citation: cit, createdAt: new Date().toISOString() }]);
          setAnswer('');
          if (event.sessionId) setActiveId((current) => current ?? event.sessionId);
        }
        setStreaming(false);
        refreshSessions();
      }
    });
  };

  return (
    <div className="inner-page consultation-page">
      <div className="consultation-shell">
        <aside className="chat-history">
          <div><span className="mini-seal">问</span><p>问室</p><small>把事情慢慢说清</small></div>
          <button className="new-chat" onClick={() => navigate('/qian')}>＋　新问一卦</button>
          <button className="new-chat-plain" onClick={() => void newChat()}>不抽卦，直接问山问 →</button>
          <p className="aside-label">近日问卦</p>
          {sessions.map((item) => (
            <button key={item.id} className={`history-item${item.id === activeId ? ' active' : ''}`} onClick={() => void openSession(item.id)}>
              <i />{item.title}
              <span className="history-remove" role="button" aria-label="删除会话" onClick={(event) => void removeSession(event, item.id)}>×</span>
            </button>
          ))}
          {sessions.length === 0 ? <p className="aside-empty">还没有问卦记录</p> : null}
          <p className="chat-disclaimer">解读用于传统文化娱乐与自我观察，不构成现实决策建议。</p>
        </aside>

        <section className="chat-scroll">
          <header className="chat-title"><div><span>与山问对谈</span><small>古籍旁证 · 可追溯引用</small></div><i className={streaming ? 'is-live' : ''}>{streaming ? '正在检索' : '静候一问'}</i></header>
          <div className="conversation">
            {messages.length === 0 && !answer ? (
              <div className="chat-welcome"><span className="oracle-mark">卦</span><p className="eyebrow dark">先说困惑，不必先找答案</p><h1>此刻，什么事情<br />最牵动你的心？</h1><p>把事情的来龙去脉说清楚。山问会从古籍中寻找可供参照的文字，但最终的选择仍在你手中。</p><div className="prompt-list">{prompts.map((prompt) => <button key={prompt} onClick={() => send(prompt)}>{prompt}<span>↗</span></button>)}</div></div>
            ) : (
              <div className="message-list">
                {messages.map((message) => <article key={message.id} className={`message ${message.role}`}><small>{message.role === 'user' ? '你问' : '山问答'}</small><p>{message.text}</p></article>)}
                {answer ? <article className="message assistant"><small>山问答</small><p>{answer}{streaming ? <span className="cursor" /> : null}</p></article> : null}
                <div ref={bottomRef} />
              </div>
            )}
          </div>
          <div className="chat-composer"><textarea value={text} onChange={(event) => setText(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="把此刻的困惑写下来…" rows={2} /><button onClick={() => send()} disabled={!text.trim() || streaming}>问</button><small>Enter 发送 · Shift + Enter 换行</small></div>
        </section>

        <aside className="citation-panel">
          <p className="aside-label">古籍旁证</p>
          {citation ? <div className="citation-card"><span>{citation.book.slice(0, 1)}</span><small>{citation.book}</small><h3>{citation.chapter}</h3><blockquote>{citation.text}</blockquote><p>{citation.plain}</p><em>文本来源可追溯</em></div> : <div className="citation-empty"><div className="book-lines" /><b>有据可考</b><p>山问回答时，相关古籍原文会在这里展开。</p></div>}
          <div className="citation-principle"><b>这里如何回答</b><p>先理解你的处境，再检索古籍原文，最后给出不夸大、不宿命的解释。</p></div>
        </aside>
      </div>
    </div>
  );
}
