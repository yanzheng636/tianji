import { useState, type ReactNode } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useTianji } from '../App';

const nav = [
  ['/', '游寺'], ['/chat', '问卦'], ['/library', '藏经阁'], ['/wishes', '许愿池'],
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const { user, sessionReady } = useTianji();
  const [open, setOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="brand" aria-label="返回天机寺山门">
          <span className="brand-seal">天</span>
          <span><b>天机寺</b><small>TIANJI TEMPLE</small></span>
        </NavLink>
        <nav className={open ? 'primary-nav is-open' : 'primary-nav'} aria-label="主导航">
          {nav.map(([to, label]) => <NavLink key={to} to={to} onClick={() => setOpen(false)} className={({ isActive }) => isActive && (to !== '/' || location.pathname === '/') ? 'active' : ''}>{label}</NavLink>)}
          <NavLink to="/qian" onClick={() => setOpen(false)}>求签</NavLink>
          <NavLink to="/incense" onClick={() => setOpen(false)}>香火</NavLink>
        </nav>
        <div className="top-actions">
          <NavLink to="/lamp" className="lamp-status"><i />灯火</NavLink>
          <NavLink to="/profile" className="visitor-pill" aria-label="进入我的居所">
            <span>{sessionReady ? (user?.nickname?.slice(0, 1) ?? '吾') : '·'}</span>
            <em>{sessionReady ? '山中访客' : '入山中'}</em>
          </NavLink>
          <button className="menu-button" onClick={() => setOpen((value) => !value)} aria-label="打开导航" aria-expanded={open}>☰</button>
        </div>
      </header>
      <main>{children}</main>
      <footer className="site-footer">
        <div className="footer-brand">天机寺 <span>·</span> 一念照见</div>
        <p>传统文化娱乐与心理疗愈。本产品不预测命运，不提供命运修改服务。</p>
        <div>© 2026 TIANJI TEMPLE</div>
      </footer>
    </div>
  );
}
