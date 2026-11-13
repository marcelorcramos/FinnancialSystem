import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { of } from 'rxjs';

import { AuthStore } from '../../../core/auth/auth-store';
import GoogleDonePage from './google-done-page';

describe('GoogleDonePage', () => {
  async function render(signedIn: boolean) {
    TestBed.configureTestingModule({
      imports: [GoogleDonePage],
      providers: [
        provideRouter([]),
        { provide: AuthStore, useValue: { restoreSession: () => of(signedIn) } },
      ],
    });
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    const fixture = TestBed.createComponent(GoogleDonePage);
    await fixture.whenStable();
    return navigate;
  }

  it('picks up the session Google started and enters the app', async () => {
    expect(await render(true)).toHaveBeenCalledWith('/');
  });

  it('goes back to sign in with an error when there is no session', async () => {
    const navigate = await render(false);
    expect(String(navigate.mock.calls[0]![0])).toBe('/auth/login?error=google');
  });
});
