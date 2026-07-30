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
  client_name: string | null
  client_email: string | null
  template_type: string
  status: 'draft' | 'published'
  config: Record<string, any>
  modules: string[]
  custom_domain: string | null
  custom_domain_verified: boolean
  created_at: string
  updated_at: string
}

export interface CustomDomainStatus {
  domain: string | null
  verified: boolean
  verification_host: string | null
  verification_token: string | null
}

export interface AppVersion {
  id: number
  name: string
  description: string | null
  config: Record<string, any>
  modules: string[]
  created_at: string
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

export interface ItemVariation {
  id: number
  item_id: number
  name: string
  price: number
  stock: number | null
  order: number
  group_name: string | null
}

export interface ItemReview {
  id: number
  item_id: number
  end_user_id: number
  end_user_name: string
  rating: number
  comment: string | null
  created_at: string
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
  stock: number | null
  variations: ItemVariation[]
  avg_rating: number | null
  review_count: number
}

export interface OrderItem {
  id: number
  module_item_id: number | null
  item_variation_id: number | null
  name: string
  unit_price: number
  quantity: number
  subtotal: number
}

export interface OrderStatusEvent {
  id: number
  status: string
  created_at: string
}

export interface Order {
  id: number
  app_id: number
  module_name: string
  end_user_id: number | null
  data: Record<string, any>
  amount: number | null
  subtotal: number | null
  delivery_fee: number | null
  discount_amount: number | null
  coupon_code: string | null
  fulfillment_type: string | null
  table_number: string | null
  payment_method: string | null
  payment_reference: string | null
  status: string
  created_at: string
  updated_at: string
  items: OrderItem[]
  status_events: OrderStatusEvent[]
}
