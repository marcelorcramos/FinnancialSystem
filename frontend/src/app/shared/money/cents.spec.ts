import { fromCents, signedCents, toCents } from './cents';

describe('cents', () => {
  it('reads typed amounts without floats', () => {
    expect(toCents('220')).toBe(22000);
    expect(toCents('220.5')).toBe(22050);
    expect(toCents('220,05')).toBe(22005);
    expect(toCents(' 0.10 ')).toBe(10);
    expect(toCents('999999999999.99')).toBe(99999999999999);
  });

  it('accepts a trailing separator while typing', () => {
    expect(toCents('12.')).toBe(1200);
  });

  it.each(['', 'abc', '-5', '1.234', '1e3', '1 000'])('rejects %j', (text) => {
    expect(toCents(text)).toBeNull();
  });

  it('writes the API decimal string', () => {
    expect(fromCents(22050)).toBe('220.50');
    expect(fromCents(5)).toBe('0.05');
    expect(fromCents(0)).toBe('0.00');
    expect(fromCents(-1200)).toBe('-12.00');
  });
});

describe('signedCents', () => {
  it('reads API values, negative ones included', () => {
    expect(signedCents('288.00')).toBe(28800);
    expect(signedCents('-12.50')).toBe(-1250);
    expect(signedCents('x')).toBeNull();
  });
});
