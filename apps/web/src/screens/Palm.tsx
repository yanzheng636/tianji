import { useApp } from '../store/app';
import { TopBar } from '../components/ui';
import { C, mono } from '../theme/tokens';

// 手相扫描：掌纹属敏感生物识别信息，需单独授权 + 真实视觉模型。
// 诚实做法——不伪造分析结果，展示为「需授权 · 接入中」，避免误导。
export function Palm() {
  const { go } = useApp();
  return (
    <div className="tj-body" style={{ paddingBottom: 24, display: 'flex', flexDirection: 'column' }}>
      <TopBar title="手相扫描" code="PALM-SCAN v3.1" onBack={() => go('home')} />
      <div style={{ padding: '0 20px' }}>
        <div style={{
          marginTop: 16, position: 'relative', borderRadius: 18, overflow: 'hidden',
          background: 'repeating-linear-gradient(45deg, #2A251E 0 12px, #241F19 12px 24px)', height: 360,
        }}>
          <div style={{ position: 'absolute', top: 14, left: 14, width: 26, height: 26, borderTop: `2.5px solid ${C.gold}`, borderLeft: `2.5px solid ${C.gold}` }} />
          <div style={{ position: 'absolute', top: 14, right: 14, width: 26, height: 26, borderTop: `2.5px solid ${C.gold}`, borderRight: `2.5px solid ${C.gold}` }} />
          <div style={{ position: 'absolute', bottom: 14, left: 14, width: 26, height: 26, borderBottom: `2.5px solid ${C.gold}`, borderLeft: `2.5px solid ${C.gold}` }} />
          <div style={{ position: 'absolute', bottom: 14, right: 14, width: 26, height: 26, borderBottom: `2.5px solid ${C.gold}`, borderRight: `2.5px solid ${C.gold}` }} />
          <div style={{ position: 'absolute', left: 0, right: 0, top: '20%', height: 3, background: `linear-gradient(90deg, transparent, ${C.accent}, ${C.gold}, ${C.accent}, transparent)`, boxShadow: '0 0 18px 4px rgba(166,27,41,0.4)', animation: 'tjBlink 2s ease-in-out infinite' }} />
          <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center' }}>
            <div style={{ textAlign: 'center', color: '#9C8E74', fontFamily: mono, fontSize: 12, lineHeight: 2 }}>
              [ 掌纹识别 · 敬请期待 ]<br />将手掌完整置于取景框内<br />掌心朝上 · 光线充足
            </div>
          </div>
        </div>

        <div style={{ marginTop: 14, background: C.cardWarm, border: '1px solid #D9CBA6', borderRadius: 12, padding: '14px 16px', fontSize: 13, color: C.sub, lineHeight: 1.9 }}>
          <span style={{ color: C.accent, fontWeight: 700 }}>关于手相扫描：</span>
          掌纹属于敏感生物识别信息。上线前需接入摄像头授权、单独的隐私同意，且掌纹图像
          <b>即用即弃、不留原图</b>。真实视觉模型接入后开放，当前版本先以八字排盘为你解读本命。
        </div>

        <button
          className="tj-reset tj-clickable"
          onClick={() => go('profile')}
          style={{ width: '100%', marginTop: 16, background: C.accent, color: C.creamText, textAlign: 'center', padding: 15, borderRadius: 14, fontSize: 16, fontWeight: 700, letterSpacing: 3 }}
        >先去八字排盘 ▸</button>
      </div>
    </div>
  );
}
