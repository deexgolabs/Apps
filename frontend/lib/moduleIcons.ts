import {
  FileText, Info, Video, MessageCircle, MapPin, Globe, Radio, Rss, Newspaper,
  Calendar, Images, MessageSquare, Megaphone, Pizza, ShoppingBag, List, Image,
  Building2, Phone, Truck, FileEdit, Camera, Receipt, Package, Lock, Star,
  CalendarDays, CreditCard, Banknote, Bell, ShoppingCart, Heart, Gift, Tag,
  Clock, User, Users, Settings, Home, Award, Zap, Wallet, Music, DollarSign,
  UserPlus, Landmark,
  type LucideIcon,
} from 'lucide-react'

// Ícone padrão por módulo — vetorial (mais profissional/consistente entre
// sistemas que emoji). Sempre pode ser sobrescrito pelo dono do app.
export const MODULE_VECTOR_ICONS: Record<string, LucideIcon> = {
  texto: FileText,
  quem_somos: Info,
  video: Video,
  whatsapp: MessageCircle,
  mapa: MapPin,
  pagina_web: Globe,
  radio_web: Radio,
  rss: Rss,
  wordpress: Newspaper,
  google_agenda: Calendar,
  slider_imagens: Images,
  chat_tawkto: MessageSquare,
  google_admob: Megaphone,
  blog: Newspaper,
  cardapio: Pizza,
  catalogo: ShoppingBag,
  lista_itens: List,
  galeria_imagens: Image,
  guia_empresas: Building2,
  fale_conosco: Phone,
  formulario_delivery: Truck,
  contato_personalizado: FileEdit,
  form_fotos: Camera,
  cotacao: Receipt,
  calculo_frete: Package,
  login_cadastro: Lock,
  cartao_fidelidade: Star,
  agenda_interna: CalendarDays,
  mercado_pago: CreditCard,
  paypal: Wallet,
  pagseguro: Landmark,
  pagamento_entrega: Banknote,
  push_notifications: Bell,
  mercado_livre: ShoppingCart,
}

export const DEFAULT_MODULE_ICON: LucideIcon = Package

// Conjunto curado pro seletor "Ícone" no ModuleSettingsModal — o dono do app
// escolhe qualquer um pra sobrescrever o padrão do módulo.
export const ICON_PICKER_OPTIONS: { name: string; Icon: LucideIcon }[] = [
  { name: 'Pizza', Icon: Pizza },
  { name: 'ShoppingBag', Icon: ShoppingBag },
  { name: 'ShoppingCart', Icon: ShoppingCart },
  { name: 'MessageCircle', Icon: MessageCircle },
  { name: 'MessageSquare', Icon: MessageSquare },
  { name: 'Phone', Icon: Phone },
  { name: 'MapPin', Icon: MapPin },
  { name: 'Calendar', Icon: Calendar },
  { name: 'CalendarDays', Icon: CalendarDays },
  { name: 'Star', Icon: Star },
  { name: 'Heart', Icon: Heart },
  { name: 'Bell', Icon: Bell },
  { name: 'CreditCard', Icon: CreditCard },
  { name: 'Truck', Icon: Truck },
  { name: 'Camera', Icon: Camera },
  { name: 'Image', Icon: Image },
  { name: 'Video', Icon: Video },
  { name: 'Music', Icon: Music },
  { name: 'Gift', Icon: Gift },
  { name: 'Tag', Icon: Tag },
  { name: 'Clock', Icon: Clock },
  { name: 'User', Icon: User },
  { name: 'Users', Icon: Users },
  { name: 'UserPlus', Icon: UserPlus },
  { name: 'Settings', Icon: Settings },
  { name: 'Info', Icon: Info },
  { name: 'Globe', Icon: Globe },
  { name: 'Home', Icon: Home },
  { name: 'Building2', Icon: Building2 },
  { name: 'Package', Icon: Package },
  { name: 'Award', Icon: Award },
  { name: 'Zap', Icon: Zap },
  { name: 'DollarSign', Icon: DollarSign },
]

const ICON_PICKER_BY_NAME: Record<string, LucideIcon> = Object.fromEntries(
  ICON_PICKER_OPTIONS.map(({ name, Icon }) => [name, Icon])
)

export function resolveIconName(name: string): LucideIcon | undefined {
  return ICON_PICKER_BY_NAME[name]
}
