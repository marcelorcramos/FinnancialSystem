import { Routes } from '@angular/router';

import { authGuard } from './core/auth/auth.guards';
import { currentMonthPath } from './features/month/month-route';

export const routes: Routes = [
  { path: 'auth', loadChildren: () => import('./features/auth/auth.routes') },
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
        path: 'labels',
        title: 'Labels',
        loadComponent: () => import('./features/labels/labels-page'),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
