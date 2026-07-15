import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../api';
import { useTianji } from '../App';
import type { BaziChart } from '../types';

const elementColor: Record<string, string> = { 金: '#b79a5c', 木: '#557c62', 水: '#426c80', 火: '#a64b36', 土: '#8e7046' };

export function Profile() {
  const { user, refreshUser } = useTianji();
  const [chart, setChart] = useState<BaziChart | null>(null);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({ nickname: user?.nickname ?? '山中访客', gender: 'female', birthDate: '', birthHour: '', birthPlace: '' });
  useEffect(() => { void api.getProfile().then((data) => { setChart(data.chart); if (data.profile) setForm((value) => ({ ...value, gender: data.profile!.gender, birthDate: data.profile!.birthDate, birthHour: data.profile!.birthHour === null ? '' : String(data.profile!.birthHour), birthPlace: data.profile!.birthPlace ?? '' })); }).catch(() => undefined); }, []);
  const save = async () => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(form.birthDate)) { setError('请按 YYYY-MM-DD 填写公历生日'); return; }
    setBusy(true); setError('');
    try { const data = await api.saveProfile({ nickname: form.nickname, gender: form.gender as 'female' | 'male', birthDate: form.birthDate, birthHour: form.birthHour ? Number(form.birthHour) : null, birthPlace: form.birthPlace || null }); setChart(data.chart); setEditing(false); await refreshUser(); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : '命盘暂未排成'); }
    finally { setBusy(false); }
  };
  return (
    <div className="inner-page profile-page">
      <header className="profile-hero"><div className="profile-avatar">{user?.nickname?.slice(0, 1) ?? '吾'}</div><div><p className="eyebrow">我的居所 · 不设手机号</p><h1>{user?.nickname ?? '山中访客'}</h1><small>访客身份会保存在当前浏览器 · 记录由寺中服务器保管</small></div><Link to="/lamp" className="profile-lamp"><i />{user?.isLamp ? '长明灯已亮' : '供一盏长明灯'}<span>→</span></Link></header>
      <div className="content-wrap profile-layout">
        <aside className="profile-nav"><p className="aside-label">我的居所</p><a className="active">命盘总览</a><Link to="/qian">我的签文</Link><Link to="/wishes">我的愿望</Link><Link to="/chat">问卦记录</Link><Link to="/palm">手相观照</Link></aside>
        <section>
          {chart && !editing ? <div className="chart-panel"><div className="chart-head"><div><p className="eyebrow">四柱排盘 · {chart.zodiac}年生</p><h2>日主 <span>{chart.dayMaster}</span></h2></div><button className="outline-button" onClick={() => setEditing(true)}>修改生辰</button></div><div className="pillars">{chart.pillars.map((pillar) => <article key={pillar.label}><small>{pillar.label}</small><b>{pillar.gan}</b><strong>{pillar.zhi}</strong></article>)}</div><div className="elements">{Object.entries(chart.fiveElements).map(([element, count]) => <div key={element}><span>{element}</span><i><em style={{ width: `${Math.min(100, count * 25)}%`, background: elementColor[element] }} /></i><small>{count}</small></div>)}</div><p className="chart-summary">{chart.summary}</p><small className="chart-note">{chart.lunarDate} · {chart.solarTermsNote}</small></div> : <ProfileForm form={form} setForm={setForm} save={save} busy={busy} error={error} hasChart={Boolean(chart)} />}
          <div className="profile-cards"><Link to="/qian"><span>签</span><div><small>我的签文</small><b>回看曾经照见的念头</b></div><i>→</i></Link><Link to="/chat"><span>问</span><div><small>问卦记录</small><b>继续未说完的对谈</b></div><i>→</i></Link><Link to="/wishes"><span>愿</span><div><small>我的愿望</small><b>看看正在走近的事情</b></div><i>→</i></Link></div>
        </section>
      </div>
    </div>
  );
}

interface FormValue { nickname: string; gender: string; birthDate: string; birthHour: string; birthPlace: string }
function ProfileForm({ form, setForm, save, busy, error, hasChart }: { form: FormValue; setForm: (form: FormValue) => void; save: () => void; busy: boolean; error: string; hasChart: boolean }) {
  return <div className="profile-form paper-panel"><div><p className="eyebrow dark">{hasChart ? '修改生辰' : '补全生辰 · 一键排盘'}</p><h2>{hasChart ? '重新校准你的命盘' : '先认识此刻的自己'}</h2><p>四柱依据公历生辰推演。它提供传统文化视角，不定义你的性格与未来。</p></div><div className="form-grid"><label>怎么称呼你<input className="field" value={form.nickname} onChange={(e) => setForm({ ...form, nickname: e.target.value })} /></label><label>性别<select className="field" value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}><option value="female">女</option><option value="male">男</option></select></label><label>公历生日<input className="field" value={form.birthDate} onChange={(e) => setForm({ ...form, birthDate: e.target.value })} placeholder="1995-08-16" /></label><label>出生时辰<input className="field" value={form.birthHour} onChange={(e) => setForm({ ...form, birthHour: e.target.value.replace(/\D/g, '').slice(0, 2) })} placeholder="未知可留空" /></label><label className="full">出生地<input className="field" value={form.birthPlace} onChange={(e) => setForm({ ...form, birthPlace: e.target.value })} placeholder="浙江 · 杭州" /></label><button className="primary-button full" onClick={save} disabled={busy}>{busy ? '正在排盘…' : '排出我的命盘'}</button>{error ? <p className="form-error full">{error}</p> : null}</div></div>;
}
