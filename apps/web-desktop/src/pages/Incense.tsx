import { useEffect, useMemo, useState } from 'react';
import { api, ApiError } from '../api';
import { useTianji } from '../App';
import type { Incense as IncenseType } from '../types';

const fallback = [
  { key: 'peace', char: '安', name: '清心香', desc: '给纷乱的思绪留一段安静', durationSec: 1800 },
  { key: 'wish', char: '愿', name: '祈愿香', desc: '把心愿认真说给自己听', durationSec: 1800 },
  { key: 'thanks', char: '谢', name: '感恩香', desc: '记住此刻已经拥有的事物', durationSec: 1800 },
];

export function Incense() {
  const { config } = useTianji();
  const incenses = config?.incenses?.length ? config.incenses : fallback;
  const [selected, setSelected] = useState(incenses[0]?.key ?? 'peace');
  const [wish, setWish] = useState('');
  const [active, setActive] = useState<IncenseType | null>(null);
  const [now, setNow] = useState(Date.now());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { void api.incenseActive().then(setActive).catch(() => undefined); }, []);
  useEffect(() => { if (!active) return; const timer = window.setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, [active]);
  const left = useMemo(() => active ? Math.max(0, Math.ceil((new Date(active.endsAt).getTime() - now) / 1000)) : 0, [active, now]);
  const time = `${String(Math.floor(left / 60)).padStart(2, '0')}:${String(left % 60).padStart(2, '0')}`;

  const light = async () => {
    setBusy(true); setError('');
    try { setActive(await api.lightIncense(selected, wish.trim() || undefined)); setWish(''); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : '香火暂未点燃'); }
    finally { setBusy(false); }
  };

  return (
    <div className="inner-page incense-page">
      <header className="page-heading"><div><p className="eyebrow">留半个时辰 · 与自己安坐</p><h1>香火殿</h1></div><p>点香不是向外求一个结果，而是给自己一段不被打扰的时间。</p></header>
      <div className="content-wrap incense-layout">
        <section className="incense-visual paper-panel"><div className={active && left > 0 ? 'incense-stick is-burning' : 'incense-stick'}><div className="smoke"><i /><i /><i /></div><span /></div><div className="incense-clock"><small>{active && left > 0 ? active.name + ' · 燃香中' : '香案已净 · 静候一念'}</small><strong>{active && left > 0 ? time : '30:00'}</strong><p>{active && left > 0 ? '这段时间，不必急着得到答案。' : '选一炷香，写下一句想对自己说的话。'}</p></div></section>
        <section className="incense-form"><p className="aside-label">择一炷香</p><div className="incense-options">{incenses.map((item) => <button key={item.key} className={selected === item.key ? 'active' : ''} onClick={() => setSelected(item.key)} disabled={Boolean(active && left > 0)}><span>{item.char}</span><div><b>{item.name}</b><small>{item.desc}</small></div></button>)}</div><label>寄语 <small>可不写</small><textarea className="field" rows={4} maxLength={200} value={wish} onChange={(event) => setWish(event.target.value)} placeholder="愿我在纷乱里，仍能看清真正重要的事。" /></label><button className="primary-button wide" onClick={light} disabled={busy || Boolean(active && left > 0)}>{active && left > 0 ? '此香正在燃烧' : busy ? '正在点香…' : '点燃此香'}</button>{error ? <p className="form-error">{error}</p> : null}<p className="section-note">计时由寺中服务器记录，关闭页面后仍会继续。</p></section>
      </div>
    </div>
  );
}
