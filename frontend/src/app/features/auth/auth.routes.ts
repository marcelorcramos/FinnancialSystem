import { Routes } from '@angular/router';

import { guestGuard } from '../../core/auth/auth.guards';
import { AuthLayout } from './auth-layout';

export default [
  {
    path: '',
    component: AuthLayout,
    canActivate: [guestGuard],
    children: [
      { path: 'login', title: 'Sign in', loadComponent: () => import('./login/login-page') },
      {
        path: 'register',
        title: 'Create account',
        loadComponent: () => import('./register/register-page'),
      },
      {
        path: 'forgot-password',
        title: 'Reset password',
        loadComponent: () => import('./forgot-password/forgot-password-page'),
      },
      { path: '', pathMatch: 'full', redirectTo: 'login' },
    ],
  },
  // Opened from emailed links, signed in or not.
  {
    path: '',
    component: AuthLayout,
    children: [
      {
        path: 'reset-password',
        title: 'Choose a new password',
        loadComponent: () => import('./reset-password/reset-password-page'),
      },
      {
        path: 'verify-email',
        title: 'Confirm your email',
        loadComponent: () => import('./verify-email/verify-email-page'),
      },
    ],
  },
] satisfies Routes;
