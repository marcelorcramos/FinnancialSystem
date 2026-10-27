import { Routes } from '@angular/router';

import { authGuard } from './core/auth/auth.guards';

export const routes: Routes = [
  { path: 'auth', loadChildren: () => import('./features/auth/auth.routes') },
  {
    path: '',
    loadComponent: () => import('./core/layout/shell').then((m) => m.Shell),
    canActivate: [authGuard],
    children: [
      { path: '', title: 'Month', loadComponent: () => import('./features/home/home-page') },
    ],
  },
  { path: '**', redirectTo: '' },
];
