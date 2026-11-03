/** Shapes from the "Authentication API contract" in docs/DECISIONS.md. */

export interface UserRead {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  currency: string;
  locale: string;
  timezone: string;
  email_verified_at: string | null;
  /** Create each month automatically from the previous one. */
  auto_new_month: boolean;
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

export interface ProfileUpdate {
  name?: string;
  timezone?: string;
  auto_new_month?: boolean;
}
