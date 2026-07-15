import { useEffect, useState } from 'react';
import { api, ApiError } from '../api/client';
import { useApp } from '../store/app';
import { C, mono } from '../theme/tokens';
import type { BaziChart } from '../shared';

const ELEMENT_COLOR: Record<string, string> = {
  金: '#C9A053', 木: '#6FA173', 水: '#4A7DA6', 火: '#A61B29', 土: '#A87F35',
};

export function Profile() {
  const { user, go, logout, openLogin, showToast } = useApp();
  const [chart, setChart] = useState<BaziChart | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ nickname: '', gender: 'female', birthDate: '', birthHour: '', birthPlace: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!user) return;
    api.getProfile().then((d) => {
      
      setChart(d.chart);
      if (d.profile) {
        setForm({
          nickname: user.nickname ?? '',
          gender: d.profile.gender,
          birthDate: d.profile.birthDate,
          birthHour: d.profile.birthHour === null ? '' : String(d.profile.birthHour),
          birthPlace: d.profile.birthPlace ?? '',
        });
      }
    }).catch(() => {});
  }, [user]);

  if (!user) {
    return (
      <div className="tj-body" style={{ padding: 20, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
        <div style={{ width: 62, height: 62, borderRadius: 12, background: C.ink, color: C.gold, display: 'grid', placeItems: 'center', fontSize: 28, fontWeight: 900, boxShadow: `3px 3px 0 ${C.accent}` }}>吾</div>
        <div style={{ fontSize: 16, color: C.sub }}>登录后查看你的命盘</div>
        <button className="tj-reset tj-clickable" onClick={openLogin} style={{ background: C.accent, color: C.creamText, padding: '12px 40px', borderRadius: 14, fontWeight: 700, letterSpacing: 3 }}>登录 · 入山门</button>
      </div>
    );
  }

  const save = async () => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(form.birthDate)) return showToast('请填写公历生日 YYYY-MM-DD');
    setSaving(true);
    try {
      const d = await api.saveProfile({
        nickname: form.nickname || undefined,
        gender: form.gender as 'male' | 'female',
        birthDate: form.birthDate,
        birthHour: form.birthHour === '' ? null : Number(form.birthHour),
        birthPlace: form.birthPlace || undefined,
      });
      
      setChart(d.chart);
      setEditing(false);
      showToast('命盘已更新');
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="tj-body" style={{ padding: '14px 20px 24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: 18, fontWeight: 900, letterSpacing: 1 }}>我的命盘</div>
        <button className="tj-reset" onClick={logout} style={{ fontSize: 12, color: C.muted }}>退出登录</button>
      </div>

      <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ width: 62, height: 62, borderRadius: 12, background: C.ink, color: C.gold, display: 'grid', placeItems: 'center', fontSize: 28, fontWeight: 900, boxShadow: `3px 3px 0 ${C.accent}` }}>
          {(user.nickname ?? '吾').slice(0, 1)}
        </div>
        <div>
          <div style={{ fontSize: 19, fontWeight: 900 }}>{user.nickname ?? '无名氏'}</div>
          <div style={{ fontFamily: mono, fontSize: 10, color: C.muted, marginTop: 2 }}>
            宿主编号 SU-{user.id.slice(0, 8).toUpperCase()} · {user.isLamp ? '长明灯亮' : '普通香客'}
          </div>
        </div>
      </div>

      {/* 八字命盘 */}
      {chart && !editing ? (
        <div style={{ marginTop: 16, background: C.dark, borderRadius: 16, padding: 18, color: C.cream }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <div style={{ fontSize: 13, color: C.goldSoft, letterSpacing: 2 }}>八字排盘 · {chart.zodiac}年生</div>
            <div style={{ fontFamily: mono, fontSize: 10, color: '#7A6E58' }}>{chart.lunarDate}</div>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 14, justifyContent: 'space-between' }}>
            {chart.pillars.map((p) => (
              <div key={p.label} style={{ flex: 1, textAlign: 'center', background: 'rgba(212,162,78,0.08)', borderRadius: 10, padding: '10px 0' }}>
                <div style={{ fontSize: 22, fontWeight: 900, color: C.creamText }}>{p.gan}</div>
                <div style={{ fontSize: 22, fontWeight: 900, color: C.gold }}>{p.zhi}</div>
                <div style={{ fontSize: 10, color: '#9C8E74', marginTop: 4 }}>{p.label}</div>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 6, marginTop: 14 }}>
            {Object.entries(chart.fiveElements).map(([el, n]) => (
              <div key={el} style={{ flex: 1, textAlign: 'center' }}>
                <div style={{ height: 5, background: '#3A332A', borderRadius: 999, overflow: 'hidden', marginBottom: 5 }}>
                  <div style={{ width: `${Math.min(100, n * 25)}%`, height: '100%', background: ELEMENT_COLOR[el], borderRadius: 999 }} />
                </div>
                <span style={{ fontSize: 11, color: '#C9BC9F' }}>{el} {n}</span>
              </div>
            ))}
          </div>
          <div style={{ fontSize: 13, color: '#C9BC9F', lineHeight: 1.9, marginTop: 14 }}>{chart.summary}</div>
          <button className="tj-reset tj-clickable" onClick={() => setEditing(true)} style={{ marginTop: 12, fontSize: 12, color: C.gold, border: `1px solid ${C.gold}`, borderRadius: 999, padding: '5px 14px', background: 'transparent' }}>修改生辰</button>
        </div>
      ) : (
        <div style={{ marginTop: 16, background: C.card, border: `1px solid ${C.line}`, borderRadius: 16, padding: 18 }}>
          <div style={{ fontSize: 15, fontWeight: 900 }}>{chart ? '修改生辰' : '补全生辰 · 一键排盘'}</div>
          <div style={{ fontSize: 12, color: C.muted, marginTop: 4 }}>真实干支四柱推演，非随机生成</div>
          <Field label="昵称"><input value={form.nickname} onChange={(e) => setForm({ ...form, nickname: e.target.value })} placeholder="怎么称呼你" style={inp} /></Field>
          <Field label="性别">
            <div style={{ display: 'flex', gap: 8 }}>
              {[['female', '女'], ['male', '男']].map(([v, l]) => (
                <button key={v} className="tj-reset tj-clickable" onClick={() => setForm({ ...form, gender: v })} style={{ flex: 1, padding: 10, borderRadius: 10, border: `1px solid ${form.gender === v ? C.accent : C.line}`, color: form.gender === v ? C.accent : C.sub, background: C.paper }}>{l}</button>
              ))}
            </div>
          </Field>
          <Field label="公历生日"><input value={form.birthDate} onChange={(e) => setForm({ ...form, birthDate: e.target.value })} placeholder="2003-07-13" style={inp} /></Field>
          <Field label="出生时辰（0-23，未知留空）"><input value={form.birthHour} onChange={(e) => setForm({ ...form, birthHour: e.target.value.replace(/\D/g, '').slice(0, 2) })} inputMode="numeric" placeholder="12" style={inp} /></Field>
          <Field label="出生地"><input value={form.birthPlace} onChange={(e) => setForm({ ...form, birthPlace: e.target.value })} placeholder="浙江 · 杭州" style={inp} /></Field>
          <button className="tj-reset tj-clickable" onClick={save} disabled={saving} style={{ width: '100%', marginTop: 16, background: C.accent, color: C.creamText, padding: 14, borderRadius: 12, fontWeight: 700, letterSpacing: 3 }}>{saving ? '排盘中…' : '一键排盘'}</button>
        </div>
      )}

      {/* 供灯入口 */}
      <div className="tj-clickable" onClick={() => go('vip')} style={{ marginTop: 16, background: C.dark, borderRadius: 16, padding: '16px 18px', display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ width: 40, height: 40, borderRadius: '50%', border: `1.5px solid ${C.gold}`, color: C.gold, display: 'grid', placeItems: 'center', fontWeight: 900, fontSize: 18 }}>机</div>
        <div style={{ flex: 1 }}>
          <div style={{ color: C.gold, fontWeight: 900, fontSize: 15, letterSpacing: 2 }}>供一盏长明灯</div>
          <div style={{ color: '#9C8E74', fontSize: 12, marginTop: 2 }}>{user.isLamp ? '灯已亮 · 权益生效中' : '解锁无限追问 + 每日灯语'}</div>
        </div>
        <div style={{ color: C.gold }}>→</div>
      </div>

      <div style={{ marginTop: 18, textAlign: 'center', fontFamily: mono, fontSize: 10, color: C.faint, lineHeight: 2 }}>
        赛博天机 v3.0 · 传统文化娱乐 & 心理疗愈<br />本应用不提供命运修改服务，只提供勇气补给
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontSize: 12, color: C.muted, marginBottom: 6 }}>{label}</div>
      {children}
    </div>
  );
}

const inp: React.CSSProperties = {
  width: '100%', boxSizing: 'border-box', border: `1px solid ${C.line}`, background: C.paper,
  borderRadius: 10, padding: '11px 13px', fontSize: 14, color: C.ink, outline: 'none',
};
