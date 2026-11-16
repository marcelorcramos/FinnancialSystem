import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from '../api/api-config';
import { AssistantAnswer, ChatMessage, ConversationRead, InsightRead } from '../api/types';

/**
 * The assistant: questions about the user's money, answered from their own
 * reports. The server reports whether it is set up; the app hides it otherwise.
 */
@Injectable({ providedIn: 'root' })
export class AssistantService {
  private readonly http = inject(HttpClient);
  private readonly api = inject(API_BASE_URL);

  /** Null until the server answered; false when the assistant is not set up. */
  readonly enabled = signal<boolean | null>(null);
  private checked = false;

  /** Asks the server once per app load whether the assistant is on. */
  checkStatus(): void {
    if (this.checked) return;
    this.checked = true;
    this.http.get<{ enabled: boolean }>(`${this.api}/assistant/status`).subscribe({
      next: ({ enabled }) => this.enabled.set(enabled),
      error: () => this.enabled.set(false),
    });
  }

  ask(text: string, conversationId: string | null): Observable<AssistantAnswer> {
    return this.http.post<AssistantAnswer>(`${this.api}/assistant/questions`, {
      text,
      ...(conversationId ? { conversation_id: conversationId } : {}),
    });
  }

  conversations(): Observable<ConversationRead[]> {
    return this.http.get<ConversationRead[]>(`${this.api}/assistant/conversations`);
  }

  messages(conversationId: string): Observable<ChatMessage[]> {
    return this.http.get<ChatMessage[]>(`${this.api}/assistant/conversations/${conversationId}`);
  }

  remove(conversationId: string): Observable<void> {
    return this.http.delete<void>(`${this.api}/assistant/conversations/${conversationId}`);
  }

  insight(monthId: string): Observable<InsightRead> {
    return this.http.get<InsightRead>(`${this.api}/months/${monthId}/insight`);
  }
}
