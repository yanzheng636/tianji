import { useState } from 'react';
import { api, ApiError } from '../api';
import { useTianji } from '../App';

const fallbackPlans = [
  { key: 'month', name: '一月灯', priceFen: 1900, days: 30, recommended: false },
  { key: 'year', name: '一年灯', priceFen: 9900, days: 365, recommended: true },
  { key: 'forever', name: '长明灯', priceFen: 29900, days: null, recommended: false },
];

export function Lamp() {
  const { config, refreshUser } = useTianji();
  const plans = config?.lampPlans?.length ? config.lampPlans : fallbackPlans;
  const [selected, setSelected] = useState(plans.find((plan) => plan.recommended)?.key ?? plans[0].key);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const pay = async () => {
    setBusy(true); setNotice('');
    try {
      const order = await api.createOrder({ kind: 'lamp', plan: selected });
      setNotice(`灯火订单已建立 · ${order.status === 'paid' ? '长明灯已亮' : '正在确认供灯状态'}`);
      if (order.status !== 'paid') window.setTimeout(() => { void api.getOrder(order.orderId).then(async (next) => { setNotice(next.status === 'paid' ? '长明灯已亮，权益已生效' : '订单仍在确认中，可稍后再看'); if (next.status === 'paid') await refreshUser(); }); }, 3200);
      else await refreshUser();
    } catch (error) { setNotice(error instanceof ApiError ? error.message : '此刻暂未能点亮，请稍后再试'); }
    finally { setBusy(false); }
  };
  return (
    <div className="inner-page lamp-page">
      <section className="lamp-hero"><div className="lamp-illustration"><i className="lamp-flame" /><span className="lamp-frame">天<br />机</span></div><div><p className="eyebrow">不是许愿交换 · 是给长期陪伴留一盏灯</p><h1>供一盏<br />长明灯</h1><p>解锁更多问卦追问、每日灯语与完整记录。灯火代表陪伴，不承诺改变命运。</p></div></section>
      <div className="content-wrap lamp-content"><div className="lamp-benefits"><p className="aside-label">灯下所得</p><h2 className="section-title">更从容地问，更完整地看</h2><div><article><span>问</span><b>更多深度追问</b><p>在一次对谈中把问题说完整，不被中途打断。</p></article><article><span>卷</span><b>古籍旁证展开</b><p>查看更多引用原文、现代释义与上下文。</p></article><article><span>记</span><b>完整心路记录</b><p>保留问卦、签文、愿望与灯语，随时回看。</p></article></div></div><section className="lamp-plans paper-panel"><p className="aside-label">择一盏灯</p>{plans.map((plan) => <button key={plan.key} onClick={() => setSelected(plan.key)} className={selected === plan.key ? 'active' : ''}><span>{selected === plan.key ? '●' : '○'}</span><div><b>{plan.name}</b><small>{plan.days ? `${plan.days} 日陪伴` : '长期陪伴'}</small></div><strong>¥{(plan.priceFen / 100).toFixed(0)}</strong>{plan.recommended ? <em>合宜</em> : null}</button>)}<button className="primary-button wide" onClick={pay} disabled={busy}>{busy ? '正在点灯…' : '确认供灯'}</button>{notice ? <p className="lamp-notice">{notice}</p> : null}<small>支付与权益状态由服务端确认。供灯不包含任何改运或结果承诺。</small></section></div>
    </div>
  );
}
