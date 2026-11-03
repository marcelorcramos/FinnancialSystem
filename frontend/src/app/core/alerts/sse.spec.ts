import { SseParser } from './sse';

describe('SseParser', () => {
  it('returns whole events, keeping partial ones and skipping comments', () => {
    const parser = new SseParser();
    expect(parser.push(': connected\n\n')).toEqual([]);
    expect(parser.push('event: alert\ndata: {"a"')).toEqual([]);
    expect(parser.push(':1}\n\n: ping\n\ndata: plain\r\n\r\n')).toEqual([
      { event: 'alert', data: '{"a":1}' },
      { event: 'message', data: 'plain' },
    ]);
  });

  it('joins multi-line data', () => {
    expect(new SseParser().push('data: one\ndata: two\n\n')).toEqual([
      { event: 'message', data: 'one\ntwo' },
    ]);
  });
});
