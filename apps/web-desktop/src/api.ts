import type { AuthResult, BaziChart, BirthProfile, BookDetail, BookSummary, ChatMessage, ChatSession, ChatStreamEvent, Citation, Incense, MetaConfig, Order, Qian, QianReadingStreamEvent, Quota, TodayFortune, User, WikiConceptDetail, WikiDomainDetail, WikiDomainSummary, WikiEvidencePage, WikiSearchResult, Wish, WishPool } from './types';

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
  let response: Response;
  try {
    response = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    throw new ApiError('NETWORK_UNAVAILABLE', '无法连接山问服务，请确认后端 API 已启动', 0);
  }
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && retryGuest) {
      setToken(null);
      await api.ensureGuest();
      return request<T>(method, path, body, false);
    }
    const fallbackMessage = response.status >= 500
      ? '山问服务暂时不可用，请确认后端 API 已启动'
      : '请求未能完成，请稍后再试';
    throw new ApiError(data?.error?.code ?? 'UNKNOWN', data?.error?.message ?? fallbackMessage, response.status);
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
  saveQian: (id: string, saved: boolean) => request<{ saved: boolean }>('POST', `/api/qian/${encodeURIComponent(id)}/save`, { saved }),
  listSavedQian: () => request<Qian[]>('GET', '/api/qian/saved'),
  incenseActive: () => request<Incense | null>('GET', '/api/incense/active'),
  lightIncense: (type: string, wish?: string) => request<Incense>('POST', '/api/incense/light', { type, wish }),
  wishPool: () => request<WishPool>('GET', '/api/wishes'),
  createWish: (text: string) => request<Wish>('POST', '/api/wishes', { text }),
  fulfillWish: (id: string) => request<Wish>('POST', `/api/wishes/${id}/fulfill`),
  books: () => request<BookSummary[]>('GET', '/api/scripture/books'),
  book: (slug: string) => request<BookDetail>('GET', `/api/scripture/books/${slug}`),
  search: (query: string) => request<Citation[]>('GET', `/api/scripture/search?q=${encodeURIComponent(query)}`),
  wikiDomains: () => request<WikiDomainSummary[]>('GET', '/api/wiki/domains'),
  wikiDomain: (slug: string) => request<WikiDomainDetail>('GET', `/api/wiki/domains/${encodeURIComponent(slug)}`),
  wikiConcept: (id: string) => request<WikiConceptDetail>('GET', `/api/wiki/concepts/${encodeURIComponent(id)}`),
  wikiConceptEvidence: (id: string, opts: { offset?: number; limit?: number; q?: string } = {}) => {
    const params = new URLSearchParams({ offset: String(opts.offset ?? 0), limit: String(opts.limit ?? 10) });
    if (opts.q) params.set('q', opts.q);
    return request<WikiEvidencePage>('GET', `/api/wiki/concepts/${encodeURIComponent(id)}/evidence?${params}`);
  },
  wikiSearch: (query: string, limit = 12) => request<WikiSearchResult>('GET', `/api/wiki/search?q=${encodeURIComponent(query)}&limit=${limit}`),
  getProfile: () => request<{ profile: BirthProfile | null; chart: BaziChart | null }>('GET', '/api/profile'),
  saveProfile: (profile: Partial<BirthProfile> & { nickname?: string }) => request<{ profile: BirthProfile; chart: BaziChart }>('PUT', '/api/profile', profile),
  chatHistory: () => request<ChatMessage[]>('GET', '/api/chat/history'),
  chatSessions: () => request<ChatSession[]>('GET', '/api/chat/sessions'),
  createChatSession: () => request<ChatSession>('POST', '/api/chat/sessions'),
  sessionMessages: (id: string) => request<ChatMessage[]>('GET', `/api/chat/sessions/${id}/messages`),
  deleteChatSession: (id: string) => request<null>('DELETE', `/api/chat/sessions/${id}`),
  createOrder: (body: { kind: 'lamp' | 'merit'; plan?: string; amountFen?: number; refId?: string }) => request<Order>('POST', '/api/pay/orders', body),
  getOrder: (id: string) => request<Order>('GET', `/api/pay/orders/${id}`),
};

export function streamChat(body: { text: string; qianId?: string; sessionId?: string | null }, onEvent: (event: ChatStreamEvent) => void) {
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
      if (!response.ok || !response.body) throw new Error('山问服务暂时中断，请稍后再试');
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

export function streamQianReading(drawId: string, onEvent: (event: QianReadingStreamEvent) => void) {
  const controller = new AbortController();
  let finished = false;
  let watchdog = 0;
  const armWatchdog = () => {
    window.clearTimeout(watchdog);
    watchdog = window.setTimeout(() => {
      if (finished) return;
      finished = true;
      onEvent({ type: 'error', message: '签意暂未展开' });
      controller.abort();
    }, 18000);
  };
  const emit = (event: QianReadingStreamEvent) => {
    if (finished) return;
    if (event.type === 'done' || event.type === 'error') {
      finished = true;
      window.clearTimeout(watchdog);
    } else {
      armWatchdog();
    }
    onEvent(event);
  };
  armWatchdog();
  void (async () => {
    try {
      await api.ensureGuest();
      const response = await fetch(`/api/qian/${encodeURIComponent(drawId)}/reading`, {
        headers: { authorization: `Bearer ${getToken()}` },
        signal: controller.signal,
      });
      if (!response.ok || !response.body) throw new Error('签意暂未展开');
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
          try { emit(JSON.parse(line.slice(5).trim()) as QianReadingStreamEvent); } catch { /* wait for the next complete event */ }
        }
      }
      if (!finished) emit({ type: 'error', message: '签意暂未展开' });
    } catch (error) {
      if ((error as Error).name !== 'AbortError') emit({ type: 'error', message: (error as Error).message || '签意暂未展开' });
    }
  })();
  return () => {
    finished = true;
    window.clearTimeout(watchdog);
    controller.abort();
  };
}
