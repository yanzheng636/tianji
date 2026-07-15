import { useState } from 'react';
import { api, ApiError } from '../api/client';
import { useApp } from '../store/app';
import { TopBar } from '../components/ui';
import { C, mono } from '../theme/tokens';
import { yuan } from '../shared';

const BENEFITS = [
  ['灯', '灯亮期间 · 每日灯语 + 运势推送'],
  ['卷', '深度命盘报告 · 八字/紫微双引擎'],
  ['问', '大师无限追问 · 不限次数'],
  ['典', '古籍原文全文引用 · 逐句白话对照'],
];

export function Vip() {
  const { go, config, user, requireAuth, showToast, refreshUser } = useApp();
  const [plan, setPlan] = useState('year');
  const [paying, setPaying] = useState(false);
  const plans = config?.lampPlans ?? [];

  const pay = () => {
    requireAuth(async () => {
      setPaying(true);
      try {
        const order = await api.createOrder({ kind: 'lamp', plan });
        showToast('订单已创建，等待支付…');
        // 轮询订单状态（mock 会在几秒后自动成功；真支付由用户在收银台完成后回调）
        const poll = async (tries: number): Promise<void> => {
          if (tries <= 0) {
            setPaying(false);
            showToast('支付超时，请在「我的」中查看订单');
            return;
          }
          const o = await api.getOrder(order.orderId);
          if (o.status === 'paid') {
            setPaying(false);
            await refreshUser();
            showToast('供灯成功 · 长明灯已为你点亮');
            return;
          }
          if (o.status === 'failed') {
            setPaying(false);
            showToast('支付失败');
            return;
          }
          setTimeout(() => poll(tries - 1), 1200);
        };
        poll(15);
      } catch (e) {
        setPaying(false);
        showToast(e instanceof ApiError ? e.message : '下单失败');
      }
    });
  };

  return (
    <div className="tj-body" style={{ paddingBottom: 24 }}>
      <TopBar title="供灯" code="LAMP · 长明" onBack={() => go('profile')} />
      <div style={{ padding: '0 20px' }}>
        <div style={{ marginTop: 16, background: C.dark, borderRadius: 18, padding: '24px 20px 20px', textAlign: 'center' }}>
          <div style={{ position: 'relative', width: 70, height: 84, margin: '0 auto' }}>
            <div style={{ position: 'absolute', bottom: 34, left: '50%', transform: 'translateX(-50%)', width: 22, height: 32, background: 'radial-gradient(ellipse at 50% 80%, #FFD37A 0%, #F0A03C 55%, rgba(240,160,60,0) 75%)', borderRadius: '50% 50% 45% 45% / 70% 70% 30% 30%', animation: 'tjFlame 1.4s ease-in-out infinite', transformOrigin: '50% 100%', opacity: user?.isLamp ? 1 : 0.85 }} />
            <div style={{ position: 'absolute', bottom: 26, left: '50%', transform: 'translateX(-50%)', width: 8, height: 10, background: '#3A332A', borderRadius: 2 }} />
            <div style={{ position: 'absolute', bottom: 12, left: '50%', transform: 'translateX(-50%)', width: 62, height: 18, background: 'linear-gradient(180deg, #B08D4A, #7A5E2E)', borderRadius: '8px 8px 30px 30px' }} />
          </div>
          <div style={{ fontSize: 24, fontWeight: 900, color: C.gold, letterSpacing: 4, marginTop: 10 }}>
            {user?.isLamp ? '灯已长明' : '供一盏灯'}
          </div>
          <div style={{ fontFamily: mono, fontSize: 11, color: '#9C8E74', marginTop: 8 }}>灯在，愿就在 · 每天为你亮着</div>
        </div>

        <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 9 }}>
          {BENEFITS.map(([c, t]) => (
            <div key={c} style={{ display: 'flex', gap: 10, alignItems: 'center', background: C.card, border: `1px solid ${C.line}`, borderRadius: 12, padding: '12px 14px' }}>
              <span style={{ color: C.accent, fontWeight: 900 }}>{c}</span>
              <span style={{ fontSize: 13 }}>{t}</span>
            </div>
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginTop: 16 }}>
          {plans.map((p) => (
            <div
              key={p.key}
              className="tj-clickable"
              onClick={() => setPlan(p.key)}
              style={{ border: plan === p.key ? `2px solid ${C.accent}` : `1px solid ${C.line}`, background: C.card, borderRadius: 14, padding: '14px 8px', textAlign: 'center', position: 'relative' }}
            >
              {p.recommended && (
                <div style={{ position: 'absolute', top: -9, left: '50%', transform: 'translateX(-50%)', background: C.accent, color: C.creamText, fontSize: 10, padding: '2px 8px', borderRadius: 999, whiteSpace: 'nowrap' }}>推荐</div>
              )}
              <div style={{ fontSize: 13, color: C.sub }}>{p.name}</div>
              <div style={{ fontFamily: mono, fontSize: 20, fontWeight: 600, marginTop: 6 }}>¥{yuan(p.priceFen)}</div>
            </div>
          ))}
        </div>

        <button
          className="tj-reset tj-clickable"
          onClick={pay}
          disabled={paying}
          style={{ width: '100%', marginTop: 16, background: C.accent, color: C.creamText, textAlign: 'center', padding: 15, borderRadius: 14, fontSize: 16, fontWeight: 700, letterSpacing: 3, opacity: paying ? 0.7 : 1 }}
        >
          {paying ? '支付处理中…' : user?.isLamp ? '续供此灯' : '点亮长明灯'}
        </button>
        <div style={{ marginTop: 10, textAlign: 'center', fontFamily: mono, fontSize: 10, color: C.faint }}>
          {config && (config.disclaimer ? '* 当前为 mock 支付：下单后自动完成，不产生真实扣费' : '')}
        </div>
      </div>
    </div>
  );
}
