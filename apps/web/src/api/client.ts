// API 客户端：统一携带 token、统一错误、SSE 流式。
import type {
  AuthResult,
  ChatStreamEvent,
} from './types';
import type {
  BaziChart,
  BirthProfile,
  BookDetail,
  BookSummary,
  ChatMessage,
  Citation,
  Incense,
  MetaConfig,
  Order,
  Qian,
  Quota,
  TodayFortune,
  User,
  WikiConceptDetail,
  WikiDomainDetail,
  WikiDomainSummary,
  WikiSearchResult,
  Wish,
  WishPool,
} from '../shared';

const TOKEN_KEY = 'tj_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string | null) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function req<T>(
  method: string,
  path: string,
  body?: unknown,
  retryGuest = true,
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.authorization = `Bearer ${token}`;
  if (body !== undefined) headers['content-type'] = 'application/json';

  const res = await fetch(path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return undefined as T;

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err = data?.error;
    if (res.status === 401) setToken(null);
    if (res.status === 401 && retryGuest && path !== '/api/auth/guest') {
      await ensureGuest();
      return req<T>(method, path, body, false);
    }
    throw new ApiError(err?.code ?? 'UNKNOWN', err?.message ?? '请求失败', res.status);
  }
  return data as T;
}

let guestPromise: Promise<AuthResult> | null = null;

/**
 * 透明访客会话：先让产品可直接使用，手机号登录接口保留给后续开启认证。
 * 访客仍有服务端 User 记录，因此配额、命盘、香火和问卦历史不会混在一起。
 */
async function ensureGuest(): Promise<AuthResult> {
  const token = getToken();
  if (token) {
    try {
      return { token, user: await req<User>('GET', '/api/auth/me', undefined, false) };
    } catch {
      setToken(null);
    }
  }
  if (!guestPromise) {
    guestPromise = req<AuthResult>('POST', '/api/auth/guest', undefined, false)
      .then((result) => {
        setToken(result.token);
        return result;
      })
      .finally(() => {
        guestPromise = null;
      });
  }
  return guestPromise;
}

export const api = {
  ensureGuest,
  // 认证
  sendCode: (phone: string) => req<{ ok: boolean; devCode?: string }>('POST', '/api/auth/send-code', { phone }),
  login: (phone: string, code: string) =>
    req<AuthResult>('POST', '/api/auth/login', { phone, code }),
  me: () => req<User>('GET', '/api/auth/me'),

  // 首页 / 配置
  config: () => req<MetaConfig>('GET', '/api/meta/config'),
  today: () => req<TodayFortune>('GET', '/api/meta/today'),

  // 摇签
  drawQian: (hall: string, topic?: string) =>
    req<Qian>('POST', '/api/qian/draw', { hall, topic }),
  qianQuota: () => req<Quota>('GET', '/api/qian/quota'),

  // 上香
  incenseActive: () => req<Incense | null>('GET', '/api/incense/active'),
  lightIncense: (type: string, wish?: string) =>
    req<Incense>('POST', '/api/incense/light', { type, wish }),

  // 许愿
  wishPool: () => req<WishPool>('GET', '/api/wishes'),
  createWish: (text: string) => req<Wish>('POST', '/api/wishes', { text }),
  fulfillWish: (id: string) => req<Wish>('POST', `/api/wishes/${id}/fulfill`),

  // 藏经阁 · 原书（可溯源的原文书库）
  books: () => req<BookSummary[]>('GET', '/api/scripture/books'),
  book: (slug: string) => req<BookDetail>('GET', `/api/scripture/books/${slug}`),
  search: (q: string) =>
    req<Citation[]>('GET', `/api/scripture/search?q=${encodeURIComponent(q)}`),

  // 藏经阁 · 命理百科（知识图谱：领域 → 概念词条 → 原文证据）
  wikiDomains: () => req<WikiDomainSummary[]>('GET', '/api/wiki/domains'),
  wikiDomain: (slug: string) =>
    req<WikiDomainDetail>('GET', `/api/wiki/domains/${encodeURIComponent(slug)}`),
  wikiConcept: (id: string) =>
    req<WikiConceptDetail>('GET', `/api/wiki/concepts/${encodeURIComponent(id)}`),
  wikiSearch: (q: string) =>
    req<WikiSearchResult>('GET', `/api/wiki/search?q=${encodeURIComponent(q)}`),

  // 命盘
  getProfile: () =>
    req<{ profile: BirthProfile | null; chart: BaziChart | null }>('GET', '/api/profile'),
  saveProfile: (p: Partial<BirthProfile> & { nickname?: string }) =>
    req<{ profile: BirthProfile; chart: BaziChart }>('PUT', '/api/profile', p),

  // 问卦历史
  chatHistory: () => req<ChatMessage[]>('GET', '/api/chat/history'),

  // 支付
  createOrder: (body: {
    kind: 'lamp' | 'merit';
    plan?: string;
    amountFen?: number;
    refId?: string;
  }) => req<Order>('POST', '/api/pay/orders', body),
  getOrder: (id: string) => req<Order>('GET', `/api/pay/orders/${id}`),
};

/**
 * 问卦 SSE 流式。逐事件回调；返回一个可取消的 abort 函数。
 */
export function streamChat(
  body: { text: string; qianId?: string },
  onEvent: (e: ChatStreamEvent) => void,
): () => void {
  const controller = new AbortController();
  const token = getToken();

  (async () => {
    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          ...(token ? { authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        const data = await res.json().catch(() => null);
        onEvent({ type: 'error', message: data?.error?.message ?? '天机推演失败' });
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split('\n\n');
        buf = parts.pop() ?? '';
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith('data:')) continue;
          const json = line.slice(5).trim();
          if (!json) continue;
          try {
            onEvent(JSON.parse(json) as ChatStreamEvent);
          } catch {
            /* 忽略半包 */
          }
        }
      }
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        onEvent({ type: 'error', message: '连接中断' });
      }
    }
  })();

  return () => controller.abort();
}
