import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, Subject, throwError } from 'rxjs';

import { AssistantAnswer, ChatMessage, ConversationRead } from '../../core/api/types';
import { AssistantService } from '../../core/assistant/assistant.service';
import AssistantPage, { SUGGESTIONS } from './assistant-page';

const OLD: ConversationRead = {
  id: 'c1',
  title: 'What did I spend on food?',
  created_at: '2026-11-15T10:00:00Z',
  updated_at: '2026-11-15T10:00:00Z',
};

function answer(text: string, id = 'c2'): AssistantAnswer {
  return {
    conversation: { ...OLD, id, title: 'New one' },
    answer: { id: 'a1', kind: 'answer', text, created_at: '2026-11-16T10:00:00Z' },
  };
}

describe('AssistantPage', () => {
  let fixture: ComponentFixture<AssistantPage>;
  let el: HTMLElement;
  let api: {
    enabled: ReturnType<typeof signal<boolean | null>>;
    checkStatus: ReturnType<typeof vi.fn>;
    conversations: ReturnType<typeof vi.fn>;
    messages: ReturnType<typeof vi.fn>;
    ask: ReturnType<typeof vi.fn>;
    remove: ReturnType<typeof vi.fn>;
  };

  async function render(enabled: boolean | null = true) {
    api = {
      enabled: signal(enabled),
      checkStatus: vi.fn(),
      conversations: vi.fn(() => of([OLD])),
      messages: vi.fn(() =>
        of<ChatMessage[]>([
          { id: 'm1', kind: 'question', text: 'What did I spend on food?', created_at: '' },
          { id: 'm2', kind: 'answer', text: '€212.00.', created_at: '' },
        ]),
      ),
      ask: vi.fn(() => of(answer('You invested €50.00.'))),
      remove: vi.fn(() => of(undefined)),
    };
    TestBed.configureTestingModule({
      imports: [AssistantPage],
      providers: [{ provide: AssistantService, useValue: api }],
    });
    fixture = TestBed.createComponent(AssistantPage);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  const bubbles = () =>
    [...el.querySelectorAll('.message__body')].map((b) => b.textContent?.trim());

  async function type(text: string) {
    const box = el.querySelector<HTMLTextAreaElement>('#assistant-question')!;
    box.value = text;
    box.dispatchEvent(new Event('input'));
    await fixture.whenStable();
    return box;
  }

  it('explains when the server has no assistant', async () => {
    await render(false);
    expect(el.textContent).toContain('The assistant is not set up');
    expect(el.querySelector('#assistant-question')).toBeNull();
  });

  it('offers suggestions and asks one with a click', async () => {
    await render();
    const chips = [...el.querySelectorAll<HTMLButtonElement>('.chip')];
    expect(chips.map((c) => c.textContent?.trim())).toEqual(SUGGESTIONS);
    chips[0]!.click();
    await fixture.whenStable();
    expect(api.ask).toHaveBeenCalledWith(SUGGESTIONS[0], null);
    expect(bubbles()).toEqual([SUGGESTIONS[0], 'You invested €50.00.']);
    expect(el.querySelector('.chat__title')?.textContent?.trim()).toBe('New one');
  });

  it('sends with Enter, shows the wait, then continues the same conversation', async () => {
    await render();
    const reply = new Subject<AssistantAnswer>();
    api.ask.mockReturnValue(reply);
    const box = await type('How much did I invest?');
    box.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    await fixture.whenStable();
    expect(el.textContent).toContain('Reading your reports');
    expect(box.value).toBe('');
    reply.next(answer('€50.00.'));
    reply.complete();
    await fixture.whenStable();

    api.ask.mockReturnValue(of(answer('€212.00.')));
    await type('And Food?');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
    expect(api.ask).toHaveBeenLastCalledWith('And Food?', 'c2');
  });

  it('gives the question back when the answer fails', async () => {
    await render();
    api.ask.mockReturnValue(
      throwError(
        () =>
          new HttpErrorResponse({
            status: 503,
            error: { detail: 'The assistant could not answer right now.' },
          }),
      ),
    );
    const box = await type('How much?');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
    expect(el.querySelector('[role=alert]')?.textContent).toContain('could not answer right now');
    expect(box.value).toBe('How much?');
    expect(bubbles()).toEqual([]);
  });

  it('reopens and deletes earlier conversations', async () => {
    await render();
    el.querySelector<HTMLButtonElement>('.list__open')!.click();
    await fixture.whenStable();
    expect(api.messages).toHaveBeenCalledWith('c1');
    expect(bubbles()).toEqual(['What did I spend on food?', '€212.00.']);

    el.querySelector<HTMLButtonElement>('[aria-label^="Delete conversation"]')!.click();
    await fixture.whenStable();
    expect(api.remove).toHaveBeenCalledWith('c1');
    expect(el.querySelectorAll('.list__open').length).toBe(0);
    expect(bubbles()).toEqual([]);
  });
});
