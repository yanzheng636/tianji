import { useApp } from '../store/app';
import { TopBar } from '../components/ui';
import { C, mono } from '../theme/tokens';

const ACTIONS: Record<string, { icon: string; label: string; sub: string; act: string }[]> = {
  wenshu: [
    { icon: '香', label: '上一炷香', sub: '心愿实时燃烧 30 分钟', act: 'incense' },
    { icon: '签', label: '求一支考运签', sub: '摇签筒 · 问上岸', act: 'qian' },
    { icon: '问', label: '问考运', sub: '天机子推演上岸窗口期', act: 'chat:我今年能上岸吗' },
  ],
  yuelao: [
    { icon: '香', label: '上一炷香', sub: '心愿实时燃烧 30 分钟', act: 'incense' },
    { icon: '签', label: '求一支姻缘签', sub: '摇签筒 · 问缘分', act: 'qian' },
    { icon: '问', label: '问姻缘', sub: '天机子检索感情线', act: 'chat:我的姻缘什么时候来' },
  ],
  caishen: [
    { icon: '香', label: '上一炷香', sub: '心愿实时燃烧 30 分钟', act: 'incense' },
    { icon: '签', label: '求一支财运签', sub: '摇签筒 · 问财路', act: 'qian' },
    { icon: '问', label: '问财运', sub: '正财偏财信号检测', act: 'chat:今年财运如何' },
    { icon: '仕', label: '问事业', sub: '跳槽/晋升 · 官禄宫推演', act: 'chat:我该不该跳槽' },
  ],
  tianji: [
    { icon: '香', label: '上一炷香', sub: '心愿实时燃烧 30 分钟', act: 'incense' },
    { icon: '掌', label: '手相扫描', sub: '需摄像头授权 · 敬请期待', act: 'palm' },
    { icon: '命', label: '八字排盘', sub: '生辰一键起盘', act: 'profile' },
  ],
  qianfang: [
    { icon: '签', label: '摇一支签', sub: '心中默念所问之事', act: 'qian' },
    { icon: '问', label: '找大师问卦', sub: '天机子在线 · 引经据典', act: 'chat:' },
  ],
};

export function Hall() {
  const { nav, go, config } = useApp();
  const key = nav.hallKey ?? 'wenshu';
  const hall = config?.halls.find((h) => h.key === key);
  const actions = ACTIONS[key] ?? [];

  const doAct = (act: string) => {
    if (act === 'incense') go('incense');
    else if (act === 'qian') go('qian', { hallKey: key });
    else if (act === 'palm') go('palm');
    else if (act === 'profile') go('profile');
    else if (act.startsWith('chat:')) go('chat', { chatPreset: act.slice(5) || undefined });
  };

  return (
    <div className="tj-body" style={{ paddingBottom: 24 }}>
      <TopBar title={hall?.name ?? '殿内'} code={hall?.code} onBack={() => go('home')} />

      <div style={{ padding: '0 20px' }}>
        <div style={{
          marginTop: 16, background: C.dark, borderRadius: 18, padding: '26px 20px',
          textAlign: 'center', position: 'relative', overflow: 'hidden',
        }}>
          <div style={{ position: 'absolute', inset: 10, border: '1px solid rgba(212,162,78,0.25)', borderRadius: 12 }} />
          <div style={{
            width: 72, height: 72, margin: '0 auto', borderRadius: '50%', border: `2px solid ${C.gold}`,
            color: C.gold, display: 'grid', placeItems: 'center', fontWeight: 900, fontSize: 34,
          }}>{hall?.char}</div>
          <div style={{ color: C.cream, fontSize: 20, fontWeight: 900, letterSpacing: 4, marginTop: 14 }}>{hall?.deity}</div>
          <div style={{ fontFamily: mono, fontSize: 10, color: '#9C8E74', marginTop: 6 }}>{hall?.sub}</div>
          <div style={{ fontSize: 13, color: '#C9BC9F', lineHeight: 1.9, marginTop: 12 }}>{hall?.desc}</div>
        </div>

        <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {actions.map((a, i) => (
            <div
              key={i}
              className="tj-clickable"
              onClick={() => doAct(a.act)}
              style={{
                background: C.card, border: `1px solid ${C.line}`, borderRadius: 14,
                padding: '15px 16px', display: 'flex', alignItems: 'center', gap: 12,
              }}
            >
              <div style={{
                width: 38, height: 38, borderRadius: 8, background: C.cream,
                display: 'grid', placeItems: 'center', fontWeight: 900, fontSize: 18, color: C.accent,
              }}>{a.icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 15 }}>{a.label}</div>
                <div style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>{a.sub}</div>
              </div>
              <div style={{ color: C.accent }}>→</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
