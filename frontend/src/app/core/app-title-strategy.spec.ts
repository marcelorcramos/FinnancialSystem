import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Title } from '@angular/platform-browser';
import { provideRouter, Router, TitleStrategy } from '@angular/router';

import { AppTitleStrategy } from './app-title-strategy';

@Component({ template: '' })
class Blank {}

describe('AppTitleStrategy', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: 'labels', title: 'Labels', component: Blank },
          { path: 'untitled', component: Blank },
        ]),
        { provide: TitleStrategy, useClass: AppTitleStrategy },
      ],
    });
  });

  it('adds the app name after the page title', async () => {
    await TestBed.inject(Router).navigateByUrl('/labels');
    expect(TestBed.inject(Title).getTitle()).toBe('Labels · FinnancialSystem');
  });

  it('uses only the app name when the route has no title', async () => {
    await TestBed.inject(Router).navigateByUrl('/untitled');
    expect(TestBed.inject(Title).getTitle()).toBe('FinnancialSystem');
  });
});
