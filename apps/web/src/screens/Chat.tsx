import { useEffect, useRef, useState } from 'react';
import { api, streamChat } from '../api/client';
import { useApp } from '../store/app';
import { C, mono } from '../theme/tokens';
import type { ChatMessage } from '../shared';

const WELCOME: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  text: '贫道天机子，内核 v3.0，已挂载《麻衣相法》《渊海子平》《周易》《关帝灵签》等古籍。施主想问点什么？上岸、搞钱，还是姻缘？',
  citation: null,
  createdAt: '',
};

const QUICK = ['我今年能上岸吗', '财运如何', '该不该跳槽', '姻缘什么时候来'];

export function Chat() {
  const { requireAuth, showToast, user, nav } = useApp();
  const [msgs, setMsgs] = useState<ChatMessage[]>([WELCOME]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [typing, setTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const presetFired = useRef(false);

  const scrollDown = () => {
    requestAnimationFrame(() => {
      if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    });
  };

  // 载入历史
  useEffect(() => {
    if (!user) return;
    api.chatHistory().then((h) => {
      if (h.length) setMsgs(h);
      scrollDown();
    }).catch(() => {});
  }, [user]);

  const send = (text: string, qianId?: string) => {
    const t = text.trim();
    if (!t || streaming) return;
    requireAuth(() => {
      setInput('');
      const userMsg: ChatMessage = { id: `u-${Date.now()}`, role: 'user', text: t, citation: null, createdAt: '' };
      const aiId = `a-${Date.now()}`;
      setMsgs((m) => [...m.filter((x) => x.id !== 'welcome'), userMsg]);
      setStreaming(true);
      setTyping(true);
      scrollDown();

      let started = false;
      streamChat({ text: t, qianId }, (e) => {
        if (e.type === 'delta') {
          if (!started) {
            started = true;
            setTyping(false);
            setMsgs((m) => [...m, { id: aiId, role: 'assistant', text: e.text, citation: null, createdAt: '' }]);
          } else {
            setMsgs((m) => m.map((x) => (x.id === aiId ? { ...x, text: x.text + e.text } : x)));
          }
          scrollDown();
        } else if (e.type === 'citation') {
          setMsgs((m) => m.map((x) => (x.id === aiId ? { ...x, citation: e.citation } : x)));
          scrollDown();
        } else if (e.type === 'done') {
          setStreaming(false);
          setTyping(false);
        } else if (e.type === 'error') {
          setStreaming(false);
          setTyping(false);
          showToast(e.message);
        }
      });
    });
  };

  // 处理带入的预设问题
  useEffect(() => {
    if (presetFired.current) return;
    if (nav.chatPreset !== undefined && user) {
      presetFired.current = true;
      if (nav.chatPreset) send(nav.chatPreset, nav.qianId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nav.chatPreset, user]);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* 大师头 */}
      <div style={{ padding: '12px 20px', display: 'flex', alignItems: 'center', gap: 12, borderBottom: `1px solid ${C.lineSoft}`, background: C.paper }}>
        <div style={{ width: 42, height: 42, borderRadius: '50%', background: C.accent, color: C.creamText, display: 'grid', placeItems: 'center', fontSize: 20, fontWeight: 900 }}>天</div>
        <div>
          <div style={{ fontSize: 16, fontWeight: 900, letterSpacing: 1 }}>天机子</div>
          <div style={{ fontFamily: mono, fontSize: 10, color: C.green }}>● AGENT 在线 · 已挂载古籍库</div>
        </div>
      </div>

      {/* 消息区 */}
      <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {msgs.map((m) => {
          const me = m.role === 'user';
          return (
            <div key={m.id} style={{ display: 'flex', justifyContent: me ? 'flex-end' : 'flex-start' }}>
              <div style={{
                maxWidth: '82%', background: me ? C.accent : '#fff', color: me ? C.creamText : C.ink,
                borderRadius: me ? '16px 16px 4px 16px' : '16px 16px 16px 4px', padding: '11px 14px',
                fontSize: 14, lineHeight: 1.75, border: `1px solid ${me ? C.accent : C.lineSoft}`,
              }}>
                <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
                {m.citation && (
                  <div style={{ marginTop: 10, background: C.cardWarm, border: '1px solid #D9CBA6', borderRadius: 10, padding: '10px 12px' }}>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 6 }}>
                      <span style={{ fontFamily: mono, fontSize: 10, color: C.green, border: `1px solid ${C.green}`, borderRadius: 999, padding: '2px 7px' }}>
                        {m.citation.quality === 'verified' ? '原典已校验' : '原典待复核'}
                      </span>
                      {m.citation.concepts.slice(0, 3).map((concept) => (
                        <span key={concept} style={{ fontFamily: mono, fontSize: 10, color: C.muted, border: `1px solid ${C.line}`, borderRadius: 999, padding: '2px 7px' }}>{concept}</span>
                      ))}
                      {m.citation.structure?.number_label != null && (
                        <span style={{ fontFamily: mono, fontSize: 10, color: C.accent, border: `1px solid ${C.accent}`, borderRadius: 999, padding: '2px 7px' }}>
                          {String(m.citation.structure.number_label)} {m.citation.structure.level ? `· ${String(m.citation.structure.level)}` : ''}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: C.inkSoft, lineHeight: 1.8 }}>“{m.citation.text}”</div>
                    <div style={{ fontSize: 11, color: C.muted, textAlign: 'right', marginTop: 4 }}>——《{m.citation.book} · {m.citation.chapter}》</div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
        {typing && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{ background: '#fff', border: `1px solid ${C.lineSoft}`, borderRadius: '16px 16px 16px 4px', padding: '12px 16px', display: 'flex', gap: 5, alignItems: 'center' }}>
              <span style={{ fontFamily: mono, fontSize: 11, color: C.muted }}>天机推演中</span>
              {[0, 0.2, 0.4].map((d) => (
                <span key={d} style={{ width: 5, height: 5, borderRadius: '50%', background: C.accent, animation: `tjBlink 1.2s ${d}s infinite` }} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 输入区 */}
      <div style={{ padding: '10px 20px 12px', background: C.paper, borderTop: `1px solid ${C.lineSoft}` }}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
          {QUICK.map((q) => (
            <button key={q} className="tj-reset tj-clickable" onClick={() => send(q)} style={{ fontSize: 12, border: `1px solid ${C.line}`, background: C.card, borderRadius: 999, padding: '6px 12px', color: C.sub }}>{q}</button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') send(input, nav.qianId); }}
            placeholder="向天机子问一卦…"
            style={{ flex: 1, border: `1px solid ${C.line}`, background: '#fff', borderRadius: 12, padding: '12px 14px', fontSize: 14, color: C.ink, outline: 'none' }}
          />
          <button className="tj-reset tj-clickable" onClick={() => send(input, nav.qianId)} disabled={streaming} style={{ width: 46, height: 46, borderRadius: 12, background: C.accent, color: C.creamText, display: 'grid', placeItems: 'center', fontSize: 18, fontWeight: 900, opacity: streaming ? 0.6 : 1 }}>问</button>
        </div>
      </div>
    </div>
  );
}
