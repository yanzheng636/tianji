import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../api';
import { useTianji } from '../App';
import type { Qian as QianResult, Quota } from '../types';

const fallbackHalls = [
  { key: 'qianfang', name: '问心', char: '问', sub: '万事皆可问', topic: 'general' },
  { key: 'wenshu', name: '文殊', char: '文', sub: '学业与抉择', topic: 'study' },
  { key: 'yuelao', name: '月老', char: '缘', sub: '关系与情感', topic: 'love' },
  { key: 'caishen', name: '财神', char: '财', sub: '事业与取舍', topic: 'career' },
];

export function Qian() {
  const { config } = useTianji();
  const halls = config?.halls?.length ? config.halls.slice(0, 5) : fallbackHalls;
  const [hall, setHall] = useState(halls[0]?.key ?? 'qianfang');
  const [result, setResult] = useState<QianResult | null>(null);
  const [quota, setQuota] = useState<Quota | null>(null);
  const [drawing, setDrawing] = useState(false);
  const [error, setError] = useState('');
  const currentHall = halls.find((item) => item.key === hall) ?? halls[0];
  const currentCopy = hallCopy(currentHall);

  useEffect(() => { void api.qianQuota().then(setQuota).catch(() => undefined); }, []);

  const draw = async () => {
    setDrawing(true); setError('');
    try {
      const value = await api.drawQian(hall);
      window.setTimeout(() => { setResult(value); setDrawing(false); }, 1250);
      void api.qianQuota().then(setQuota);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '签筒暂时无声，请稍后再试');
      setDrawing(false);
    }
  };

  return (
    <div className="premium-qian-page">
      <section className={drawing ? 'qian-chamber is-drawing' : 'qian-chamber'} aria-labelledby="qian-title">
        <img src="/images/qian-chamber-premium.webp" className="qian-chamber-image" alt="暗色签房内，木案上放着一只竹签筒" />
        <div className="qian-chamber-shade" />
        <div className="qian-chamber-grain" />

        <header className="qian-chamber-header">
          <p className="museum-label"><span>{currentCopy.name}</span><i />签室</p>
          <div><span>今日尚可求签</span><strong>{quota?.remaining ?? '—'}</strong><span>次</span></div>
        </header>

        {result ? (
          <QianReading result={result} onReset={() => setResult(null)} />
        ) : (
          <div className="qian-intention">
            <span className="qian-step">壹</span>
            <p>先不问吉凶</p>
            <h1 id="qian-title">静心片刻，<br />再问所问之事。</h1>
            <p>把真正困扰你的那件事，在心里说完整。</p>
            <button className="qian-draw-button" onClick={draw} disabled={drawing}>
              <span>{drawing ? '签意将明' : '静心摇签'}</span><i>{drawing ? '···' : '→'}</i>
            </button>
            {error ? <small className="qian-error">{error}</small> : null}
          </div>
        )}

        {!result ? (
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
  return (
    <div className="premium-qian-result">
      <div className="premium-qian-paper">
        <span>{result.no}{result.story ? ` · ${result.story}` : ''}</span>
        <strong>{result.text.split(/[，。]/).filter(Boolean).map((line, index) => <em key={index}>{line}</em>)}</strong>
        <i>{result.level}</i><small>關聖帝君靈籤</small>
      </div>
      <article>
        <p className="museum-label"><span>此签照见</span><i />READING</p>
        <h2>{result.level}</h2>
        {result.story ? <p className="qian-story">签题 · {result.story}</p> : null}
        <p>{result.note}</p>
        <blockquote>{result.text}</blockquote>
        <small>原典出处 · {result.src}</small>
        <div><button onClick={onReset}>再问一事</button><Link to={`/chat?qian=${encodeURIComponent(result.id)}`}>带此签去问卦 <span>→</span></Link></div>
      </article>
    </div>
  );
}
