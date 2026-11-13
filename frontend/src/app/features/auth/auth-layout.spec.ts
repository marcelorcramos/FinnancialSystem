import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import { AuthStore } from '../../core/auth/auth-store';
import { USER } from '../../core/auth/testing';
import { ToastService } from '../../shared/ui/toast.service';
import { AuthLayout } from './auth-layout';

describe('AuthLayout', () => {
  async function render(reply: unknown) {
    const startDemo = vi.fn(() => reply);
    const show = vi.fn();
    TestBed.configureTestingModule({
      imports: [AuthLayout],
      providers: [
        provideRouter([]),
        { provide: AuthStore, useValue: { startDemo } },
        { provide: ToastService, useValue: { show, toasts: () => [] } },
      ],
    });
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    const fixture = TestBed.createComponent(AuthLayout);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    const button = [...el.querySelectorAll('button')].find((b) =>
      b.textContent?.includes('Try it'),
    )!;
    button.click();
    await fixture.whenStable();
    return { startDemo, navigate, show };
  }

  it('opens a demo account with "Try it"', async () => {
    const { startDemo, navigate } = await render(of(USER));
    expect(startDemo).toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith('/');
  });

  it('says why the demo could not start', async () => {
    const { show } = await render(
      throwError(
        () => new HttpErrorResponse({ status: 429, error: { detail: 'Too many attempts.' } }),
      ),
    );
    expect(show).toHaveBeenCalledWith('Too many attempts.');
  });
});
