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
    expect(register.request.body).toEqual({ email: USER.email, password: 'secret123', name: 'Ana' });
    register.flush(USER, { status: 201, statusText: 'Created' });

    http.expectOne(`${API}/auth/login`).flush(tokens('access-1'));
    http.expectOne(`${API}/users/me`).flush(USER);

    expect(await result).toEqual(USER);
    expect(store.accessToken()).toBe('access-1');
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
    http
      .expectOne(`${API}/auth/refresh`)
      .flush(null, { status: 401, statusText: 'Unauthorized' });

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
