import { useState } from 'react';
import { api, ApiError } from '../api';
import { useTianji } from '../App';

const fallbackPlans = [
  { key: 'month', name: '一月灯', priceFen: 1900, days: 30, recommended: false },
  { key: 'year', name: '一年灯', priceFen: 9900, days: 365, recommended: true },
  { key: 'forever', name: '长明灯', priceFen: 29900, days: null, recommended: false },
];

const benefits = [
  ['问', '更多深度追问', '在一次对谈中把问题说完整，不被中途打断。'],
  ['卷', '古籍旁证展开', '查看更多引用原文、现代释义与上下文。'],
  ['记', '完整心路记录', '保留问答、签录与愿望，随时回看。'],
] as const;

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
      setNotice(`订单已建立 · ${order.status === 'paid' ? '长明已生效' : '正在确认状态'}`);
      if (order.status !== 'paid') window.setTimeout(() => { void api.getOrder(order.orderId).then(async (next) => { setNotice(next.status === 'paid' ? '长明已生效' : '订单仍在确认中，可稍后再看'); if (next.status === 'paid') await refreshUser(); }); }, 3200);
      else await refreshUser();
    } catch (error) { setNotice(error instanceof ApiError ? error.message : '此刻未能建立订单，请稍后再试'); }
    finally { setBusy(false); }
  };

  return (
    <div className="membership-page">
      <header className="membership-hero">
        <div className="membership-glow" aria-hidden="true"><i /></div>
        <div className="membership-copy"><p className="museum-label"><span>长明</span><i />持续陪伴</p><h1>留一盏灯，<br />给未说完的话。</h1><p>获得更完整的问答、古籍旁证与个人记录。长明代表持续陪伴，不承诺改变结果。</p></div>
        <div className="membership-statement"><span>山问原则</span><p>不夸大<br />不宿命<br />有出处</p></div>
      </header>

      <div className="membership-body">
        <section className="membership-benefits">
          <p className="museum-label dark"><span>灯下所得</span><i />三件事</p>
          <h2>更从容地问，<br />更完整地看。</h2>
          <div>{benefits.map(([mark, title, body]) => <article key={mark}><span>{mark}</span><div><b>{title}</b><p>{body}</p></div></article>)}</div>
        </section>

        <section className="membership-plans">
          <div className="membership-plans-head"><span>选择陪伴时间</span><small>随时可查看状态</small></div>
          {plans.map((plan) => (
            <button key={plan.key} onClick={() => setSelected(plan.key)} className={selected === plan.key ? 'active' : ''}>
              <span>{selected === plan.key ? '●' : '○'}</span><div><b>{plan.name}</b><small>{plan.days ? `${plan.days} 日` : '长期'}</small></div><strong><em>¥</em>{(plan.priceFen / 100).toFixed(0)}</strong>{plan.recommended ? <i>合宜</i> : null}
            </button>
          ))}
          <button className="membership-confirm" onClick={pay} disabled={busy}>{busy ? '正在确认…' : '确认选择'}<span>→</span></button>
          {notice ? <p className="membership-notice" role="status">{notice}</p> : null}
          <small>支付与权益状态由服务端确认，不包含任何改运或结果承诺。</small>
        </section>
      </div>
    </div>
  );
}
