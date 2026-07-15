import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../api/client';
import { useApp } from '../store/app';
import { TopBar, Loading } from '../components/ui';
import { C, mono } from '../theme/tokens';
import type { Incense as IncenseType } from '../shared';

function fmt(sec: number) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export function Incense() {
  const { go, config, requireAuth, showToast, user } = useApp();
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState<IncenseType | null>(null);
  const [remaining, setRemaining] = useState(0);
  const [pick, setPick] = useState('tan');
  const [done, setDone] = useState(false);
  const tick = useRef<ReturnType<typeof setInterval>>();

  const incenses = config?.incenses ?? [];

  // 载入服务端权威状态（退出再进 / 换设备都在此恢复）
  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }
    api.incenseActive()
      .then((inc) => {
        if (inc && inc.status === 'burning') {
          setActive(inc);
          setRemaining(inc.remainingSec);
        } else if (inc && inc.status === 'done') {
          setDone(true);
        }
      })
      .finally(() => setLoading(false));
  }, [user]);

  // 本地倒计时（仅显示；真相在服务端 endsAt）
  useEffect(() => {
    if (!active) return;
    tick.current = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          clearInterval(tick.current);
          setActive(null);
          setDone(true);
          return 0;
        }
        return r - 1;
      });
    }, 1000);
    return () => clearInterval(tick.current);
  }, [active]);

  const light = () => {
    requireAuth(async () => {
      try {
        const inc = await api.lightIncense(pick);
        setActive(inc);
        setRemaining(inc.remainingSec);
        setDone(false);
      } catch (e) {
        showToast(e instanceof ApiError ? e.message : '点香失败');
      }
    });
  };

  if (loading) {
    return (
      <div className="tj-body" style={{ display: 'flex', flexDirection: 'column' }}>
        <TopBar title="上香" code="INCENSE" onBack={() => go('home')} />
        <Loading />
      </div>
    );
  }

  return (
    <div className="tj-body" style={{ paddingBottom: 24, display: 'flex', flexDirection: 'column' }}>
      <TopBar title="上香" code="INCENSE · 实时燃烧" onBack={() => go('home')} />

      {/* 选香 */}
      {!active && !done && (
        <div style={{ padding: '0 20px' }}>
          <div style={{ marginTop: 16, fontSize: 13, color: C.sub, lineHeight: 1.8 }}>
            选一炷香，点燃后<span style={{ color: C.accent, fontWeight: 700 }}>真实燃烧 30 分钟</span>——退出再进，它还在烧。香尽，签成。
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginTop: 14 }}>
            {incenses.map((inc) => (
              <div
                key={inc.key}
                className="tj-clickable"
                onClick={() => setPick(inc.key)}
                style={{
                  border: pick === inc.key ? `2px solid ${C.accent}` : `1px solid ${C.line}`,
                  background: C.card, borderRadius: 14, padding: '14px 10px', textAlign: 'center',
                }}
              >
                <div style={{ fontSize: 22, fontWeight: 900, color: C.accent }}>{inc.char}</div>
                <div style={{ fontWeight: 700, fontSize: 14, marginTop: 6 }}>{inc.name}</div>
                <div style={{ fontSize: 10, color: C.muted, marginTop: 4, lineHeight: 1.6 }}>{inc.desc}</div>
              </div>
            ))}
          </div>
          <button
            className="tj-reset tj-clickable"
            onClick={light}
            style={{ width: '100%', marginTop: 16, background: C.accent, color: C.creamText, textAlign: 'center', padding: 15, borderRadius: 14, fontSize: 16, fontWeight: 700, letterSpacing: 4 }}
          >点 香 ▸</button>
          {!user && <div style={{ fontFamily: mono, fontSize: 10, color: C.faint, marginTop: 8, textAlign: 'center' }}>* 上香需先登录</div>}
        </div>
      )}

      {/* 燃烧中 */}
      {active && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ fontFamily: mono, fontSize: 30, fontWeight: 600, color: C.ink }}>{fmt(remaining)}</div>
          <div style={{ fontFamily: mono, fontSize: 10, color: C.muted, marginTop: 4 }}>{active.name} · 燃烧中</div>
          <IncenseBurner />
          <div style={{ fontSize: 13, color: C.sub, marginTop: 8 }}>香在烧，愿在传 · 退出再进，它还在烧</div>
        </div>
      )}

      {/* 香尽 */}
      {done && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: 20, animation: 'tjDrop 0.5s ease-out' }}>
          <div style={{ background: C.card, border: `1.5px solid ${C.accent}`, borderRadius: 18, padding: '26px 20px', textAlign: 'center' }}>
            <div style={{
              width: 60, height: 60, margin: '0 auto', borderRadius: '50%', background: 'rgba(166,27,41,0.08)',
              border: `1px dashed ${C.accent}`, display: 'grid', placeItems: 'center', fontSize: 28, fontWeight: 900, color: C.accent,
            }}>愿</div>
            <div style={{ fontSize: 19, fontWeight: 900, letterSpacing: 2, marginTop: 14 }}>香已燃尽</div>
            <div style={{ fontSize: 13, color: C.sub, lineHeight: 1.9, marginTop: 8 }}>心愿已随青烟上传云端<br />此炉香，换得一支签</div>
          </div>
          <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
            <button className="tj-reset tj-clickable" onClick={() => go('qian', { hallKey: 'qianfang' })} style={{ flex: 1, background: C.accent, color: C.creamText, textAlign: 'center', padding: 14, borderRadius: 14, fontWeight: 700, letterSpacing: 2 }}>去摇一支签</button>
            <button className="tj-reset tj-clickable" onClick={() => { setDone(false); }} style={{ flex: 1, border: `1.5px solid ${C.accent}`, color: C.accent, textAlign: 'center', padding: 14, borderRadius: 14, fontWeight: 700, letterSpacing: 2, background: 'transparent' }}>再上一炷</button>
          </div>
        </div>
      )}
    </div>
  );
}

function IncenseBurner() {
  return (
    <div style={{ position: 'relative', width: 170, height: 250, marginTop: 10 }}>
      <div style={{ position: 'absolute', bottom: 190, left: '50%', transform: 'translateX(-50%)', width: 24, height: 10, borderRadius: '50%', background: 'rgba(140,120,90,0.35)', animation: 'tjSmoke 2.4s ease-out infinite' }} />
      <div style={{ position: 'absolute', bottom: 190, left: '50%', transform: 'translateX(-50%)', width: 7, height: 7, borderRadius: '50%', background: '#FF7A45', boxShadow: '0 0 12px 3px rgba(255,122,69,0.7)', animation: 'tjBlink 1.1s infinite' }} />
      <div style={{ position: 'absolute', bottom: 78, left: '50%', transform: 'translateX(-50%)', width: 5, height: 112, background: 'linear-gradient(180deg, #7A5A3A, #5E4526)', borderRadius: 3 }} />
      <div style={{ position: 'absolute', bottom: 26, left: '50%', transform: 'translateX(-50%)', width: 150, height: 58, background: 'linear-gradient(180deg, #8C6B3F, #5E4526)', borderRadius: '10px 10px 70px 70px' }} />
      <div style={{ position: 'absolute', bottom: 74, left: '50%', transform: 'translateX(-50%)', width: 150, height: 16, background: '#4A3820', borderRadius: 999 }} />
    </div>
  );
}
