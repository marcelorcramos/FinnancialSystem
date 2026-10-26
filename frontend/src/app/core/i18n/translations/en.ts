import type { Translation } from './pt';

export const en: Translation = {
  app: {
    name: 'FinnancialSystem',
    skipToContent: 'Skip to content',
  },
  kind: {
    expense: 'Expense',
    saving: 'Saving',
    investment: 'Investment',
  },
  nav: {
    home: 'Home',
    openMenu: 'Open menu',
    mainNavigation: 'Main navigation',
  },
  theme: {
    label: 'Theme',
    light: 'Light',
    dark: 'Dark',
    system: 'System',
  },
  language: {
    label: 'Language',
    pt: 'Português',
    en: 'English',
  },
  user: {
    menu: 'Account',
    logout: 'Sign out',
  },
  home: {
    greeting: 'Hello, {{name}}',
    intro: 'Your months, labels and charts will show up here.',
  },
  auth: {
    email: 'Email',
    password: 'Password',
    confirmPassword: 'Confirm password',
    name: 'Name',
    showPassword: 'Show password',
    hidePassword: 'Hide password',
    login: {
      title: 'Sign in',
      subtitle: 'Track your money month by month.',
      submit: 'Sign in',
      noAccount: "Don't have an account?",
      goToRegister: 'Create account',
    },
    register: {
      title: 'Create account',
      subtitle: 'Start organising your months today.',
      submit: 'Create account',
      hasAccount: 'Already have an account?',
      goToLogin: 'Sign in',
    },
    errors: {
      invalidCredentials: 'Incorrect email or password.',
      emailTaken: 'An account with this email already exists.',
      invalidData: 'Please check the data you entered.',
      network: 'Could not reach the server. Please try again.',
      unknown: 'Something went wrong. Please try again.',
      sessionExpired: 'Your session has expired. Please sign in again.',
    },
  },
  validation: {
    required: 'This field is required.',
    email: 'Enter a valid email.',
    minLength: 'At least {{min}} characters.',
    maxLength: 'At most {{max}} characters.',
    passwordMismatch: 'Passwords do not match.',
  },
};
