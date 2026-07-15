import { create } from 'zustand';
import { api, getToken, setToken } from '../api/client';
import type { MetaConfig, User } from '../shared';

export type Screen =
  | 'home'
  | 'hall'
  | 'qian'
  | 'incense'
  | 'wish'
  | 'library'
  | 'domain'
  | 'concept'
  | 'book'
  | 'chat'
  | 'profile'
  | 'vip'
  | 'palm';

interface Nav {
  screen: Screen;
  hallKey?: string;
  bookSlug?: string;
  /** 藏经阁 · 知识领域 slug（领域页） */
  domainSlug?: string;
  /** 藏经阁 · 概念词条 id（词条页），形如 concept:physiognomy:yintang */
  conceptId?: string;
  /** 带入问卦页的预设问题 */
  chatPreset?: string;
  /** 摇签/报告带入问卦的签 id */
  qianId?: string;
}

interface AppState {
  ready: boolean;
  user: User | null;
  config: MetaConfig | null;
  nav: Nav;
  toast: string | null;
  loginOpen: boolean;

  init: () => Promise<void>;
  setUser: (u: User | null, token?: string) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
  go: (screen: Screen, extra?: Partial<Nav>) => void;
  showToast: (t: string) => void;
  openLogin: () => void;
  closeLogin: () => void;
  /** 访客会话就绪后执行 action；访客创建失败时再回退到手机号登录 */
  requireAuth: (action: () => void) => void;
}

let toastTimer: ReturnType<typeof setTimeout> | undefined;

export const useApp = create<AppState>((set, get) => ({
  ready: false,
  user: null,
  config: null,
  nav: { screen: 'home' },
  toast: null,
  loginOpen: false,

  init: async () => {
    const config = await api.config().catch(() => null);
    let user: User | null = null;
    const guest = await api.ensureGuest().catch(() => null);
    user = guest?.user ?? null;
    set({ config, user, ready: true });
  },

  setUser: (u, token) => {
    if (token !== undefined) setToken(token);
    set({ user: u });
  },

  logout: () => {
    setToken(null);
    set({ user: null, nav: { screen: 'home' } });
    // 当前为免手机号的访客模式；退出只重置本地访客，随后自动建立新会话。
    void api.ensureGuest().then(({ user, token }) => {
      setToken(token);
      set({ user });
    }).catch(() => {});
  },

  refreshUser: async () => {
    if (!getToken()) return;
    const user = await api.me().catch(() => null);
    set({ user });
  },

  go: (screen, extra) => set({ nav: { screen, ...extra } }),

  showToast: (t) => {
    set({ toast: t });
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => set({ toast: null }), 2400);
  },

  openLogin: () => set({ loginOpen: true }),
  closeLogin: () => set({ loginOpen: false }),

  requireAuth: (action) => {
    if (get().user) action();
    else {
      void api.ensureGuest()
        .then(({ user, token }) => {
          setToken(token);
          set({ user });
          action();
        })
        .catch(() => set({ loginOpen: true }));
    }
  },
}));

export const _api = api;
export { getToken };
