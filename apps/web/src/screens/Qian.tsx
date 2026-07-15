import { useState } from 'react';
import { api, ApiError } from '../api/client';
import { useApp } from '../store/app';
import { TopBar } from '../components/ui';
import { C, mono } from '../theme/tokens';
import type { Qian as QianType } from '../shared';

export function Qian() {
  const { nav, go, requireAuth, showToast, user } = useApp();
  const [stage, setStage] = useState<'idle' | 'shaking' | 'done'>('idle');
  const [qian, setQian] = useState<QianType | null>(null);

  const shake = () => {
    requireAuth(async () => {
      setStage('shaking');
      // 摇签动画 1.2s，同时请求服务端发签
      const started = Date.now();
      try {
        const q = await api.drawQian(nav.hallKey ?? 'qianfang');
        const wait = Math.max(0, 1200 - (Date.now() - started));
        setTimeout(() => {
          setQian(q);
          setStage('done');
        }, wait);
      } catch (e) {
        setStage('idle');
        showToast(e instanceof ApiError ? e.message : '摇签失败');
      }
    });
  };

  const reset = () => {
    setStage('idle');
    setQian(null);
  };

  return (
    <div className="tj-body" style={{ paddingBottom: 24, display: 'flex', flexDirection: 'column' }}>
      <TopBar title="摇签问事" code="RNG · 天注定" onBack={() => go('home')} />

      {stage !== 'done' && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, padding: 20 }}>
          <div style={{ animation: stage === 'shaking' ? 'tjShake 0.5s ease-in-out infinite' : 'none', transformOrigin: '50% 90%' }}>
            <QianTube />
          </div>
          <div style={{ fontFamily: mono, fontSize: 11, color: C.muted, marginTop: 10 }}>
            {stage === 'shaking' ? '> 签筒晃动中 · 天机计算随机数…' : '> 心中默念所问之事，再摇签'}
          </div>
          <button
            className="tj-reset tj-clickable"
            onClick={shake}
            disabled={stage === 'shaking'}
            style={{
              marginTop: 14, background: stage === 'shaking' ? '#6B6154' : C.accent,
              color: C.creamText, textAlign: 'center', padding: '15px 52px', borderRadius: 14,
              fontSize: 16, fontWeight: 700, letterSpacing: 4,
            }}
          >
            {stage === 'shaking' ? '摇签中…' : '摇 签 ▸'}
          </button>
          {!user && <div style={{ fontFamily: mono, fontSize: 10, color: C.faint, marginTop: 8 }}>* 摇签需先登录</div>}
        </div>
      )}

      {stage === 'done' && qian && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: 20, animation: 'tjDrop 0.5s ease-out' }}>
          <div style={{ background: C.card, border: `1.5px solid ${C.accent}`, borderRadius: 18, padding: '22px 20px', position: 'relative' }}>
            <div style={{
              position: 'absolute', top: -1, left: '50%', transform: 'translateX(-50%)',
              background: C.accent, color: C.creamText, fontSize: 12, padding: '4px 16px',
              borderRadius: '0 0 10px 10px', letterSpacing: 3, whiteSpace: 'nowrap',
            }}>{qian.no} · {qian.level}</div>
            <div style={{ textAlign: 'center', fontSize: 19, fontWeight: 900, lineHeight: 2.1, marginTop: 18, letterSpacing: 1 }}>{qian.text}</div>
            <div style={{ textAlign: 'right', fontSize: 12, color: C.muted, marginTop: 8 }}>——{qian.src}</div>
            <div style={{ marginTop: 14, paddingTop: 12, borderTop: `1px dashed #D9CBA6`, fontSize: 13, color: C.sub, lineHeight: 1.9 }}>
              <span style={{ color: C.accent, fontWeight: 700 }}>签解：</span>{qian.note}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
            <button
              className="tj-reset tj-clickable"
              onClick={() => go('chat', { qianId: qian.id, chatPreset: '帮我解这支签' })}
              style={{ flex: 1, background: C.accent, color: C.creamText, textAlign: 'center', padding: 14, borderRadius: 14, fontWeight: 700, letterSpacing: 2 }}
            >请天机子解签</button>
            <button
              className="tj-reset tj-clickable"
              onClick={reset}
              style={{ flex: 1, border: `1.5px solid ${C.accent}`, color: C.accent, textAlign: 'center', padding: 14, borderRadius: 14, fontWeight: 700, letterSpacing: 2, background: 'transparent' }}
            >再摇一次</button>
          </div>
        </div>
      )}
    </div>
  );
}

function QianTube() {
  return (
    <div style={{ position: 'relative', width: 130, height: 200 }}>
      {[[24, 58], [42, 66], [60, 54], [78, 62], [96, 50]].map(([left, h], i) => (
        <div key={i} style={{
          position: 'absolute', bottom: 130 + (i % 2) * 6, left, width: 9, height: h,
          background: '#C9A063', borderRadius: 3, borderTop: `8px solid ${C.accent}`,
        }} />
      ))}
      <div style={{
        position: 'absolute', bottom: 0, left: 5, width: 120, height: 140,
        background: 'linear-gradient(90deg, #5E3025, #8A4636 45%, #5E3025)',
        borderRadius: '14px 14px 18px 18px', boxShadow: 'inset 0 -12px 20px rgba(0,0,0,0.3)',
      }} />
      <div style={{ position: 'absolute', bottom: 128, left: 0, width: 130, height: 18, background: '#4A251C', borderRadius: 999 }} />
      <div style={{
        position: 'absolute', bottom: 52, left: 5, width: 120, textAlign: 'center', color: C.gold,
        fontWeight: 900, fontSize: 22, letterSpacing: 6, writingMode: 'vertical-rl', height: 70,
        display: 'flex', justifyContent: 'center',
      }}>天机签</div>
    </div>
  );
}
