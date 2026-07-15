import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useApp } from '../store/app';
import { C, mono } from '../theme/tokens';
import type { TodayFortune } from '../shared';

const HALL_CARDS = [
  { key: 'wenshu', char: '文', name: '文殊殿', sub: '升学 · 考试 · 智慧' },
  { key: 'yuelao', char: '缘', name: '月老祠', sub: '姻缘 · 感情 · 桃花' },
  { key: 'caishen', char: '财', name: '财神殿', sub: '财运 · 事业 · 偏财' },
  { key: 'tianji', char: '机', name: '天机殿', sub: '手相 · 八字 · 本命' },
];

export function Home() {
  const { go, user } = useApp();
  const [today, setToday] = useState<TodayFortune | null>(null);

  useEffect(() => {
    api.today().then(setToday).catch(() => {});
  }, []);

  const luck = today?.luck ?? 87;

  return (
    <div className="tj-body" style={{ padding: '14px 20px 20px' }}>
      {/* 顶栏 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{
          width: 44, height: 44, background: C.accent, color: C.creamText,
          display: 'grid', placeItems: 'center', fontSize: 24, fontWeight: 900,
          borderRadius: 8, boxShadow: `2px 2px 0 ${C.ink}`,
        }}>机</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 22, fontWeight: 900, letterSpacing: 2 }}>赛博天机寺</div>
          <div style={{ fontFamily: mono, fontSize: 10, color: C.muted, letterSpacing: 1 }}>
            SPIRITUAL LINK · {user ? '已入山门' : '游客参访'} · v3.0
          </div>
        </div>
        <div style={{
          fontFamily: mono, fontSize: 10, color: C.accent,
          border: `1px solid ${C.accent}`, borderRadius: 999, padding: '4px 10px',
        }}>灵力 ▮▮▮▮▯</div>
      </div>

      {/* 今日运势 */}
      <div style={{ marginTop: 18, background: C.dark, borderRadius: 16, padding: '18px 18px 16px', color: C.cream }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <div style={{ fontSize: 13, color: C.goldSoft, letterSpacing: 2 }}>
            今日运势 · {today?.ganzhi ?? '——'}
          </div>
          <div style={{ fontFamily: mono, fontSize: 10, color: '#7A6E58' }}>{today?.date ?? ''}</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginTop: 10 }}>
          <div style={{ fontFamily: mono, fontSize: 44, fontWeight: 600, color: C.creamText, lineHeight: 1 }}>
            {luck}<span style={{ fontSize: 18, color: C.goldSoft }}>%</span>
          </div>
          <div style={{ fontFamily: mono, fontSize: 11, color: C.goldSoft }}>运势已加载 {luck}%</div>
        </div>
        <div style={{ marginTop: 12, height: 6, background: '#3A332A', borderRadius: 999, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${luck}%`, background: `linear-gradient(90deg, ${C.accent}, ${C.gold})`, borderRadius: 999 }} />
        </div>
        <div style={{ display: 'flex', gap: 18, marginTop: 14, fontSize: 13, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ color: C.green, fontWeight: 700 }}>宜</span>
            <span style={{ color: '#D9CFB8' }}>{(today?.yi ?? ['摸鱼充电']).join(' · ')}</span>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ color: C.danger, fontWeight: 700 }}>忌</span>
            <span style={{ color: '#D9CFB8' }}>{(today?.ji ?? ['精神内耗']).join(' · ')}</span>
          </div>
        </div>
      </div>

      {/* 摇签 CTA */}
      <div
        className="tj-clickable"
        onClick={() => go('qian', { hallKey: 'qianfang' })}
        style={{
          marginTop: 16, background: C.card, border: `1.5px solid ${C.accent}`,
          borderRadius: 16, padding: 18, display: 'flex', alignItems: 'center', gap: 16,
          animation: 'tjPulse 3s ease-in-out infinite',
        }}
      >
        <div style={{
          width: 56, height: 56, borderRadius: '50%', background: 'rgba(166,27,41,0.08)',
          border: `1px dashed ${C.accent}`, display: 'grid', placeItems: 'center',
          fontSize: 28, fontWeight: 900, color: C.accent,
        }}>签</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 18, fontWeight: 900, letterSpacing: 1 }}>摇签问事</div>
          <div style={{ fontSize: 12, color: C.muted, marginTop: 3 }}>手机一摇，天机自现 · AI 大师在线解签</div>
        </div>
        <div style={{ color: C.accent, fontSize: 20 }}>→</div>
      </div>

      {/* 灵境四殿 */}
      <div style={{ marginTop: 18, display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ flex: 1, height: 1, background: C.line }} />
        <div style={{ fontSize: 12, color: C.muted, letterSpacing: 4 }}>灵 境 四 殿</div>
        <div style={{ flex: 1, height: 1, background: C.line }} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 12 }}>
        {HALL_CARDS.map((h) => (
          <div
            key={h.key}
            className="tj-clickable"
            onClick={() => go('hall', { hallKey: h.key })}
            style={{
              background: C.card, border: `1px solid ${C.line}`, borderTop: `4px solid ${C.accent}`,
              borderRadius: 14, padding: '16px 14px', textAlign: 'center',
            }}
          >
            <div style={{
              width: 46, height: 46, margin: '0 auto', borderRadius: '50%', background: C.ink,
              color: C.gold, display: 'grid', placeItems: 'center', fontWeight: 900, fontSize: 22,
            }}>{h.char}</div>
            <div style={{ fontWeight: 900, fontSize: 16, marginTop: 10, letterSpacing: 2 }}>{h.name}</div>
            <div style={{ fontSize: 11, color: C.muted, marginTop: 4 }}>{h.sub}</div>
          </div>
        ))}
      </div>

      {/* 藏经阁 */}
      <div
        className="tj-clickable"
        onClick={() => go('library')}
        style={{
          marginTop: 12, background: C.dark, borderRadius: 14, padding: '13px 16px',
          display: 'flex', alignItems: 'center', gap: 12,
        }}
      >
        <div style={{
          width: 34, height: 34, borderRadius: 6, border: `1px solid ${C.gold}`,
          color: C.gold, display: 'grid', placeItems: 'center', fontWeight: 900, fontSize: 16,
        }}>经</div>
        <div style={{ flex: 1 }}>
          <div style={{ color: C.gold, fontWeight: 900, fontSize: 14, letterSpacing: 2 }}>藏经阁</div>
          <div style={{ color: '#9C8E74', fontSize: 11, marginTop: 1 }}>古籍原文可溯源 · 大师引用皆有据</div>
        </div>
        <div style={{ color: C.gold, fontSize: 15 }}>→</div>
      </div>

      <div style={{ marginTop: 16, textAlign: 'center', fontFamily: mono, fontSize: 10, color: C.faint }}>
        * 结果仅供心灵慰藉 · 人生 bug 请自行修复
      </div>
    </div>
  );
}
