export interface User { id: string; phone: string; nickname: string | null; isLamp: boolean }
export interface AuthResult { token: string; user: User }
export interface TodayFortune { ganzhi: string; date: string; luck: number; yi: string[]; ji: string[] }
export interface HallMeta { key: string; name: string; code: string; char: string; deity: string; sub: string; desc: string; topic: string }
export interface IncenseMeta { key: string; char: string; name: string; desc: string; durationSec: number }
export interface LampPlanMeta { key: string; name: string; priceFen: number; days: number | null; recommended: boolean }
export interface MetaConfig { halls: HallMeta[]; incenses: IncenseMeta[]; lampPlans: LampPlanMeta[]; disclaimer: string }
export interface Qian { id: string; no: string; level: string; text: string; src: string; note: string; topic: string; drawnAt: string }
export interface Quota { kind: string; used: number; limit: number; remaining: number }
export interface Incense { id: string; type: string; name: string; startedAt: string; endsAt: string; durationSec: number; remainingSec: number; status: 'burning' | 'done' }
export interface Wish { id: string; text: string; status: 'active' | 'fulfilled'; moderation: 'pending' | 'approved' | 'rejected'; moderationReason: string | null; createdAt: string; fulfilledAt: string | null; mine: boolean }
export interface WishPool { total: number; floating: Wish[]; mine: Wish[] }
export interface Citation { book: string; chapter: string; text: string; plain: string; sourceId: string | null; quality: string; concepts: string[]; intent: string | null; path: string | null; relationHops: string[]; structure: Record<string, unknown> | null }
export interface ChatMessage { id: string; role: 'user' | 'assistant'; text: string; citation: Citation | null; createdAt: string }
export interface BookSummary { slug: string; char: string; name: string; meta: string; passageCount: number }
export interface Passage { id: string; chapter: string; text: string; plain: string }
export interface BookDetail extends BookSummary { passages: Passage[] }
export interface BaziPillar { gan: string; zhi: string; label: string }
export interface BaziChart { pillars: BaziPillar[]; dayMaster: string; zodiac: string; lunarDate: string; solarTermsNote: string; fiveElements: Record<string, number>; summary: string; hourKnown: boolean }
export interface BirthProfile { gender: 'male' | 'female'; birthDate: string; birthHour: number | null; birthPlace: string | null }
export interface Order { orderId: string; outTradeNo: string; amountFen: number; status: 'pending' | 'paid' | 'failed' | 'refunded'; payParams: Record<string, unknown> | null }
export type ChatStreamEvent = { type: 'delta'; text: string } | { type: 'citation'; citation: Citation } | { type: 'done'; messageId: string } | { type: 'error'; message: string };
