import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import {
  ApplicationConfig,
  inject,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import { provideRouter, TitleStrategy, withComponentInputBinding } from '@angular/router';
import { provideEchartsCore } from 'ngx-echarts';

import { routes } from './app.routes';
import { AppTitleStrategy } from './core/app-title-strategy';
import { authInterceptor } from './core/auth/auth.interceptor';
import { DisplayPreferencesService } from './core/preferences/display-preferences';
import { ThemeService } from './core/theme/theme.service';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes, withComponentInputBinding()),
    { provide: TitleStrategy, useClass: AppTitleStrategy },
    provideHttpClient(withFetch(), withInterceptors([authInterceptor])),
    // ECharts is loaded lazily, only when the first chart renders.
    provideEchartsCore({ echarts: () => import('echarts') }),
    provideAppInitializer(() => inject(ThemeService).init()),
    provideAppInitializer(() => inject(DisplayPreferencesService).init()),
  ],
};
