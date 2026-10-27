import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';

import { Icon, IconName } from '../../shared/ui/icon';
import { THEME_MODES, ThemeMode, ThemeService } from '../theme/theme.service';

const MODES: Record<ThemeMode, { name: string; icon: IconName }> = {
  dark: { name: 'Dark', icon: 'moon' },
  light: { name: 'Light', icon: 'sun' },
  system: { name: 'System', icon: 'contrast' },
};

/** One button that cycles the theme: dark → light → system. */
@Component({
  selector: 'app-theme-toggle',
  imports: [Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <button
      type="button"
      class="btn btn--icon btn--quiet"
      [attr.aria-label]="label()"
      [attr.title]="label()"
      (click)="next()"
    >
      <app-icon [name]="current().icon" />
    </button>
  `,
})
export class ThemeToggle {
  private readonly theme = inject(ThemeService);

  protected readonly current = computed(() => MODES[this.theme.mode()]);
  private readonly following = computed(() => {
    const index = THEME_MODES.indexOf(this.theme.mode());
    return THEME_MODES[(index + 1) % THEME_MODES.length];
  });
  protected readonly label = computed(
    () => `Theme: ${this.current().name}. Switch to ${MODES[this.following()].name}`,
  );

  protected next(): void {
    this.theme.setMode(this.following());
  }
}
