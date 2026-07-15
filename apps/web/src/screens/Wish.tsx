import { useEffect, useState } from 'react';
import { api, ApiError } from '../api/client';
import { useApp } from '../store/app';
import { C, mono } from '../theme/tokens';
import type { WishPool } from '../shared';

const FLOAT_POS = [
  { x: '8%', y: '52%', dur: '7s' },
  { x: '56%', y: '58%', dur: '9s' },
  { x: '30%', y: '68%', dur: '8s' },
  { x: '62%', y: '78%', dur: '6.5s' },
  { x: '14%', y: '80%', dur: '7.5s' },
];

export function Wish() {
  const { requireAuth, showToast, user } = useApp();
  const [pool, setPool] = useState<WishPool | null>(null);
  const [writing, setWriting] = useState(false);
  const [input, setInput] = useState('');
  const [coin, setCoin] = useState(false);

  const load = () => api.wishPool().then(setPool).catch(() => {});
  useEffect(() => { load(); }, [user]);

  const toss = () => {
    const text = input.trim();
    if (!text) return showToast('先写下心愿，铜钱才知道往哪落');
    requireAuth(async () => {
      setCoin(true);
      try {
        const w = await api.createWish(text);
        setInput('');
        setWriting(false);
        setTimeout(() => setCoin(false), 1200);
        if (w.moderation === 'rejected') {
          showToast('心愿含不当内容，未能入池');
        } else {
          showToast('叮咚 · 愿望已入池，天机已记录');
        }
        load();
      } catch (e) {
        setCoin(false);
        showToast(e instanceof ApiError ? e.message : '投币失败');
      }
    });
  };

  const fulfill = (id: string) => {
    requireAuth(async () => {
      try {
        await api.fulfillWish(id);
        showToast('愿已应验 · 钟声三响，功德圆满');
        load();
      } catch (e) {
        showToast(e instanceof ApiError ? e.message : '操作失败');
      }
    });
  };

  const floating = (pool?.floating ?? []).slice(0, 5);

  return (
    <div className="tj-body" style={{
      marginTop: -58, padding: '68px 0 24px',
      background: 'linear-gradient(180deg, #0B0F17 0%, #101724 34%, #17222E 52%, #121B23 100%)',
    }}>
      <div style={{ padding: '0 22px', display: 'flex', alignItems: 'baseline', gap: 12 }}>
        <div style={{ fontSize: 20, fontWeight: 900, letterSpacing: 4, color: '#F4E8CD' }}>许愿池</div>
        <div style={{ flex: 1 }} />
        <div style={{ fontFamily: mono, fontSize: 10, color: 'rgba(212,162,78,0.65)' }}>
          {pool?.total ?? 0} 愿在池中
        </div>
      </div>

      {/* 星空池面 */}
      <div style={{ position: 'relative', height: 300, marginTop: 4, overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: 18, right: 40, width: 52, height: 52, borderRadius: '50%', background: 'radial-gradient(circle at 42% 38%, #FBF2DC, #E9D6A4 70%, #DCC38A)', boxShadow: '0 0 44px 14px rgba(246,235,210,0.22)' }} />
        {[[34, 48], [74, 118], [22, 210], [96, 300]].map(([top, left], i) => (
          <div key={i} style={{ position: 'absolute', top, left, width: 2.5, height: 2.5, borderRadius: '50%', background: '#EFE6D0', animation: `tjTwinkle ${3 + i * 0.4}s ease-in-out infinite` }} />
        ))}
        <div style={{ position: 'absolute', left: 0, right: 0, top: 150, bottom: 0, background: 'linear-gradient(180deg, #1D2C3A 0%, #14202B 46%, #0F1820 100%)' }} />
        <div style={{ position: 'absolute', left: 0, right: 0, top: 149, height: 1, background: 'linear-gradient(90deg, transparent, rgba(212,162,78,0.35) 30%, rgba(244,232,205,0.5) 50%, rgba(212,162,78,0.35) 70%, transparent)' }} />

        {coin && (
          <div style={{ position: 'absolute', left: '50%', top: '68%', width: 20, height: 20, borderRadius: '50%', background: 'radial-gradient(circle at 35% 35%, #F2DA9C, #B8863B)', border: '2px solid #8A6428', boxShadow: '0 0 12px rgba(242,218,156,0.5)', animation: 'tjCoin 1.1s ease-in forwards' }} />
        )}

        {floating.map((w, i) => {
          const pos = FLOAT_POS[i % FLOAT_POS.length];
          return (
            <div key={w.id} style={{ position: 'absolute', left: pos.x, top: pos.y, animation: `tjDrift ${pos.dur} ease-in-out infinite` }}>
              <div style={{ animation: 'tjLantern 3s ease-in-out infinite', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 5 }}>
                <div style={{ width: 14, height: 16, borderRadius: '7px 7px 5px 5px', background: 'radial-gradient(circle at 50% 30%, #FFE9B0, #E8A94E 75%)', boxShadow: '0 0 14px 4px rgba(255,211,122,0.4)' }} />
                <div style={{ fontSize: 11, color: 'rgba(244,232,205,0.88)', letterSpacing: 1, whiteSpace: 'nowrap', textShadow: '0 0 10px rgba(255,211,122,0.4)' }}>{w.text}</div>
              </div>
            </div>
          );
        })}
        <div style={{ position: 'absolute', bottom: 8, left: 0, right: 0, textAlign: 'center', fontFamily: mono, fontSize: 9, color: 'rgba(228,213,180,0.38)', letterSpacing: 3 }}>
          众生的愿望正漂在池面 · 匿名
        </div>
      </div>

      {/* 投币 */}
      <div style={{ padding: '0 22px' }}>
        {writing ? (
          <div style={{ marginTop: 6, background: 'rgba(247,240,223,0.05)', border: '1px solid rgba(212,162,78,0.45)', borderRadius: 16, padding: 16, animation: 'tjDrop 0.3s ease-out' }}>
            <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: 2, color: '#F4E8CD' }}>写下心愿 · 随铜钱入池</div>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value.slice(0, 60))}
              autoFocus
              placeholder="例：十月考研，一战上岸"
              rows={2}
              style={{ width: '100%', boxSizing: 'border-box', marginTop: 12, border: '1px solid rgba(212,162,78,0.3)', background: 'rgba(11,15,23,0.6)', borderRadius: 12, padding: '11px 13px', fontSize: 14, color: '#F4E8CD', outline: 'none', resize: 'none' }}
            />
            <div style={{ display: 'flex', gap: 10, marginTop: 12 }}>
              <button className="tj-reset tj-clickable" onClick={toss} style={{ flex: 1, background: 'linear-gradient(180deg, #C9A053, #A87F35)', color: '#1A130A', textAlign: 'center', padding: 12, borderRadius: 12, fontWeight: 900, letterSpacing: 3 }}>投币许愿</button>
              <button className="tj-reset tj-clickable" onClick={() => { setWriting(false); setInput(''); }} style={{ padding: '12px 18px', border: '1px solid rgba(212,162,78,0.3)', color: 'rgba(228,213,180,0.6)', borderRadius: 12, background: 'transparent' }}>算了</button>
            </div>
          </div>
        ) : (
          <button
            className="tj-reset tj-clickable"
            onClick={() => requireAuth(() => setWriting(true))}
            style={{ width: '100%', marginTop: 6, background: 'linear-gradient(180deg, rgba(201,160,83,0.16), rgba(201,160,83,0.06))', border: '1px solid rgba(212,162,78,0.55)', color: '#E9D6A4', textAlign: 'center', padding: 15, borderRadius: 14, fontSize: 16, fontWeight: 700, letterSpacing: 4 }}
          >投一枚铜钱 · 许愿</button>
        )}

        {/* 我的愿 */}
        <div style={{ marginTop: 22, display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ flex: 1, height: 1, background: 'linear-gradient(90deg, transparent, rgba(212,162,78,0.4))' }} />
          <div style={{ fontSize: 12, color: 'rgba(212,162,78,0.8)', letterSpacing: 5 }}>吾 之 愿</div>
          <div style={{ flex: 1, height: 1, background: 'linear-gradient(90deg, rgba(212,162,78,0.4), transparent)' }} />
        </div>

        {(!pool || pool.mine.length === 0) && (
          <div style={{ marginTop: 16, textAlign: 'center', fontSize: 13, color: 'rgba(228,213,180,0.45)', lineHeight: 1.9 }}>
            {user ? '池中还没有你的愿望' : '登录后可查看你的愿望'}
            <br /><span style={{ fontFamily: mono, fontSize: 10 }}>先投一枚铜钱试试</span>
          </div>
        )}

        <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {pool?.mine.map((w) => (
            <div key={w.id} style={{ background: 'rgba(247,240,223,0.045)', border: '1px solid rgba(212,162,78,0.22)', borderRadius: 14, padding: '13px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{
                width: 34, height: 34, borderRadius: '50%', flexShrink: 0,
                background: w.status === 'fulfilled' ? 'rgba(111,161,115,0.12)' : 'rgba(166,27,41,0.12)',
                color: w.status === 'fulfilled' ? C.green : C.gold,
                border: `1px dashed ${w.status === 'fulfilled' ? C.green : 'rgba(212,162,78,0.6)'}`,
                display: 'grid', placeItems: 'center', fontWeight: 900, fontSize: 15,
              }}>{w.status === 'fulfilled' ? '还' : '愿'}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, fontWeight: 600, lineHeight: 1.6, color: '#F4E8CD' }}>{w.text}</div>
                <div style={{ fontFamily: mono, fontSize: 10, color: 'rgba(228,213,180,0.42)', marginTop: 3 }}>
                  {w.status === 'fulfilled'
                    ? '已应验还愿'
                    : w.moderation === 'rejected'
                    ? '未通过审核 · 仅自己可见'
                    : w.moderation === 'pending'
                    ? '审核中'
                    : '愿望进行中'}
                </div>
              </div>
              {w.status === 'active' && w.moderation === 'approved' && (
                <button className="tj-reset tj-clickable" onClick={() => fulfill(w.id)} style={{ fontSize: 12, border: '1px solid rgba(212,162,78,0.6)', color: '#E9D6A4', borderRadius: 999, padding: '6px 12px', fontWeight: 700, whiteSpace: 'nowrap', background: 'transparent' }}>应验了</button>
              )}
              {w.status === 'fulfilled' && (
                <div style={{ fontSize: 12, color: C.green, fontWeight: 700, whiteSpace: 'nowrap' }}>✓ 已还愿</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
