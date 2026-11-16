import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { API } from '../auth/testing';
import { AssistantService } from './assistant.service';

describe('AssistantService', () => {
  let service: AssistantService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AssistantService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('asks the server once whether the assistant is on', () => {
    expect(service.enabled()).toBeNull();
    service.checkStatus();
    service.checkStatus();
    http.expectOne(`${API}/assistant/status`).flush({ enabled: true });
    expect(service.enabled()).toBe(true);
  });

  it('treats an unreachable server as off', () => {
    service.checkStatus();
    http.expectOne(`${API}/assistant/status`).flush(null, { status: 500, statusText: 'Error' });
    expect(service.enabled()).toBe(false);
  });

  it('sends a question, continuing a conversation when given', () => {
    service.ask('How much?', null).subscribe();
    expect(http.expectOne(`${API}/assistant/questions`).request.body).toEqual({
      text: 'How much?',
    });
    service.ask('And Food?', 'c1').subscribe();
    expect(http.expectOne(`${API}/assistant/questions`).request.body).toEqual({
      text: 'And Food?',
      conversation_id: 'c1',
    });
  });
});
