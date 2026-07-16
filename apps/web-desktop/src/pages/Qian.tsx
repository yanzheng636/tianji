import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError, streamQianReading } from '../api';
import { useTianji } from '../App';
import type { Qian as QianResult, Quota } from '../types';

const fallbackHalls = [
  { key: 'qianfang', name: '问心', char: '问', sub: '万事皆可问', topic: 'general' },
  { key: 'wenshu', name: '文殊', char: '文', sub: '学业与抉择', topic: 'study' },
  { key: 'yuelao', name: '月老', char: '缘', sub: '关系与情感', topic: 'love' },
  { key: 'caishen', name: '财神', char: '财', sub: '事业与取舍', topic: 'career' },
];

type DrawPhase = 'idle' | 'summoning' | 'shaking' | 'ejecting' | 'revealing';
type ActiveDrawPhase = Exclude<DrawPhase, 'idle'>;

const wait = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));
const readingFallback = '这支签先照见你此刻的迟疑：不必急着替未来下结论。\n今日可做：写下眼前最小、最确定的一步，只完成这一件。\n心若从容，万事皆缓。';

export function Qian() {
  const { config } = useTianji();
  const halls = config?.halls?.length ? config.halls.slice(0, 5) : fallbackHalls;
  const [hall, setHall] = useState(halls[0]?.key ?? 'qianfang');
  const [result, setResult] = useState<QianResult | null>(null);
  const [quota, setQuota] = useState<Quota | null>(null);
  const [drawing, setDrawing] = useState(false);
  const [phase, setPhase] = useState<DrawPhase>('idle');
  const [error, setError] = useState('');
  const drawRun = useRef(0);
  const currentHall = halls.find((item) => item.key === hall) ?? halls[0];
  const currentCopy = hallCopy(currentHall);

  useEffect(() => { void api.qianQuota().then(setQuota).catch(() => undefined); }, []);
  useEffect(() => () => { drawRun.current += 1; }, []);

  const draw = async () => {
    const run = ++drawRun.current;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    setDrawing(true);
    setError('');
    setPhase('summoning');

    const outcomePromise = api.drawQian(hall).then(
      (value) => ({ value, error: null }),
      (reason: unknown) => ({ value: null, error: reason }),
    );

    try {
      if (!reducedMotion) {
        await wait(480);
        if (run !== drawRun.current) return;
        setPhase('shaking');
        await wait(1280);
      }
      const outcome = await outcomePromise;
      if (run !== drawRun.current) return;
      if (outcome.error) throw outcome.error;
      if (!outcome.value) throw new Error('签筒暂时无声');

      if (!reducedMotion) {
        setPhase('ejecting');
        await wait(680);
        if (run !== drawRun.current) return;
        setPhase('revealing');
      }
      setResult(outcome.value);
      setDrawing(false);
      void api.qianQuota().then(setQuota).catch(() => undefined);
      if (!reducedMotion) await wait(520);
      if (run === drawRun.current) setPhase('idle');
    } catch (reason) {
      if (run !== drawRun.current) return;
      setError(reason instanceof ApiError ? reason.message : '签筒暂时无声，请稍后再试');
      setDrawing(false);
      setPhase('idle');
    }
  };

  const chamberClass = ['qian-chamber', drawing ? 'is-drawing' : '', phase !== 'idle' ? `phase-${phase}` : ''].filter(Boolean).join(' ');

  return (
    <div className="premium-qian-page">
      <section className={chamberClass} aria-labelledby="qian-title">
        <img src="/images/qian-chamber-premium.webp" className="qian-chamber-image" alt="暗色签房内，木案上放着一只竹签筒" />
        <div className="qian-chamber-shade" />
        <div className="qian-chamber-grain" />

        <header className="qian-chamber-header">
          <p className="museum-label"><span>{currentCopy.name}</span><i />签室</p>
          <div>
            <span>{quota?.unlimited ? '今日求签' : '今日尚可求签'}</span>
            <strong>{quota?.unlimited ? '不限' : (quota?.remaining ?? '—')}</strong>
            {quota?.unlimited ? null : <span>次</span>}
          </div>
        </header>

        {result ? (
          <QianReading result={result} onReset={() => setResult(null)} />
        ) : phase === 'idle' ? (
          <div className="qian-intention">
            <span className="qian-step">壹</span>
            <p>先不问吉凶</p>
            <h1 id="qian-title">静心片刻，<br />再问所问之事。</h1>
            <p>把真正困扰你的那件事，在心里说完整。</p>
            <button className="qian-draw-button" onClick={draw} disabled={drawing}>
              <span>静心摇签</span><i>→</i>
            </button>
            {error ? <small className="qian-error">{error}</small> : null}
          </div>
        ) : null}

        {phase !== 'idle' ? <QianRitual phase={phase} /> : null}

        {!result && phase === 'idle' ? (
          <div className="hall-plaques" aria-label="选择求签主题">
            <span className="hall-plaques-label">择一殿</span>
            {halls.map((item) => (
              <button key={item.key} className={hall === item.key ? 'active' : ''} onClick={() => setHall(item.key)} disabled={drawing}>
                <span>{item.char}</span><div><b>{hallCopy(item).name}</b><small>{hallCopy(item).sub}</small></div>
              </button>
            ))}
          </div>
        ) : null}

        <footer className="qian-chamber-footer"><span>签是观照，不是命令</span><span>传统文化娱乐 · 不作为现实决策依据</span></footer>
      </section>
    </div>
  );
}

function QianRitual({ phase }: { phase: ActiveDrawPhase }) {
  const copy: Record<ActiveDrawPhase, string> = {
    summoning: '请签入案',
    shaking: '静听签声',
    ejecting: '一签应心',
    revealing: '签意将明',
  };
  return (
    <div className={`qian-ritual qian-ritual-${phase}`} role="status" aria-live="polite">
      <div className="qian-ritual-halo" />
      <div className="qian-ritual-object" aria-hidden="true">
        <div className="qian-loose-sticks"><i /><i /><i /><i /><i /></div>
        <div className="qian-chosen-stick"><span>山问</span></div>
        <div className="qian-ritual-cylinder"><i /><b>签</b><i /></div>
      </div>
      <p><span>{copy[phase]}</span><i /></p>
    </div>
  );
}

function hallCopy(item: { key: string; name: string; char: string; sub: string } | undefined) {
  if (!item) return { name: '山问签室', sub: '今日一事' };
  const copies: Record<string, { name: string; sub: string }> = {
    文: { name: '问学', sub: '学业与抉择' },
    缘: { name: '问缘', sub: '关系与情感' },
    财: { name: '问业', sub: '事业与取舍' },
    机: { name: '问心', sub: '万事皆可问' },
    签: { name: '山问签室', sub: '今日一事' },
  };
  return copies[item.char] ?? { name: item.name, sub: item.sub.includes('·') ? '静心观照' : item.sub };
}

function QianReading({ result, onReset }: { result: QianResult; onReset: () => void }) {
  const [reading, setReading] = useState('');
  const [readingState, setReadingState] = useState<'loading' | 'done' | 'error'>('loading');
  const [saved, setSaved] = useState(result.saved);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState('');

  useEffect(() => {
    setReading('');
    setReadingState('loading');
    setSaved(result.saved);
    setActionError('');
    return streamQianReading(result.id, (event) => {
      if (event.type === 'delta') setReading((value) => value + event.text);
      if (event.type === 'done') setReadingState('done');
      if (event.type === 'error') setReadingState('error');
    });
  }, [result.id, result.saved]);

  const toggleSaved = async () => {
    if (saving) return;
    setSaving(true);
    setActionError('');
    try {
      const state = await api.saveQian(result.id, !saved);
      setSaved(state.saved);
    } catch (reason) {
      setActionError(reason instanceof ApiError ? reason.message : '静心集暂时未能打开');
    } finally {
      setSaving(false);
    }
  };

  const visibleReading = reading || (readingState === 'error' ? readingFallback : '山问正沿着这支签，慢慢照见你的所问……');

  return (
    <div className="premium-qian-result">
      <div className="premium-qian-paper">
        <span>{result.no}{result.story ? ` · ${result.story}` : ''}</span>
        <strong>{result.text.split(/[，。]/).filter(Boolean).map((line, index) => <em key={index}>{line}</em>)}</strong>
        <i>{result.level}</i><small>關聖帝君靈籤</small>
      </div>
      <article className="qian-reading-copy">
        <p className="museum-label"><span>此签照见</span><i />REFLECTION</p>
        <h2>{result.story || '此刻，先把心放稳'}</h2>
        <p className="qian-reading-meta">{result.no} · {result.level}</p>
        <section className={`qian-guidance ${readingState === 'loading' ? 'is-streaming' : ''}`}>
          <header><span>心绪指引</span><small>{readingState === 'loading' ? '正在展开' : readingState === 'error' ? '静心观照' : '由命盘与所问生成'}</small></header>
          <p aria-live="polite">{visibleReading}</p>
        </section>
        <blockquote>{result.text}</blockquote>
        <small className="qian-source">原典出处 · {result.src}</small>
        <div className="qian-result-actions">
          <button className={saved ? 'qian-save-button is-saved' : 'qian-save-button'} onClick={toggleSaved} disabled={saving} title={saved ? '点击移出静心集' : '收藏到静心集'}>
            <span>{saved ? '已存入静心集' : '收藏 · 存入静心集'}</span><i>{saved ? '✓' : '＋'}</i>
          </button>
          <Link className="qian-chat-button" to={`/chat?qian=${encodeURIComponent(result.id)}`}>带此签去问卦 <span>→</span></Link>
        </div>
        <button className="qian-reset-button" onClick={onReset}>再问一事</button>
        {actionError ? <p className="qian-action-error">{actionError}</p> : null}
      </article>
    </div>
  );
}
