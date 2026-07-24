export interface ModuleField {
  key: string
  label: string
  type: 'text' | 'textarea' | 'url' | 'image'
  placeholder?: string
}

export const MODULE_FIELDS: Record<string, ModuleField[]> = {
  texto: [
    { key: 'titulo', label: 'Título', type: 'text', placeholder: 'Sobre nós' },
    { key: 'conteudo', label: 'Conteúdo', type: 'textarea', placeholder: 'Texto livre...' },
  ],
  quem_somos: [
    { key: 'titulo', label: 'Título', type: 'text', placeholder: 'Quem somos' },
    { key: 'texto', label: 'Texto de apresentação', type: 'textarea' },
    { key: 'imagem_url', label: 'Imagem', type: 'image' },
  ],
  video: [{ key: 'url', label: 'URL do vídeo (YouTube/Vimeo)', type: 'url' }],
  whatsapp: [
    { key: 'numero', label: 'Número (com DDI e DDD)', type: 'text', placeholder: '5511999999999' },
    { key: 'mensagem_padrao', label: 'Mensagem padrão', type: 'textarea' },
  ],
  mapa: [
    { key: 'endereco', label: 'Endereço', type: 'text' },
    { key: 'latitude', label: 'Latitude', type: 'text' },
    { key: 'longitude', label: 'Longitude', type: 'text' },
  ],
  pagina_web: [{ key: 'url', label: 'URL da página', type: 'url' }],
  radio_web: [
    { key: 'stream_url', label: 'URL do stream', type: 'url' },
    { key: 'nome_radio', label: 'Nome da rádio', type: 'text' },
  ],
  rss: [{ key: 'feed_url', label: 'URL do feed RSS', type: 'url' }],
  wordpress: [{ key: 'site_url', label: 'URL do site WordPress', type: 'url' }],
  google_agenda: [{ key: 'calendar_embed_url', label: 'URL de incorporação do calendário', type: 'url' }],
  slider_imagens: [
    { key: 'imagens', label: 'URLs das imagens (uma por linha)', type: 'textarea' },
  ],
  chat_tawkto: [{ key: 'widget_id', label: 'ID do widget Tawk.to', type: 'text' }],
  google_admob: [{ key: 'ad_unit_id', label: 'ID da unidade de anúncio', type: 'text' }],
  calculo_frete: [
    {
      key: 'regras',
      label: 'Regras de frete (prefixo do CEP:preço, uma por linha)',
      type: 'textarea',
      placeholder: '01000:15.00\n02000:20.00',
    },
  ],
  contato_personalizado: [
    {
      key: 'campos',
      label: 'Campos do formulário (um por linha — Rótulo, Rótulo:numero, Rótulo:data — * no fim marca obrigatório)',
      type: 'textarea',
      placeholder: 'Nome*\nTelefone:numero\nData de nascimento:data\nMensagem',
    },
  ],
  cartao_fidelidade: [
    { key: 'titulo', label: 'Título', type: 'text', placeholder: 'Cartão Fidelidade' },
    { key: 'regra', label: 'Regra', type: 'textarea', placeholder: 'A cada compra, ganhe 1 selo' },
    { key: 'total_selos', label: 'Total de selos para o prêmio', type: 'text', placeholder: '10' },
    { key: 'premio', label: 'Prêmio', type: 'text', placeholder: 'Uma sobremesa grátis' },
  ],
  mercado_pago: [
    { key: 'titulo', label: 'Título da cobrança', type: 'text', placeholder: 'Sinal de reserva' },
    { key: 'valor', label: 'Valor (R$)', type: 'text', placeholder: '50.00' },
    { key: 'access_token', label: 'Access Token do Mercado Pago', type: 'text' },
  ],
  paypal: [
    { key: 'titulo', label: 'Título da cobrança', type: 'text', placeholder: 'Sinal de reserva' },
    { key: 'valor', label: 'Valor (R$)', type: 'text', placeholder: '50.00' },
    { key: 'client_id', label: 'Client ID do PayPal', type: 'text' },
    { key: 'client_secret', label: 'Client Secret do PayPal', type: 'text' },
  ],
  pagseguro: [
    { key: 'titulo', label: 'Título da cobrança', type: 'text', placeholder: 'Sinal de reserva' },
    { key: 'valor', label: 'Valor (R$)', type: 'text', placeholder: '50.00' },
    { key: 'token', label: 'Token do PagSeguro', type: 'text' },
  ],
  pagamento_entrega: [
    { key: 'titulo', label: 'Título', type: 'text', placeholder: 'Pagamento na entrega' },
    {
      key: 'instrucoes',
      label: 'Instruções',
      type: 'textarea',
      placeholder: 'Aceitamos dinheiro, cartão e Pix na entrega',
    },
  ],
}

// Módulos de pagamento que chamam uma gateway real via /checkout (não /submissions).
export const PAYMENT_GATEWAY_MODULES = ['mercado_pago', 'paypal', 'pagseguro']

// Campos fixos preenchidos pelo cliente final do app (não pelo dono da conta).
export interface FormField {
  key: string
  label: string
  type: 'text' | 'textarea' | 'number' | 'url'
}

export const FORM_MODULE_FIELDS: Record<string, FormField[]> = {
  fale_conosco: [
    { key: 'nome', label: 'Nome', type: 'text' },
    { key: 'email', label: 'Email', type: 'text' },
    { key: 'mensagem', label: 'Mensagem', type: 'textarea' },
  ],
  formulario_delivery: [
    { key: 'nome', label: 'Nome', type: 'text' },
    { key: 'telefone', label: 'Telefone', type: 'text' },
    { key: 'endereco', label: 'Endereço', type: 'textarea' },
    { key: 'itens_pedido', label: 'Itens do pedido', type: 'textarea' },
  ],
  cotacao: [
    { key: 'nome', label: 'Nome', type: 'text' },
    { key: 'contato', label: 'Contato', type: 'text' },
    { key: 'produto_interesse', label: 'Produto/serviço de interesse', type: 'text' },
    { key: 'mensagem', label: 'Mensagem', type: 'textarea' },
  ],
  form_fotos: [
    { key: 'nome', label: 'Nome', type: 'text' },
    { key: 'avaliacao', label: 'Avaliação (1 a 5)', type: 'number' },
    { key: 'comentario', label: 'Comentário', type: 'textarea' },
    { key: 'foto_url', label: 'URL da foto', type: 'url' },
  ],
}

// Módulos de formulário com campos fixos — o modal ⚙ só mostra as respostas recebidas.
export const FIXED_FORM_MODULES = Object.keys(FORM_MODULE_FIELDS)

// Módulos cujo envio vira um Pedido (com status) em vez de uma resposta de contato simples.
export const ORDER_MODULES = ['formulario_delivery', 'cotacao']

// Campos de cliente capturados antes de confirmar "pagamento na entrega" (vira Pedido).
export const PAGAMENTO_ENTREGA_CUSTOMER_FIELDS: FormField[] = [
  { key: 'nome', label: 'Nome', type: 'text' },
  { key: 'telefone', label: 'Telefone', type: 'text' },
  { key: 'endereco', label: 'Endereço', type: 'textarea' },
]

// Formato do campo "campos" do contato_personalizado: um rótulo por linha, com
// ":tipo" opcional (numero/data — texto é o padrão) e "*" no fim marcando
// obrigatório. Sem ":tipo" continua funcionando como antes (texto livre).
export interface CustomField {
  key: string
  label: string
  type: 'texto' | 'numero' | 'data'
  required: boolean
}

export function parseCustomFields(campos: string): CustomField[] {
  return (campos || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [rawLabel, rawType] = line.split(':')
      const required = rawLabel.trim().endsWith('*')
      const label = rawLabel.trim().replace(/\*$/, '').trim()
      const normalizedType = rawType?.trim().toLowerCase()
      const type: CustomField['type'] = normalizedType === 'numero' || normalizedType === 'data' ? normalizedType : 'texto'
      return { key: label, label, type, required }
    })
}

// Módulos que usam itens/categorias (ItemsManager) em vez de MODULE_FIELDS.
// O valor indica se o módulo suporta categorias além de itens.
export const LIST_MODULES: Record<string, boolean> = {
  cardapio: true,
  catalogo: true,
  lista_itens: false,
  galeria_imagens: false,
  guia_empresas: false,
  agenda_interna: false,
  mercado_livre: false,
}
