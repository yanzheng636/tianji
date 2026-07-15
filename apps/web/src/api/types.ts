import type { User, ChatStreamEvent } from '../shared';

export interface AuthResult {
  token: string;
  user: User;
}

export type { ChatStreamEvent };
