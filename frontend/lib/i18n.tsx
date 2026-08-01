'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'

export type Language = 'pt-BR' | 'en' | 'es'

export const SUPPORTED_LANGUAGES: { code: Language; label: string }[] = [
  { code: 'pt-BR', label: 'Português' },
  { code: 'en', label: 'English' },
  { code: 'es', label: 'Español' },
]

// Cobre só as telas de maior tráfego do lado do cliente final (login/cadastro,
// carrinho, checkout, meus pedidos) -- conteúdo que o próprio dono escreve
// (nome/descrição de item, textos livres) não é traduzido automaticamente,
// continua como o dono escreveu. Escopo deliberadamente básico: dá pra
// estender adicionando mais chaves aqui, sem mudar a infraestrutura.
const translations: Record<Language, Record<string, string>> = {
  'pt-BR': {
    'auth.login_tab': 'Entrar',
    'auth.register_tab': 'Cadastrar',
    'auth.name': 'Nome',
    'auth.email': 'Email',
    'auth.password': 'Senha',
    'auth.submit_login': 'Entrar',
    'auth.submit_register': 'Cadastrar',
    'auth.submit_loading': 'Aguarde...',
    'auth.facebook': 'Continuar com Facebook',
    'auth.logout': 'Sair',
    'auth.edit_profile': 'Editar perfil',
    'auth.cancel': 'Cancelar',
    'auth.greeting': 'Olá',
    'cart.title': 'Carrinho',
    'cart.empty': 'Seu carrinho está vazio',
    'cart.checkout': 'Finalizar pedido',
    'cart.subtotal': 'Subtotal',
    'checkout.name': 'Nome',
    'checkout.phone': 'Telefone',
    'checkout.address': 'Endereço',
    'checkout.submit': 'Confirmar pedido',
    'checkout.sending': 'Enviando...',
    'orders.title': 'Meus Pedidos',
    'orders.empty': 'Você ainda não fez nenhum pedido.',
  },
  en: {
    'auth.login_tab': 'Log in',
    'auth.register_tab': 'Sign up',
    'auth.name': 'Name',
    'auth.email': 'Email',
    'auth.password': 'Password',
    'auth.submit_login': 'Log in',
    'auth.submit_register': 'Sign up',
    'auth.submit_loading': 'Please wait...',
    'auth.facebook': 'Continue with Facebook',
    'auth.logout': 'Log out',
    'auth.edit_profile': 'Edit profile',
    'auth.cancel': 'Cancel',
    'auth.greeting': 'Hello',
    'cart.title': 'Cart',
    'cart.empty': 'Your cart is empty',
    'cart.checkout': 'Checkout',
    'cart.subtotal': 'Subtotal',
    'checkout.name': 'Name',
    'checkout.phone': 'Phone',
    'checkout.address': 'Address',
    'checkout.submit': 'Confirm order',
    'checkout.sending': 'Sending...',
    'orders.title': 'My Orders',
    'orders.empty': "You haven't placed any orders yet.",
  },
  es: {
    'auth.login_tab': 'Iniciar sesión',
    'auth.register_tab': 'Registrarse',
    'auth.name': 'Nombre',
    'auth.email': 'Correo electrónico',
    'auth.password': 'Contraseña',
    'auth.submit_login': 'Iniciar sesión',
    'auth.submit_register': 'Registrarse',
    'auth.submit_loading': 'Espere...',
    'auth.facebook': 'Continuar con Facebook',
    'auth.logout': 'Salir',
    'auth.edit_profile': 'Editar perfil',
    'auth.cancel': 'Cancelar',
    'auth.greeting': 'Hola',
    'cart.title': 'Carrito',
    'cart.empty': 'Tu carrito está vacío',
    'cart.checkout': 'Finalizar compra',
    'cart.subtotal': 'Subtotal',
    'checkout.name': 'Nombre',
    'checkout.phone': 'Teléfono',
    'checkout.address': 'Dirección',
    'checkout.submit': 'Confirmar pedido',
    'checkout.sending': 'Enviando...',
    'orders.title': 'Mis pedidos',
    'orders.empty': 'Todavía no has hecho ningún pedido.',
  },
}

function languageStorageKey(appId: string) {
  return `app_language_${appId}`
}

export function getStoredLanguage(appId: string): Language {
  if (typeof window === 'undefined') return 'pt-BR'
  const saved = localStorage.getItem(languageStorageKey(appId))
  return saved === 'en' || saved === 'es' || saved === 'pt-BR' ? saved : 'pt-BR'
}

export function setStoredLanguage(appId: string, language: Language) {
  if (typeof window === 'undefined') return
  localStorage.setItem(languageStorageKey(appId), language)
}

export function translate(language: Language, key: string): string {
  return translations[language]?.[key] ?? translations['pt-BR'][key] ?? key
}

interface LanguageContextValue {
  language: Language
  setLanguage: (lang: Language) => void
  t: (key: string) => string
}

const LanguageContext = createContext<LanguageContextValue>({
  language: 'pt-BR',
  setLanguage: () => {},
  t: (key: string) => translate('pt-BR', key),
})

export function LanguageProvider({ appId, children }: { appId: string; children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>('pt-BR')

  useEffect(() => {
    setLanguageState(getStoredLanguage(appId))
  }, [appId])

  const setLanguage = (lang: Language) => {
    setLanguageState(lang)
    setStoredLanguage(appId, lang)
  }

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t: (key: string) => translate(language, key) }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  return useContext(LanguageContext)
}
