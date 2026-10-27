import { FormControl } from '@angular/forms';

import { passwordPolicy, passwordRules } from './password-policy';

describe('passwordPolicy', () => {
  const check = (value: string) => passwordPolicy(new FormControl(value, { nonNullable: true }));

  it('accepts a password with lower, upper, digit and symbol', () => {
    expect(check('Segura#2026')).toBeNull();
  });

  it.each(['Ab1!', 'SEGURA#2026', 'segura#2026', 'Segura#Senha', 'Segura2026', 'Segura 2026'])(
    'rejects %s',
    (value) => {
      expect(check(value)).toEqual({ passwordPolicy: true });
    },
  );

  it('leaves empty values to the required validator', () => {
    expect(check('')).toBeNull();
  });
});

describe('passwordRules', () => {
  it('reports each rule separately', () => {
    expect(passwordRules('secure2026').map((rule) => rule.met)).toEqual([
      true,
      true,
      false,
      true,
      false,
    ]);
    expect(passwordRules('Secure#2026').every((rule) => rule.met)).toBe(true);
  });
});
