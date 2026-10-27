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
      { path: '', pathMatch: 'full', redirectTo: 'login' },
    ],
  },
] satisfies Routes;
