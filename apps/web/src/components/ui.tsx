import type { ReactNode } from 'react';
import { useApp, type Screen } from '../store/app';
import { C, mono } from '../theme/tokens';

export function TopBar({
  title,
  code,
  onBack,
  right,
}: {
  title: string;
  code?: string;
  onBack?: () => void;
  right?: ReactNode;
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 20px 0' }}>
      {onBack && (
        <button
          className="tj-reset tj-clickable"
          onClick={onBack}
          style={{
            width: 34, height: 34, border: `1px solid ${C.line}`, borderRadius: '50%',
            display: 'grid', placeItems: 'center', fontSize: 16, flexShrink: 0,
          }}
        >
          ←
        </button>
      )}
      <div style={{ flex: 1, fontSize: 18, fontWeight: 900, letterSpacing: 2 }}>{title}</div>
      {code ? (
        <div style={{ fontFamily: mono, fontSize: 10, color: C.muted }}>{code}</div>
      ) : (
        right
      )}
    </div>
  );
}

const TABS: { screen: Screen; char: string; label: string }[] = [
  { screen: 'home', char: '寺', label: '山门' },
  { screen: 'wish', char: '愿', label: '许愿池' },
  { screen: 'chat', char: '卦', label: '问卦' },
  { screen: 'profile', char: '吾', label: '我的' },
];

export function TabBar() {
  const { nav, go } = useApp();
  return (
    <div
      style={{
        display: 'flex', borderTop: `1px solid ${C.lineSoft}`,
        background: C.paper, padding: '8px 10px 6px', flexShrink: 0,
      }}
    >
      {TABS.map((t) => {
        const active = nav.screen === t.screen;
        const color = active ? C.accent : C.muted;
        return (
          <button
            key={t.screen}
            className="tj-reset"
            onClick={() => go(t.screen)}
            style={{ flex: 1, textAlign: 'center', padding: '6px 0' }}
          >
            <div style={{ fontSize: 18, fontWeight: 900, color }}>{t.char}</div>
            <div style={{ fontSize: 10, color, marginTop: 2 }}>{t.label}</div>
          </button>
        );
      })}
    </div>
  );
}

export function Toast() {
  const toast = useApp((s) => s.toast);
  if (!toast) return null;
  return (
    <div
      style={{
        position: 'absolute', bottom: 96, left: '50%', transform: 'translateX(-50%)',
        background: C.ink, color: C.cream, fontSize: 13, padding: '10px 18px',
        borderRadius: 999, whiteSpace: 'nowrap', maxWidth: '86%',
        boxShadow: '0 6px 20px rgba(0,0,0,0.25)', zIndex: 80, textAlign: 'center',
      }}
    >
      {toast}
    </div>
  );
}

/** 待校残本的诚实标注：不把网络竖排 OCR 底本包装成可靠证据。 */
export function QualityTag({ quality }: { quality: string }) {
  if (quality === 'verified') return null;
  return (
    <span
      style={{
        fontSize: 9, color: C.goldSoft, border: `1px solid ${C.line}`,
        borderRadius: 4, padding: '1px 5px', flexShrink: 0, whiteSpace: 'nowrap',
      }}
    >
      竖排OCR · 待校
    </span>
  );
}

export function Loading() {
  return (
    <div style={{ flex: 1, display: 'grid', placeItems: 'center' }}>
      <div className="tj-spin" />
    </div>
  );
}

export function Disclaimer({ text }: { text: string }) {
  return (
    <div
      style={{
        margin: '16px 20px 0', textAlign: 'center', fontFamily: mono,
        fontSize: 10, color: C.faint, lineHeight: 1.8,
      }}
    >
      {text}
    </div>
  );
}
