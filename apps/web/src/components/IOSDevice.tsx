import type { ReactNode } from 'react';

// 简化版 iOS 设备外壳（灵感来自 demo 的 iOS 26 frame）。
// 在桌面居中显示一台「手机」；移动端自动铺满全屏。
export function IOSDevice({ children }: { children: ReactNode }) {
  return (
    <div className="tj-stage">
      <div className="tj-device">
        <div className="tj-island" />
        <div className="tj-statusbar">
          <span className="tj-time">9:41</span>
          <span className="tj-signal">
            <svg width="18" height="11" viewBox="0 0 18 11">
              <rect x="0" y="7" width="3" height="4" rx="0.6" fill="#000" />
              <rect x="4.5" y="5" width="3" height="6" rx="0.6" fill="#000" />
              <rect x="9" y="2.5" width="3" height="8.5" rx="0.6" fill="#000" />
              <rect x="13.5" y="0" width="3" height="11" rx="0.6" fill="#000" />
            </svg>
            <svg width="24" height="12" viewBox="0 0 24 12">
              <rect x="0.5" y="0.5" width="20" height="11" rx="3" stroke="#000" strokeOpacity="0.35" fill="none" />
              <rect x="2" y="2" width="17" height="8" rx="1.6" fill="#000" />
              <path d="M22 4v4c.7-.3 1.3-1.1 1.3-2S22.7 4.3 22 4Z" fill="#000" fillOpacity="0.4" />
            </svg>
          </span>
        </div>
        <div className="tj-screen">{children}</div>
        <div className="tj-home" />
      </div>
    </div>
  );
}
