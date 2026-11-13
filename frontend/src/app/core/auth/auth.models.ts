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
  /** False for accounts created with Google only. */
  has_password: boolean;
  google_linked: boolean;
  two_factor_enabled: boolean;
  /** Set on demo accounts, which are deleted at this moment. */
  demo_expires_at: string | null;
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

/** Login answer when the account has two-factor sign-in on. */
export interface TwoFactorRequired {
  two_factor_required: true;
  ticket: string;
  expires_in: number;
}

/** Signed in, or waiting for the two-factor code (with the ticket to send it with). */
export type SignInResult = { user: UserRead } | { ticket: string };

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
