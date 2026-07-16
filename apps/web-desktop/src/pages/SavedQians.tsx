import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../api';
import type { Qian } from '../types';

export function SavedQians() {
  const [items, setItems] = useState<Qian[]>([]);
  const [loading, setLoading] = useState(true);
  const [removing, setRemoving] = useState<string | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    void api.listSavedQian()
      .then((data) => { if (active) setItems(data); })
      .catch((reason) => { if (active) setError(reason instanceof ApiError ? reason.message : '静心集暂时未能打开'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const remove = async (item: Qian) => {
    setRemoving(item.id);
    setError('');
    try {
      await api.saveQian(item.id, false);
      setItems((value) => value.filter((qian) => qian.id !== item.id));
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '这支签暂时未能移出');
    } finally {
      setRemoving(null);
    }
  };

  return (
    <div className="saved-qians-page">
      <header className="saved-qians-hero">
        <div>
          <p className="museum-label"><span>我的山居</span><i />QUIET COLLECTION</p>
          <h1>静心集</h1>
          <p>只留下你亲手收藏的签。回看不是重问，而是看看当时的念头走到了哪里。</p>
        </div>
        <Link to="/qian"><span>再去签室</span><i>→</i></Link>
      </header>

      <main className="saved-qians-content">
        <header><div><span>已留签文</span><strong>{loading ? '—' : items.length}</strong></div><Link to="/profile">返回命盘总览</Link></header>
        {error ? <p className="saved-qians-error">{error}</p> : null}
        {loading ? <div className="saved-qians-loading"><i />正在展开静心集…</div> : null}
        {!loading && items.length === 0 ? (
          <div className="saved-qians-empty"><span>签</span><h2>还没有留下的签</h2><p>有些念头值得收好。去签室静一静，遇见想留下的那一支。</p><Link to="/qian">去摇一支 <i>→</i></Link></div>
        ) : null}
        {!loading && items.length ? (
          <div className="saved-qians-grid">
            {items.map((item) => <SavedQianCard key={item.id} item={item} removing={removing === item.id} onRemove={() => void remove(item)} />)}
          </div>
        ) : null}
      </main>
    </div>
  );
}

function SavedQianCard({ item, removing, onRemove }: { item: Qian; removing: boolean; onRemove: () => void }) {
  const date = new Date(item.drawnAt);
  const dateText = Number.isNaN(date.getTime()) ? '' : new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' }).format(date);
  return (
    <article className="saved-qian-card">
      <div className="saved-qian-paper"><span>{item.no}</span><strong>{item.text}</strong><i>{item.level}</i></div>
      <div className="saved-qian-copy">
        <small>{dateText} · {item.topic}</small>
        <h2>{item.story || '一念留存'}</h2>
        <p>这支签曾在此刻被你留下。回看签面，也回看当时真正牵动你的那件事；不替未来下结论，只照见已经走过的心路。</p>
        <div><Link to={`/chat?qian=${encodeURIComponent(item.id)}`}>带此签再谈 <span>→</span></Link><button onClick={onRemove} disabled={removing}>{removing ? '正在移出…' : '移出静心集'}</button></div>
      </div>
    </article>
  );
}
