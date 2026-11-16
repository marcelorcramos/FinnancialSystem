import {
  ChangeDetectionStrategy,
  Component,
  computed,
  ElementRef,
  inject,
  signal,
  viewChild,
} from '@angular/core';

import { apiErrorMessage } from '../../core/api/api-errors';
import { ChatMessage, ConversationRead } from '../../core/api/types';
import { AssistantService } from '../../core/assistant/assistant.service';
import { Icon } from '../../shared/ui/icon';
import { ToastService } from '../../shared/ui/toast.service';

export const SUGGESTIONS = [
  'How much did I invest in the last 2 months?',
  'How much did I spend on food in the last 3 months?',
  'Which label grew the most since last month?',
  'Am I on track for my goals?',
];

const MAX_LENGTH = 1000;

/** A message on screen: saved, or the question waiting for its answer. */
interface Shown {
  id: string;
  kind: string;
  text: string;
}

/**
 * Questions about your money, answered from your own reports. Conversations
 * are kept on the server; the list on the side reopens them.
 */
@Component({
  selector: 'app-assistant-page',
  imports: [Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './assistant-page.html',
  styleUrl: './assistant-page.scss',
})
export default class AssistantPage {
  private readonly assistant = inject(AssistantService);
  private readonly toasts = inject(ToastService);
  private readonly thread = viewChild<ElementRef<HTMLElement>>('thread');
  private readonly input = viewChild<ElementRef<HTMLTextAreaElement>>('question');

  protected readonly enabled = this.assistant.enabled;
  protected readonly suggestions = SUGGESTIONS;
  protected readonly maxLength = MAX_LENGTH;
  protected readonly conversations = signal<ConversationRead[]>([]);
  protected readonly activeId = signal<string | null>(null);
  protected readonly messages = signal<Shown[]>([]);
  protected readonly draft = signal('');
  protected readonly pending = signal(false);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly showList = signal(false);
  protected readonly canSend = computed(
    () => this.draft().trim().length > 0 && this.draft().length <= MAX_LENGTH && !this.pending(),
  );
  protected readonly activeTitle = computed(
    () => this.conversations().find((c) => c.id === this.activeId())?.title ?? 'New conversation',
  );

  constructor() {
    this.assistant.checkStatus();
    this.loadConversations();
  }

  private loadConversations(): void {
    this.assistant.conversations().subscribe({
      next: (list) => this.conversations.set(list),
      error: () => this.conversations.set([]),
    });
  }

  protected newConversation(): void {
    this.activeId.set(null);
    this.messages.set([]);
    this.error.set(null);
    this.showList.set(false);
    this.focusInput();
  }

  protected open(conversation: ConversationRead): void {
    if (this.pending()) return;
    this.activeId.set(conversation.id);
    this.showList.set(false);
    this.error.set(null);
    this.loading.set(true);
    this.assistant.messages(conversation.id).subscribe({
      next: (list) => {
        this.messages.set(list.map(toShown));
        this.loading.set(false);
        this.scrollToEnd();
      },
      error: (error: unknown) => {
        this.loading.set(false);
        this.error.set(apiErrorMessage(error));
      },
    });
  }

  protected remove(conversation: ConversationRead): void {
    this.assistant.remove(conversation.id).subscribe({
      next: () => {
        this.conversations.update((list) => list.filter((c) => c.id !== conversation.id));
        if (this.activeId() === conversation.id) this.newConversation();
        this.toasts.show('Conversation deleted');
      },
      error: (error: unknown) => this.toasts.show(apiErrorMessage(error)),
    });
  }

  protected useSuggestion(text: string): void {
    this.draft.set(text);
    this.send();
  }

  /** Enter sends; Shift+Enter starts a new line. */
  protected onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      this.send();
    }
  }

  protected send(): void {
    if (!this.canSend()) return;
    const text = this.draft().trim();
    this.pending.set(true);
    this.error.set(null);
    this.draft.set('');
    this.messages.update((list) => [...list, { id: 'pending', kind: 'question', text }]);
    this.scrollToEnd();
    this.assistant.ask(text, this.activeId()).subscribe({
      next: ({ conversation, answer }) => {
        this.pending.set(false);
        this.messages.update((list) => [
          ...list.map((m) => (m.id === 'pending' ? { ...m, id: `q-${answer.id}` } : m)),
          toShown(answer),
        ]);
        if (this.activeId() !== conversation.id) {
          this.activeId.set(conversation.id);
          this.conversations.update((list) => [conversation, ...list]);
        } else {
          this.conversations.update((list) => [
            conversation,
            ...list.filter((c) => c.id !== conversation.id),
          ]);
        }
        this.scrollToEnd();
        this.focusInput();
      },
      error: (error: unknown) => {
        this.pending.set(false);
        // Nothing was saved: take the question back so it can be sent again.
        this.messages.update((list) => list.filter((m) => m.id !== 'pending'));
        this.draft.set(text);
        this.error.set(apiErrorMessage(error));
      },
    });
  }

  private scrollToEnd(): void {
    setTimeout(() => {
      const thread = this.thread()?.nativeElement;
      if (thread) thread.scrollTop = thread.scrollHeight;
    });
  }

  private focusInput(): void {
    setTimeout(() => this.input()?.nativeElement.focus());
  }
}

function toShown(message: ChatMessage): Shown {
  return { id: message.id, kind: message.kind, text: message.text };
}
