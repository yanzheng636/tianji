import { useState, type ReactNode } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useTianji } from '../App';

const nav = [
  ['/', '山门'], ['/chat', '问室'], ['/library', '书阁'], ['/wishes', '愿池'],
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const { user, sessionReady } = useTianji();
  const [open, setOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="brand" aria-label="返回山问首页">
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /><b /></span>
          <span><b>山问</b><small>SHANWEN</small></span>
        </NavLink>
        <nav className={open ? 'primary-nav is-open' : 'primary-nav'} aria-label="主导航">
          {nav.map(([to, label]) => <NavLink key={to} to={to} onClick={() => setOpen(false)} className={({ isActive }) => isActive && (to !== '/' || location.pathname === '/') ? 'active' : ''}>{label}</NavLink>)}
          <NavLink to="/qian" onClick={() => setOpen(false)}>签室</NavLink>
          <NavLink to="/incense" onClick={() => setOpen(false)}>静室</NavLink>
        </nav>
        <div className="top-actions">
          <NavLink to="/lamp" className="lamp-status"><i />长明</NavLink>
          <NavLink to="/profile" className="visitor-pill" aria-label="进入我的山居">
            <span>{sessionReady ? (user?.nickname?.slice(0, 1) ?? '吾') : '·'}</span>
            <em>{sessionReady ? '我的山居' : '入山中'}</em>
          </NavLink>
          <button className="menu-button" onClick={() => setOpen((value) => !value)} aria-label="打开导航" aria-expanded={open}>☰</button>
        </div>
      </header>
      <main>{children}</main>
      <footer className="site-footer">
        <div className="footer-brand">山问 <span>·</span> 入山问心</div>
        <p>传统文化娱乐与心理疗愈。本产品不预测命运，不提供命运修改服务。</p>
        <div>© 2026 SHANWEN</div>
      </footer>
    </div>
  );
}
