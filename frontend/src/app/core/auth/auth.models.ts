/** Shapes from the "Contrato da API de autenticação" in docs/DECISIONS.md. */

export interface UserRead {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  currency: string;
  locale: string;
  timezone: string;
  email_verified_at: string | null;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}
