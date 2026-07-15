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
      setText(''); setNotice(wish.moderation === 'approved' ? '心愿已挂上愿墙' : '心愿已收下，审核后会出现在愿墙');
    } catch (error) { setNotice(error instanceof ApiError ? error.message : '心愿暂未送达，请稍后再试'); }
    finally { setBusy(false); }
  };

  return (
    <div className="inner-page wishes-page">
      <header className="page-heading wishes-heading"><div><p className="eyebrow">凡愿有声 · 写给未来的自己</p><h1>许愿池</h1></div><p>愿望不是交换，而是一种确认：我知道自己珍惜什么，也愿意为它走一段路。</p></header>
      <div className="wish-ribbon"><span>{pool?.total ?? 108}</span> 个愿望正在风中轻响</div>
      <div className="content-wrap wishes-layout">
        <section className="wish-wall"><div className="section-row"><div><p className="aside-label">愿墙</p><h2 className="section-title">听见人间心事</h2></div><small>只展示审核通过的公开愿望</small></div><div className="wish-grid">{wishes.slice(0, 9).map((wish, index) => <article key={wish.id} className={`wish-plaque tone-${index % 3}`}><span>愿</span><p>{wish.text}</p><small>{new Date(wish.createdAt).toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' })}</small><i /></article>)}</div></section>
        <aside className="make-wish paper-panel"><span className="vertical-title">写下一愿</span><p className="eyebrow dark">此愿由你开始</p><h2>你真正盼望的，<br />是什么？</h2><p>写得具体一些。不是“希望一切顺利”，而是你愿意为之行动的那件事。</p><textarea className="field" maxLength={200} rows={6} value={text} onChange={(event) => setText(event.target.value)} placeholder="愿我……" /><div className="wish-count">{text.length} / 200</div><button className="primary-button wide" onClick={submit} disabled={busy || !text.trim()}>{busy ? '正在系上愿牌…' : '把心愿挂上愿墙'}</button>{notice ? <p className="wish-notice">{notice}</p> : null}<small>公开愿望需经过内容审核，不会展示个人联系方式。</small></aside>
      </div>
    </div>
  );
}
