import { useEffect, useMemo, useState, type CSSProperties } from 'react';
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
  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [active]);

  const left = useMemo(() => active ? Math.max(0, Math.ceil((new Date(active.endsAt).getTime() - now) / 1000)) : 0, [active, now]);
  const progress = active ? Math.max(0, Math.min(100, (left / 1800) * 100)) : 100;
  const time = `${String(Math.floor(left / 60)).padStart(2, '0')}:${String(left % 60).padStart(2, '0')}`;

  const light = async () => {
    setBusy(true); setError('');
    try { setActive(await api.lightIncense(selected, wish.trim() || undefined)); setWish(''); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : '此刻未能开始静坐，请稍后再试'); }
    finally { setBusy(false); }
  };

  return (
    <div className="ritual-page incense-page">
      <header className="ritual-heading">
        <p className="museum-label"><span>静室</span><i />半个时辰</p>
        <h1>留一段时间，<br />只与自己相处。</h1>
        <p>点香不是向外求一个结果，而是把注意力重新带回当下。</p>
      </header>

      <div className="ritual-stage">
        <section className="ritual-clock" aria-live="polite">
          <div className={active && left > 0 ? 'time-orbit is-active' : 'time-orbit'} style={{ '--ritual-progress': `${progress}%` } as CSSProperties}>
            <div><small>{active && left > 0 ? '静坐剩余' : '一次静坐'}</small><strong>{active && left > 0 ? time : '30:00'}</strong><span>{active && left > 0 ? active.name : '山中无事'}</span></div>
          </div>
          <blockquote>{active && left > 0 ? '这段时间，不必急着得到答案。' : '先让呼吸慢下来，再写一句真正想对自己说的话。'}</blockquote>
          <small>计时由服务端记录，离开页面后仍会继续</small>
        </section>

        <section className="ritual-form">
          <div className="ritual-form-head"><span>选择此刻的心意</span><small>壹 / 贰</small></div>
          <div className="intention-options">
            {incenses.map((item) => (
              <button key={item.key} className={selected === item.key ? 'active' : ''} onClick={() => setSelected(item.key)} disabled={Boolean(active && left > 0)}>
                <span>{item.char}</span><div><b>{item.name}</b><small>{item.desc}</small></div><i>{selected === item.key ? '已选' : '选择'}</i>
              </button>
            ))}
          </div>
          <label className="ritual-message">写给此刻的自己 <small>可不写</small>
            <textarea rows={4} maxLength={200} value={wish} onChange={(event) => setWish(event.target.value)} placeholder="愿我在纷乱里，仍能看清真正重要的事。" />
            <span>{wish.length} / 200</span>
          </label>
          <button className="ritual-submit" onClick={light} disabled={busy || Boolean(active && left > 0)}>
            {active && left > 0 ? '静坐正在进行' : busy ? '正在开始…' : '开始半小时静坐'}<span>→</span>
          </button>
          {error ? <p className="form-error">{error}</p> : null}
        </section>
      </div>
    </div>
  );
}
