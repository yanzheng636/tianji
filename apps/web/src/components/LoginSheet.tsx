import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../api/client';
import { useApp } from '../store/app';
import { C, mono } from '../theme/tokens';

// 需要登录时弹出的底部登录卡片（手机号 + 验证码）。
export function LoginSheet({ onClose }: { onClose: () => void }) {
  const setUser = useApp((s) => s.setUser);
  const showToast = useApp((s) => s.showToast);
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [sent, setSent] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [busy, setBusy] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => () => clearInterval(timer.current), []);

  const startCooldown = () => {
    setCooldown(60);
    timer.current = setInterval(
      () => setCooldown((c) => (c <= 1 ? (clearInterval(timer.current), 0) : c - 1)),
      1000,
    );
  };

  const send = async () => {
    if (!/^1[3-9]\d{9}$/.test(phone)) return showToast('请输入有效手机号');
    setBusy(true);
    try {
      const result = await api.sendCode(phone);
      setSent(true);
      startCooldown();
      if (result.devCode) {
        setCode(result.devCode);
        showToast('开发验证码已自动填入');
      } else {
        showToast('验证码已发送');
      }
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : '发送失败');
    } finally {
      setBusy(false);
    }
  };

  const login = async () => {
    if (!/^\d{6}$/.test(code)) return showToast('请输入 6 位验证码');
    setBusy(true);
    try {
      const r = await api.login(phone, code);
      setUser(r.user, r.token);
      showToast(`欢迎入山门`);
      onClose();
    } catch (e) {
      showToast(e instanceof ApiError ? e.message : '登录失败');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: 'absolute', inset: 0, zIndex: 90, background: 'rgba(22,18,14,0.5)',
        display: 'flex', flexDirection: 'column', justifyContent: 'flex-end',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: C.paper, borderRadius: '24px 24px 0 0', padding: '24px 24px 34px',
          animation: 'tjDrop 0.3s ease-out',
        }}
      >
        <div style={{ width: 40, height: 4, borderRadius: 2, background: C.line, margin: '0 auto 20px' }} />
        <div style={{ fontSize: 20, fontWeight: 900, letterSpacing: 2 }}>登录 · 入山门</div>
        <div style={{ fontSize: 12, color: C.muted, marginTop: 6 }}>
          手机号登录，未注册将自动开光建档
        </div>

        <input
          value={phone}
          onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 11))}
          inputMode="numeric"
          placeholder="手机号"
          style={inputStyle}
        />

        <div style={{ display: 'flex', gap: 10, marginTop: 12 }}>
          <input
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            inputMode="numeric"
            placeholder="6 位验证码"
            style={{ ...inputStyle, marginTop: 0, flex: 1 }}
          />
          <button
            className="tj-reset tj-clickable"
            onClick={send}
            disabled={busy || cooldown > 0}
            style={{
              width: 118, borderRadius: 12, border: `1px solid ${C.accent}`,
              color: cooldown > 0 ? C.muted : C.accent,
              fontFamily: mono, fontSize: 13, background: C.card,
              opacity: cooldown > 0 ? 0.6 : 1,
            }}
          >
            {cooldown > 0 ? `${cooldown}s` : sent ? '重发' : '获取验证码'}
          </button>
        </div>

        <button
          className="tj-reset tj-clickable"
          onClick={login}
          disabled={busy}
          style={{
            width: '100%', marginTop: 18, background: C.accent, color: C.creamText,
            textAlign: 'center', padding: 15, borderRadius: 14, fontSize: 16,
            fontWeight: 700, letterSpacing: 4,
          }}
        >
          进入
        </button>
        <div style={{ marginTop: 12, textAlign: 'center', fontSize: 11, color: C.faint }}>
          登录即代表同意《用户协议》与《隐私政策》
        </div>
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: '100%', marginTop: 16, border: `1px solid ${C.line}`, background: '#fff',
  borderRadius: 12, padding: '13px 14px', fontSize: 15, color: C.ink, outline: 'none',
};
