export const pt = {
  app: {
    name: 'FinnancialSystem',
    skipToContent: 'Saltar para o conteúdo',
  },
  kind: {
    expense: 'Gasto',
    saving: 'Poupança',
    investment: 'Investimento',
  },
  nav: {
    home: 'Início',
    openMenu: 'Abrir menu',
    mainNavigation: 'Navegação principal',
  },
  theme: {
    label: 'Tema',
    light: 'Claro',
    dark: 'Escuro',
    system: 'Sistema',
  },
  language: {
    label: 'Idioma',
    pt: 'Português',
    en: 'English',
  },
  user: {
    menu: 'Conta',
    logout: 'Terminar sessão',
  },
  home: {
    greeting: 'Olá, {{name}}',
    intro: 'Os teus meses, etiquetas e gráficos vão aparecer aqui.',
  },
  auth: {
    email: 'Email',
    password: 'Password',
    confirmPassword: 'Confirmar password',
    name: 'Nome',
    showPassword: 'Mostrar password',
    hidePassword: 'Esconder password',
    login: {
      title: 'Entrar',
      subtitle: 'Controla o teu dinheiro mês a mês.',
      submit: 'Entrar',
      noAccount: 'Ainda não tens conta?',
      goToRegister: 'Criar conta',
    },
    register: {
      title: 'Criar conta',
      subtitle: 'Começa já a organizar os teus meses.',
      submit: 'Criar conta',
      hasAccount: 'Já tens conta?',
      goToLogin: 'Entrar',
    },
    errors: {
      invalidCredentials: 'Email ou password incorretos.',
      emailTaken: 'Já existe uma conta com este email.',
      invalidData: 'Verifica os dados introduzidos.',
      network: 'Não foi possível contactar o servidor. Tenta de novo.',
      unknown: 'Ocorreu um erro inesperado. Tenta de novo.',
      sessionExpired: 'A tua sessão expirou. Entra de novo.',
    },
  },
  validation: {
    required: 'Campo obrigatório.',
    email: 'Introduz um email válido.',
    minLength: 'Mínimo de {{min}} caracteres.',
    maxLength: 'Máximo de {{max}} caracteres.',
    passwordMismatch: 'As passwords não coincidem.',
  },
};

export type Translation = typeof pt;
