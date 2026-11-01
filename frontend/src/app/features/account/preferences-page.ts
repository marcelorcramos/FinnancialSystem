import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import {
  DisplayPreferences,
  DisplayPreferencesService,
  TEXT_SIZES,
  TextSize,
} from '../../core/preferences/display-preferences';
import { THEME_MODES, ThemeMode, ThemeService } from '../../core/theme/theme.service';

const THEME_NAMES: Record<ThemeMode, string> = { dark: 'Dark', light: 'Light', system: 'System' };
const SIZE_NAMES: Record<TextSize, string> = {
  default: 'Default',
  large: 'Large',
  larger: 'Larger',
};

type Switch = Exclude<keyof DisplayPreferences, 'textSize'>;

const SWITCHES: { key: Switch; title: string; help: string }[] = [
  { key: 'reduceMotion', title: 'Reduce motion', help: 'Turns off chart and hover animations.' },
  { key: 'highContrast', title: 'High contrast', help: 'Stronger borders and brighter text.' },
  {
    key: 'patterns',
    title: 'Patterns in charts',
    help: 'Adds stripes and dots so kinds never rely on colour alone.',
  },
];

/** Theme, text size and accessibility options, kept in this browser. */
@Component({
  selector: 'app-preferences-page',
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './preferences-page.html',
  styleUrl: './preferences-page.scss',
})
export default class PreferencesPage {
  private readonly theme = inject(ThemeService);
  private readonly display = inject(DisplayPreferencesService);

  protected readonly themes = THEME_MODES.map((mode) => ({ mode, name: THEME_NAMES[mode] }));
  protected readonly sizes = TEXT_SIZES.map((size) => ({ size, name: SIZE_NAMES[size] }));
  protected readonly switches = SWITCHES;
  protected readonly mode = this.theme.mode;
  protected readonly current = this.display.current;
  protected readonly motionText = computed(() =>
    this.current().reduceMotion
      ? 'Animations off.'
      : 'Animations on: slices and points react on hover.',
  );

  protected setTheme(mode: ThemeMode): void {
    this.theme.setMode(mode);
  }

  protected setSize(size: TextSize): void {
    this.display.set('textSize', size);
  }

  protected toggle(key: Switch): void {
    this.display.set(key, !this.current()[key]);
  }
}
