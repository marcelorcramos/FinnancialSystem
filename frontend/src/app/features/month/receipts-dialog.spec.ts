import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { AttachmentRead } from '../../core/api/types';
import { FileOpener } from '../../shared/files/open-file';
import { ReceiptsApi, receiptProblem } from './receipts-api';
import { ReceiptsDialog, ReceiptsDialogData } from './receipts-dialog';

const RECEIPT: AttachmentRead = {
  id: 'r1',
  month_id: 'm10',
  entry_id: 'e1',
  filename: 'groceries.pdf',
  mime: 'application/pdf',
  size: 2048,
  created_at: '2026-10-02T09:00:00Z',
};
const LOOSE: AttachmentRead = { ...RECEIPT, id: 'r2', entry_id: null, filename: 'rent.png' };

describe('receiptProblem', () => {
  it('accepts receipt types up to 10 MB', () => {
    expect(receiptProblem(new File(['%PDF'], 'a.pdf', { type: 'application/pdf' }))).toBeNull();
    expect(receiptProblem(new File(['x'], 'a.txt', { type: 'text/plain' }))).toContain(
      'only JPEG, PNG, WebP images and PDF files are accepted',
    );
    const big = new File(['x'], 'big.jpg', { type: 'image/jpeg' });
    Object.defineProperty(big, 'size', { value: 11 * 1024 * 1024 });
    expect(receiptProblem(big)).toBe('big.jpg is larger than 10 MB');
  });
});

/** The real opener, except that it records where it would go instead of navigating. */
class TestOpener extends FileOpener {
  readonly visited: string[] = [];
  override go(url: string): void {
    this.visited.push(url);
  }
}

describe('ReceiptsDialog', () => {
  afterEach(() => vi.restoreAllMocks());

  let fixture: ComponentFixture<ReceiptsDialog>;
  let el: HTMLElement;
  let api: Record<string, ReturnType<typeof vi.fn>>;

  async function render(data: Partial<ReceiptsDialogData> = {}) {
    api = {
      list: vi.fn(() => of([RECEIPT, LOOSE])),
      upload: vi.fn((_: string, file: File) => of({ ...RECEIPT, id: 'new', filename: file.name })),
      url: vi.fn(() => of({ url: 'https://s3/signed', expires_in: 300 })),
      remove: vi.fn(() => of(undefined)),
      restore: vi.fn(() => of(RECEIPT)),
    };
    TestBed.configureTestingModule({
      imports: [ReceiptsDialog],
      providers: [
        { provide: ReceiptsApi, useValue: api },
        { provide: FileOpener, useClass: TestOpener },
        { provide: DialogRef, useValue: { close: vi.fn() } },
        {
          provide: DIALOG_DATA,
          useValue: {
            monthId: 'm10',
            monthTitle: 'October 2026',
            entry: null,
            closed: false,
            entryTitles: { e1: 'Food' },
            ...data,
          },
        },
      ],
    });
    fixture = TestBed.createComponent(ReceiptsDialog);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  const names = () => [...el.querySelectorAll('.file__name')].map((n) => n.textContent?.trim());

  it('lists the month receipts with the entry they belong to', async () => {
    await render();
    expect(el.querySelector('h2')?.textContent).toContain('Receipts · October 2026');
    expect(names()).toEqual(['groceries.pdf', 'rent.png']);
    expect(el.querySelector('.file__meta')?.textContent).toContain('2 KB');
    expect(el.querySelector('.file__meta')?.textContent).toContain('Food');
  });

  it('shows only the entry receipts and ties new uploads to the entry', async () => {
    await render({ entry: { id: 'e1', title: 'Food' } });
    expect(names()).toEqual(['groceries.pdf']);

    const input = el.querySelector<HTMLInputElement>('input[type=file]')!;
    const good = new File(['%PDF-1.7'], 'dinner.pdf', { type: 'application/pdf' });
    const bad = new File(['hi'], 'notes.txt', { type: 'text/plain' });
    Object.defineProperty(input, 'files', { value: [good, bad], configurable: true });
    input.dispatchEvent(new Event('change'));
    await fixture.whenStable();

    expect(api['upload']).toHaveBeenCalledTimes(1);
    expect(api['upload']).toHaveBeenCalledWith('m10', good, 'e1');
    expect(el.querySelector('[role=alert]')?.textContent).toContain('notes.txt');
  });

  it('opens and downloads through signed links', async () => {
    await render();
    const assign = vi.spyOn(TestBed.inject(FileOpener), 'go');
    const tab = { opener: {}, location: { href: '' }, close: vi.fn() };
    vi.spyOn(window, 'open').mockReturnValue(tab as unknown as Window);

    el.querySelector<HTMLButtonElement>('[aria-label="View groceries.pdf"]')!.click();
    expect(api['url']).toHaveBeenCalledWith('r1');
    expect(tab.location.href).toBe('https://s3/signed');
    expect(tab.opener).toBeNull();

    el.querySelector<HTMLButtonElement>('[aria-label="Download groceries.pdf"]')!.click();
    expect(api['url']).toHaveBeenCalledWith('r1', true);
    expect(assign).toHaveBeenCalledWith('https://s3/signed');
  });

  it('deletes with Undo', async () => {
    await render();
    el.querySelector<HTMLButtonElement>('[aria-label="Delete groceries.pdf"]')!.click();
    await fixture.whenStable();
    expect(api['remove']).toHaveBeenCalledWith('r1');
    expect(names()).toEqual(['rent.png']);
    expect(el.querySelector('.file--deleted')?.textContent).toContain('groceries.pdf deleted');

    // Undo is in the dialog: a toast would sit behind it.
    el.querySelector<HTMLButtonElement>('.file--deleted button')!.click();
    await fixture.whenStable();
    expect(api['restore']).toHaveBeenCalledWith('r1');
    expect(el.querySelector('.file--deleted')).toBeNull();
  });

  it('only shows receipts in a closed month', async () => {
    await render({ closed: true });
    expect(el.querySelector('input[type=file]')).toBeNull();
    expect(el.querySelector('[aria-label^="Delete"]')).toBeNull();
    expect(el.textContent).toContain('The month is closed');
  });
});
