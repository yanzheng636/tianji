import { useEffect, useState } from 'react';
import { api, ApiError } from '../api';
import type { Wish, WishPool } from '../types';

const sampleWishes: Wish[] = [
  { id: 'sample-1', text: '愿我有耐心走完正在走的路，也有勇气在不合适时转身。', status: 'active', moderation: 'approved', moderationReason: null, createdAt: new Date().toISOString(), fulfilledAt: null, mine: false },
  { id: 'sample-2', text: '愿家人平安，也愿自己不再把所有担心都藏在心里。', status: 'active', moderation: 'approved', moderationReason: null, createdAt: new Date().toISOString(), fulfilledAt: null, mine: false },
  { id: 'sample-3', text: '愿今年读完十二本真正喜欢的书。', status: 'active', moderation: 'approved', moderationReason: null, createdAt: new Date().toISOString(), fulfilledAt: null, mine: false },
];

export function Wishes() {
  const [pool, setPool] = useState<WishPool | null>(null);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');

  useEffect(() => { void api.wishPool().then(setPool).catch(() => undefined); }, []);
  const wishes = pool?.floating?.length ? pool.floating : sampleWishes;

  const submit = async () => {
    if (!text.trim() || busy) return;
    setBusy(true); setNotice('');
    try {
      const wish = await api.createWish(text.trim());
      setPool((current) => current ? { ...current, mine: [wish, ...current.mine] } : { total: 1, floating: [], mine: [wish] });
      setText(''); setNotice(wish.moderation === 'approved' ? '这句话已留在愿池' : '这句话已收下，审核后会出现在愿池');
    } catch (error) { setNotice(error instanceof ApiError ? error.message : '这句话暂未送达，请稍后再试'); }
    finally { setBusy(false); }
  };

  return (
    <div className="wish-ledger-page">
      <header className="wish-ledger-heading">
        <div><p className="museum-label"><span>愿池</span><i />人间心事</p><h1>写下所愿，<br />也写下愿意走的路。</h1></div>
        <div className="wish-total"><strong>{pool?.total ?? 108}</strong><span>个愿望<br />正在被认真对待</span></div>
      </header>

      <div className="wish-ledger-layout">
        <section className="wish-editor">
          <div className="wish-editor-index">你的愿望 · 001</div>
          <h2>真正盼望的，<br />是什么？</h2>
          <p>写得具体一些。不是“一切顺利”，而是你愿意为之行动的那件事。</p>
          <div className="wish-writing-area">
            <textarea maxLength={200} rows={7} value={text} onChange={(event) => setText(event.target.value)} placeholder="愿我……" />
            <span>{text.length} / 200</span>
          </div>
          <button onClick={submit} disabled={busy || !text.trim()}>{busy ? '正在收下…' : '把这句话留在愿池'}<span>→</span></button>
          {notice ? <p className="wish-notice" role="status">{notice}</p> : null}
          <small>公开内容会先经过审核，不会展示联系方式与个人身份。</small>
        </section>

        <section className="wish-voices">
          <div className="wish-voices-head"><div><span>愿池来信</span><h2>听见别人，也照见自己</h2></div><small>只展示审核通过的公开内容</small></div>
          <div className="wish-entries">
            {wishes.slice(0, 6).map((wish, index) => (
              <article key={wish.id}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                <blockquote>{wish.text}</blockquote>
                <time>{new Date(wish.createdAt).toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' })}</time>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
