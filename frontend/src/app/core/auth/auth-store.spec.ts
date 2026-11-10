import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { AuthStore } from './auth-store';
import { authInterceptor } from './auth.interceptor';
import { API, tokens, USER } from './testing';

describe('AuthStore', () => {
  let store: AuthStore;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    store = TestBed.inject(AuthStore);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function flushRefresh(token = 'refreshed') {
    const req = http.expectOne(`${API}/auth/refresh`);
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);
    req.flush(tokens(token));
  }

  it('logs in, keeps the token in memory and loads the user', async () => {
    const result = firstValueFrom(store.login({ email: USER.email, password: 'secret123' }));

    const login = http.expectOne(`${API}/auth/login`);
    expect(login.request.body).toEqual({ email: USER.email, password: 'secret123' });
    expect(login.request.withCredentials).toBe(true);
    login.flush(tokens('access-1'));

    const me = http.expectOne(`${API}/users/me`);
    expect(me.request.headers.get('Authorization')).toBe('Bearer access-1');
    me.flush(USER);

    expect(await result).toEqual(USER);
    expect(store.isAuthenticated()).toBe(true);
    expect(store.user()).toEqual(USER);
  });

  it('registers then signs in with the same credentials', async () => {
    const result = firstValueFrom(
      store.register({ email: USER.email, password: 'secret123', name: 'Ana' }),
    );

    const register = http.expectOne(`${API}/auth/register`);
    expect(register.request.body).toEqual({
      email: USER.email,
      password: 'secret123',
      name: 'Ana',
    });
    register.flush(USER, { status: 201, statusText: 'Created' });

    http.expectOne(`${API}/auth/login`).flush(tokens('access-1'));
    http.expectOne(`${API}/users/me`).flush(USER);

    expect(await result).toEqual(USER);
    expect(store.accessToken()).toBe('access-1');
  });

  async function signIn() {
    const done = firstValueFrom(store.login({ email: USER.email, password: 'Old-pass-1!' }));
    http.expectOne(`${API}/auth/login`).flush(tokens('access-1'));
    http.expectOne(`${API}/users/me`).flush(USER);
    await done;
  }

  it('saves the profile and keeps the new user', async () => {
    await signIn();
    const result = firstValueFrom(store.updateProfile({ name: 'Ana Silva' }));
    const patch = http.expectOne(`${API}/users/me`);
    expect(patch.request.method).toBe('PATCH');
    expect(patch.request.body).toEqual({ name: 'Ana Silva' });
    patch.flush({ ...USER, name: 'Ana Silva' });
    await result;
    expect(store.user()?.name).toBe('Ana Silva');
  });

  it('changes the password, then signs this session in again with it', async () => {
    await signIn();
    const result = firstValueFrom(store.changePassword('Old-pass-1!', 'New-pass-2!'));
    const change = http.expectOne(`${API}/users/me/password`);
    expect(change.request.body).toEqual({
      current_password: 'Old-pass-1!',
      new_password: 'New-pass-2!',
    });
    change.flush(null, { status: 204, statusText: 'No Content' });
    const login = http.expectOne(`${API}/auth/login`);
    expect(login.request.body).toEqual({ email: USER.email, password: 'New-pass-2!' });
    login.flush(tokens('access-2'));
    http.expectOne(`${API}/users/me`).flush(USER);
    await result;
    expect(store.accessToken()).toBe('access-2');
  });

  it('signs out the other devices with the refresh cookie', async () => {
    await signIn();
    const result = firstValueFrom(store.logoutOthers(), { defaultValue: undefined });
    const request = http.expectOne(`${API}/auth/logout-others`);
    expect(request.request.withCredentials).toBe(true);
    request.flush(null, { status: 204, statusText: 'No Content' });
    await result;
    expect(store.isAuthenticated()).toBe(true);
  });

  it('confirms the email and reloads a signed-in user to show it', async () => {
    await signIn();
    const result = firstValueFrom(store.verifyEmail('tok'));
    const verify = http.expectOne(`${API}/auth/verify-email`);
    expect(verify.request.body).toEqual({ token: 'tok' });
    verify.flush(null);
    http.expectOne(`${API}/users/me`).flush({ ...USER, email_verified_at: '2026-11-10T00:00:00Z' });
    await result;
    expect(store.user()?.email_verified_at).toBe('2026-11-10T00:00:00Z');
  });

  it('confirms the email without a session too', async () => {
    const result = firstValueFrom(store.verifyEmail('tok'));
    http.expectOne(`${API}/auth/verify-email`).flush(null);
    await result;
    http.expectNone(`${API}/users/me`);
  });

  it('deletes the account with the password, clears the session and goes to sign in', async () => {
    await signIn();
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    const result = firstValueFrom(store.deleteAccount('Secret-1'));
    const request = http.expectOne(`${API}/users/me`);
    expect(request.request.method).toBe('DELETE');
    expect(request.request.body).toEqual({ password: 'Secret-1' });
    expect(request.request.withCredentials).toBe(true);
    request.flush(null);
    await result;
    expect(store.isAuthenticated()).toBe(false);
    expect(navigate).toHaveBeenCalledWith('/auth/login');
  });

  it('does not log in when the credentials are rejected', async () => {
    const result = firstValueFrom(store.login({ email: USER.email, password: 'wrong' }));
    http
      .expectOne(`${API}/auth/login`)
      .flush({ detail: 'Invalid credentials' }, { status: 401, statusText: 'Unauthorized' });

    await expect(result).rejects.toMatchObject({ status: 401 });
    expect(store.isAuthenticated()).toBe(false);
  });

  it('shares a single refresh request between concurrent callers', async () => {
    const a = firstValueFrom(store.refresh());
    const b = firstValueFrom(store.refresh());

    flushRefresh('new-token');

    expect(await a).toBe('new-token');
    expect(await b).toBe('new-token');
    expect(store.accessToken()).toBe('new-token');
  });

  it('restores the session from the refresh cookie only once', async () => {
    const first = firstValueFrom(store.restoreSession());
    flushRefresh();
    http.expectOne(`${API}/users/me`).flush(USER);

    expect(await first).toBe(true);
    expect(await firstValueFrom(store.restoreSession())).toBe(true);
    expect(store.user()).toEqual(USER);
  });

  it('reports no session when the refresh cookie is missing, without retrying', async () => {
    const first = firstValueFrom(store.restoreSession());
    http.expectOne(`${API}/auth/refresh`).flush(null, { status: 401, statusText: 'Unauthorized' });

    expect(await first).toBe(false);
    expect(await firstValueFrom(store.restoreSession())).toBe(false);
    expect(store.sessionExpired()).toBe(false);
  });

  it('logs out, clears the session and goes to the login page', async () => {
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    store.login({ email: USER.email, password: 'secret123' }).subscribe();
    http.expectOne(`${API}/auth/login`).flush(tokens('access-1'));
    http.expectOne(`${API}/users/me`).flush(USER);

    const done = firstValueFrom(store.logout(), { defaultValue: undefined });
    const logout = http.expectOne(`${API}/auth/logout`);
    expect(logout.request.withCredentials).toBe(true);
    logout.flush(null, { status: 204, statusText: 'No Content' });
    await done;

    expect(store.isAuthenticated()).toBe(false);
    expect(store.user()).toBeNull();
    expect(navigate).toHaveBeenCalledWith('/auth/login');
    // No refresh attempt after an explicit logout.
    expect(await firstValueFrom(store.restoreSession())).toBe(false);
  });

  it('still clears the session locally when the logout request fails', async () => {
    vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    const done = firstValueFrom(store.logout(), { defaultValue: undefined });
    http.expectOne(`${API}/auth/logout`).error(new ProgressEvent('error'));
    await done;

    expect(store.isAuthenticated()).toBe(false);
  });
});
