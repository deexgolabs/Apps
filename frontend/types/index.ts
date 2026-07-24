export interface User {
  id: number
  email: string
  full_name: string
  plan: 'free' | 'pro' | 'business'
  is_active: boolean
  is_verified: boolean
  is_admin: boolean
  created_at: string
}

export interface App {
  id: number
  user_id: number
  name: string
  description: string | null
  template_type: string
  status: 'draft' | 'published'
  config: Record<string, any>
  modules: string[]
  created_at: string
  updated_at: string
}

export interface Module {
  id: number
  name: string
  description: string
  category: string
  icon_url: string | null
  requires_plan: 'free' | 'pro' | 'business'
  features: string[]
}

export interface ModuleCategory {
  id: number
  app_id: number
  module_name: string
  name: string
  order: number
}

export interface ModuleItem {
  id: number
  app_id: number
  module_name: string
  category_id: number | null
  name: string
  description: string | null
  price: number | null
  image_url: string | null
  extra: Record<string, any>
  order: number
}
