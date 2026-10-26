import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { AuthStore } from './auth-store';
import { authInterceptor } from './auth.interceptor';
import { API, tokens, USER } from './testing';

describe('authInterceptor', () => {
  let http: HttpTestingController;
  let client: HttpClient;
  let store: AuthStore;
  let navigate: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpTestingController);
    client = TestBed.inject(HttpClient);
    store = TestBed.inject(AuthStore);
    navigate = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
  });

  afterEach(() => http.verify());

  function signIn(token = 'access-1') {
    store.login({ email: USER.email, password: 'secret123' }).subscribe();
    http.expectOne(`${API}/auth/login`).flush(tokens(token));
    http.expectOne(`${API}/users/me`).flush(USER);
  }

  const unauthorized = { status: 401, statusText: 'Unauthorized' };

  it('sends the access token as a Bearer header to the API', () => {
    signIn();
    client.get(`${API}/months`).subscribe();

    const req = http.expectOne(`${API}/months`);
    expect(req.request.headers.get('Authorization')).toBe('Bearer access-1');
    req.flush([]);
  });

  it('does not send the token to other origins', () => {
    signIn();
    client.get('https://example.com/data').subscribe();

    const req = http.expectOne('https://example.com/data');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({});
  });

  it('refreshes on 401 and retries the request with the new token', async () => {
    signIn('expired');
    const result = firstValueFrom(client.get(`${API}/months`));

    http.expectOne(`${API}/months`).flush(null, unauthorized);
    const refresh = http.expectOne(`${API}/auth/refresh`);
    expect(refresh.request.withCredentials).toBe(true);
    refresh.flush(tokens('fresh'));

    const retry = http.expectOne(`${API}/months`);
    expect(retry.request.headers.get('Authorization')).toBe('Bearer fresh');
    retry.flush(['ok']);

    expect(await result).toEqual(['ok']);
    expect(store.accessToken()).toBe('fresh');
  });

  it('refreshes once for several requests failing together', async () => {
    signIn('expired');
    const a = firstValueFrom(client.get(`${API}/a`));
    const b = firstValueFrom(client.get(`${API}/b`));

    http.expectOne(`${API}/a`).flush(null, unauthorized);
    http.expectOne(`${API}/b`).flush(null, unauthorized);
    http.expectOne(`${API}/auth/refresh`).flush(tokens('fresh'));

    http.expectOne(`${API}/a`).flush('A');
    http.expectOne(`${API}/b`).flush('B');
    expect([await a, await b]).toEqual(['A', 'B']);
  });

  it('expires the session and redirects to login when the refresh fails', async () => {
    signIn('expired');
    const result = firstValueFrom(client.get(`${API}/months`));

    http.expectOne(`${API}/months`).flush(null, unauthorized);
    http.expectOne(`${API}/auth/refresh`).flush(null, unauthorized);

    await expect(result).rejects.toMatchObject({ status: 401 });
    expect(store.isAuthenticated()).toBe(false);
    expect(store.sessionExpired()).toBe(true);
    expect(navigate).toHaveBeenCalledWith(['/auth/login'], expect.anything());
  });

  it('does not refresh again when the retried request fails with 401', async () => {
    signIn('expired');
    const result = firstValueFrom(client.get(`${API}/months`));

    http.expectOne(`${API}/months`).flush(null, unauthorized);
    http.expectOne(`${API}/auth/refresh`).flush(tokens('fresh'));
    http.expectOne(`${API}/months`).flush(null, unauthorized);

    await expect(result).rejects.toMatchObject({ status: 401 });
  });

  it('passes other errors through without refreshing', async () => {
    signIn();
    const result = firstValueFrom(client.get(`${API}/months`));
    http.expectOne(`${API}/months`).flush(null, { status: 500, statusText: 'Server Error' });

    await expect(result).rejects.toMatchObject({ status: 500 });
  });

  it('leaves /auth endpoints alone (a 401 on login is bad credentials)', async () => {
    const result = firstValueFrom(client.post(`${API}/auth/login`, {}));
    const req = http.expectOne(`${API}/auth/login`);
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush(null, unauthorized);

    await expect(result).rejects.toMatchObject({ status: 401 });
  });
});
