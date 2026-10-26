import { BreakpointObserver } from '@angular/cdk/layout';
import { computed, inject, Injectable } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { map } from 'rxjs';

import { PHONE_QUERY, ScreenSize, TABLET_QUERY } from './breakpoints';

/** Current screen size (phone, tablet, desktop) as a signal. */
@Injectable({ providedIn: 'root' })
export class ScreenService {
  private readonly observer = inject(BreakpointObserver);

  readonly size = toSignal(
    this.observer.observe([PHONE_QUERY, TABLET_QUERY]).pipe(
      map((state): ScreenSize => {
        if (state.breakpoints[PHONE_QUERY]) return 'phone';
        if (state.breakpoints[TABLET_QUERY]) return 'tablet';
        return 'desktop';
      }),
    ),
    { initialValue: 'desktop' as ScreenSize },
  );

  readonly isPhone = computed(() => this.size() === 'phone');
  readonly isTablet = computed(() => this.size() === 'tablet');
}
