import type { AuthResult, BaziChart, BirthProfile, BookDetail, BookSummary, ChatMessage, ChatStreamEvent, Citation, Incense, MetaConfig, Order, Qian, Quota, TodayFortune, User, Wish, WishPool } from './types';

const TOKEN_KEY = 'tj_desktop_guest_token_v1';
export const getToken = () => localStorage.getItem(TOKEN_KEY);
const setToken = (token: string | null) => token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY);

export class ApiError extends Error {
  constructor(public code: string, message: string, public status: number) { super(message); }
}

async function request<T>(method: string, path: string, body?: unknown, retryGuest = true): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.authorization = `Bearer ${token}`;
  if (body !== undefined) headers['content-type'] = 'application/json';
  const response = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && retryGuest) {
      setToken(null);
      await api.ensureGuest();
      return request<T>(method, path, body, false);
    }
    throw new ApiError(data?.error?.code ?? 'UNKNOWN', data?.error?.message ?? '山门暂时未开，请稍后再试', response.status);
  }
  return data as T;
}

let guestPromise: Promise<AuthResult> | null = null;

export const api = {
  ensureGuest: async (): Promise<AuthResult> => {
    if (getToken()) {
      try { return { token: getToken()!, user: await request<User>('GET', '/api/auth/me', undefined, false) }; }
      catch { setToken(null); }
    }
    if (!guestPromise) {
      guestPromise = request<AuthResult>('POST', '/api/auth/guest', undefined, false)
        .then((result) => { setToken(result.token); return result; })
        .finally(() => { guestPromise = null; });
    }
    return guestPromise;
  },
  me: () => request<User>('GET', '/api/auth/me'),
  config: () => request<MetaConfig>('GET', '/api/meta/config'),
  today: () => request<TodayFortune>('GET', '/api/meta/today'),
  drawQian: (hall: string, topic?: string) => request<Qian>('POST', '/api/qian/draw', { hall, topic }),
  qianQuota: () => request<Quota>('GET', '/api/qian/quota'),
  incenseActive: () => request<Incense | null>('GET', '/api/incense/active'),
  lightIncense: (type: string, wish?: string) => request<Incense>('POST', '/api/incense/light', { type, wish }),
  wishPool: () => request<WishPool>('GET', '/api/wishes'),
  createWish: (text: string) => request<Wish>('POST', '/api/wishes', { text }),
  fulfillWish: (id: string) => request<Wish>('POST', `/api/wishes/${id}/fulfill`),
  books: () => request<BookSummary[]>('GET', '/api/scripture/books'),
  book: (slug: string) => request<BookDetail>('GET', `/api/scripture/books/${slug}`),
  search: (query: string) => request<Citation[]>('GET', `/api/scripture/search?q=${encodeURIComponent(query)}`),
  getProfile: () => request<{ profile: BirthProfile | null; chart: BaziChart | null }>('GET', '/api/profile'),
  saveProfile: (profile: Partial<BirthProfile> & { nickname?: string }) => request<{ profile: BirthProfile; chart: BaziChart }>('PUT', '/api/profile', profile),
  chatHistory: () => request<ChatMessage[]>('GET', '/api/chat/history'),
  createOrder: (body: { kind: 'lamp' | 'merit'; plan?: string; amountFen?: number; refId?: string }) => request<Order>('POST', '/api/pay/orders', body),
  getOrder: (id: string) => request<Order>('GET', `/api/pay/orders/${id}`),
};

export function streamChat(body: { text: string; qianId?: string }, onEvent: (event: ChatStreamEvent) => void) {
  const controller = new AbortController();
  void (async () => {
    try {
      await api.ensureGuest();
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'content-type': 'application/json', authorization: `Bearer ${getToken()}` },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      if (!response.ok || !response.body) throw new Error('天机推演暂时中断');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() ?? '';
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith('data:')) continue;
          try { onEvent(JSON.parse(line.slice(5).trim()) as ChatStreamEvent); } catch { /* incomplete event */ }
        }
      }
    } catch (error) {
      if ((error as Error).name !== 'AbortError') onEvent({ type: 'error', message: (error as Error).message || '连接中断' });
    }
  })();
  return () => controller.abort();
}
