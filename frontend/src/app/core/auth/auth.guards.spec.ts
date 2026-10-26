import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { authGuard, guestGuard, safeReturnUrl } from './auth.guards';
import { API, tokens, USER } from './testing';

@Component({ template: 'home' })
class HomeStub {}

@Component({ template: 'login' })
class LoginStub {}

describe('auth guards', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: '', component: HomeStub, canActivate: [authGuard] },
          { path: 'months', component: HomeStub, canActivate: [authGuard] },
          { path: 'auth/login', component: LoginStub, canActivate: [guestGuard] },
        ]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  async function navigate(url: string, respond: () => void) {
    const harness = await RouterTestingHarness.create();
    const navigation = harness.navigateByUrl(url);
    // Let the router reach the guard, which then waits on the refresh call.
    await new Promise((resolve) => setTimeout(resolve));
    respond();
    await navigation;
    return TestBed.inject(Router).url;
  }

  const noSession = () =>
    http
      .expectOne(`${API}/auth/refresh`)
      .flush(null, { status: 401, statusText: 'Unauthorized' });

  const validSession = () => {
    http.expectOne(`${API}/auth/refresh`).flush(tokens('access'));
    http.expectOne(`${API}/users/me`).flush(USER);
  };

  it('sends anonymous users to login, keeping the return URL', async () => {
    expect(await navigate('/months', noSession)).toBe('/auth/login?returnUrl=%2Fmonths');
  });

  it('lets users with a valid refresh cookie in', async () => {
    expect(await navigate('/months', validSession)).toBe('/months');
  });

  it('keeps signed-in users away from the login page', async () => {
    expect(await navigate('/auth/login', validSession)).toBe('/');
  });

  it('shows the login page to anonymous users', async () => {
    expect(await navigate('/auth/login', noSession)).toBe('/auth/login');
  });
});

describe('safeReturnUrl', () => {
  it('accepts in-app paths', () => {
    expect(safeReturnUrl('/months?year=2026')).toBe('/months?year=2026');
  });

  it.each([null, undefined, '', 'https://evil.example', '//evil.example', '/auth/login'])(
    'falls back to / for %s',
    (value) => {
      expect(safeReturnUrl(value)).toBe('/');
    },
  );
});
