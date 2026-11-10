import { inject } from '@angular/core';
import { Router, Routes } from '@angular/router';

import { authGuard } from './core/auth/auth.guards';
import { currentMonthPath } from './features/month/month-route';

export const routes: Routes = [
  { path: 'auth', loadChildren: () => import('./features/auth/auth.routes') },
  // Links in emails: the query string carries the token, so it must survive the redirect.
  {
    path: 'verify-email',
    redirectTo: ({ queryParams }) =>
      inject(Router).createUrlTree(['/auth/verify-email'], { queryParams }),
  },
  {
    path: 'reset-password',
    redirectTo: ({ queryParams }) =>
      inject(Router).createUrlTree(['/auth/reset-password'], { queryParams }),
  },
  {
    path: '',
    loadComponent: () => import('./core/layout/shell').then((m) => m.Shell),
    canActivate: [authGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: () => currentMonthPath() },
      { path: 'month', pathMatch: 'full', redirectTo: () => currentMonthPath() },
      {
        path: 'month/:year/:month',
        title: 'Month',
        loadComponent: () => import('./features/month/month-page'),
      },
      {
        path: 'reports',
        title: 'Reports',
        loadComponent: () => import('./features/reports/reports-page'),
      },
      {
        path: 'account',
        title: 'Account',
        loadComponent: () => import('./features/account/account-page'),
      },
      {
        path: 'preferences',
        title: 'Preferences',
        loadComponent: () => import('./features/account/preferences-page'),
      },
      {
        path: 'goals',
        title: 'Goals',
        loadComponent: () => import('./features/goals/goals-page'),
      },
      {
        path: 'labels',
        title: 'Labels',
        loadComponent: () => import('./features/labels/labels-page'),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
