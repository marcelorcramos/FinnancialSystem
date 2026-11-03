import { TokenResponse, UserRead } from './auth.models';

export const API = '/api/v1';

export const USER: UserRead = {
  id: '3f0b8a52-8f1e-4a55-9a3f-1b1f2d3c4e5f',
  email: 'ana@example.com',
  name: 'Ana',
  avatar_url: null,
  currency: 'EUR',
  locale: 'pt-PT',
  timezone: 'Europe/Lisbon',
  email_verified_at: null,
  auto_new_month: false,
};

export function tokens(accessToken: string): TokenResponse {
  return { access_token: accessToken, token_type: 'bearer', expires_in: 900 };
}
