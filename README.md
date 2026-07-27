# Plataforma de Apps

Plataforma de criação de aplicativos sem código (estilo [Web Robot Apps](https://webrobotapps.com/)): o usuário escolhe um template de negócio, ativa os módulos que quiser (cardápio, delivery, agendamento, pagamento, login social...), personaliza cores/ícones e publica um app instalável (PWA) — tudo pelo navegador, sem escrever código.

> Repositório próprio, isolado do `igrejago` (sistema de gestão de igrejas que vive na pasta acima) — projetos sem relação entre si.

## Stack

- **Backend**: FastAPI + SQLAlchemy 2.0 + PostgreSQL (via `psycopg` v3) + JWT (`python-jose`) + Alembic
- **Frontend**: Next.js 16 (App Router) + TypeScript + Tailwind CSS v4 + Zustand + Axios + `@dnd-kit`
- **Banco**: PostgreSQL 15 via Docker Compose

## O que já tem

- **Conta e autenticação**: registro/login com JWT, verificação de e-mail, esqueci minha senha, admin com painel próprio.
- **Editor de app**: preview real do celular sempre visível (não é mockup) — arrastar pra reordenar módulos, ⚙ pra configurar, × pra remover, tudo refletindo o app de verdade. Adicionar módulo é uma tela separada, com o catálogo agrupado por categoria.
- **Assistente de criação em 4 passos**: nome → template (11 tipos de negócio) → marca (cores/logo/ícone) → preview antes de criar.
- **32 módulos** cobrindo conteúdo, cardápio/loja, formulários, comunicação, engajamento, pagamentos, mídia e integrações — incluindo cardápio/catálogo com categorias, agenda interna, cartão fidelidade, login e cadastro de usuários finais (com login social via **Facebook**), checkout via Mercado Pago/PayPal/PagSeguro/pagamento na entrega, notificações push, e sincronização de produtos do **Mercado Livre**.
- **Templates de negócio**: restaurante, loja, serviço, delivery, salão de beleza, academia, pet shop, imobiliária, igreja/ONG, educação, outro.
- **Publicação**: app publicado vira uma PWA instalável (manifest dinâmico, service worker, QR code de instalação) em `/app/{id}`.
- **Cobrança da plataforma**: upgrade de plano via gateway próprio (Mercado Pago/PayPal/PagSeguro), limites por plano (`free`/`pro`/`business`) — apps, módulos, itens, categorias e envios de push por mês, com painel de uso e aviso clicável de upgrade ao bater o limite.
- **Upload de imagem real**: logo, ícone, splash, imagem de fundo de ícone de módulo e imagens de item vão pro disco do backend (`/uploads`), servidos como arquivo estático — com dica de tamanho recomendado nos campos que a WRA documenta.
- **Duplicar app** e checklist de progresso (logo/ícone, módulo configurado, publicado) na aba Geral do editor.
- **Preview Android/iOS** alternável, fonte customizável por app, e ícones vetoriais ([lucide-react](https://lucide.dev)) por módulo (com opção de emoji ou imagem de fundo customizados).
- **Pedidos**: formulário de delivery, cotação e pagamento na entrega geram um `Order` de verdade (com status `pending`/`confirmed`/`preparing`/`completed`/`cancelled`), reunidos numa aba "Pedidos" no editor com controle de status; se o cliente final estiver logado (`login_cadastro`), o pedido some pra conta dele em "Meus pedidos".
- **Verificação real de pagamento**: checkout via Mercado Pago/PayPal/PagSeguro cria um `Order` vinculado à cobrança na gateway (via `external_reference`/id do pedido na gateway) e não finge sucesso — o cliente pode confirmar manualmente depois de pagar, e há webhooks (`/api/apps/{app_id}/webhooks/{gateway}`) que confirmam automaticamente assim que a gateway notifica (Mercado Pago e PagSeguro recebem `notification_url` dinâmica por pedido; PayPal exige configurar a URL uma vez no painel de developer). O webhook nunca confia no corpo da notificação — sempre reconsulta a gateway com as credenciais configuradas antes de marcar como `confirmed`.
- **Notificações**: aba dedicada no editor (quando o módulo está ativo) com envio + histórico dos títulos/mensagens já enviados.
- **Formulário de contato personalizado**: campos aceitam tipo (`Rótulo:numero`, `Rótulo:data`) e obrigatoriedade (`Rótulo*`), com respostas recebidas visíveis no ⚙ do módulo.
- **Administração**: limites e preço de cada plano (`free`/`pro`/`business`) editáveis pelo painel admin (não são mais fixos em código), detalhe/suspensão/exclusão de apps de qualquer usuário, log de auditoria das ações do admin, e cards de receita mensal estimada (MRR) e apps publicados.
- Rate limiting (`slowapi`) nas rotas públicas de autenticação; monitoramento de erro (Sentry) preparado e inativo até receber uma DSN.
- Suíte de testes (`pytest`) cobrindo apps, auth, admin, billing, push, pedidos, pagamentos, público, webhooks.
- Suíte de testes de frontend (`vitest` + Testing Library) cobrindo o carrinho (`CartContext`), regras de frete/campos personalizados e componentes de wishlist — `cd frontend && npm test`.

## Estrutura

```
plataforma-apps/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, seed dos módulos, monta /uploads
│   │   ├── config.py             # Settings (variáveis de ambiente)
│   │   ├── database.py           # Engine/Session SQLAlchemy
│   │   ├── models.py             # User, App, Module, AppConfig, AppUser, ModuleItem, Order,
│   │   │                          #   FormSubmission, PlanConfig, AdminAuditLog...
│   │   ├── schemas.py            # Pydantic schemas
│   │   ├── constants.py          # PLAN_LIMITS/PLAN_PRICES (seed inicial), APP_TEMPLATES, catálogo de módulos
│   │   ├── plan_limits.py        # get_plan_limits/get_plan_price — lê de PlanConfig (editável), cai pro constants.py se faltar
│   │   ├── seed.py               # popula módulos e planos padrão (idempotente)
│   │   ├── payment_gateways.py   # Mercado Pago/PayPal/PagSeguro — checkout + verify_* (consulta status real na gateway)
│   │   ├── email_utils.py        # envio de e-mail (verificação, reset de senha, novo pedido)
│   │   └── routes/               # auth, users, apps, modules, module_config, module_items,
│   │                              #   submissions, orders, end_users, oauth (Facebook), payments,
│   │                              #   mercado_livre, public, admin, billing, push, uploads
│   ├── alembic/                  # migrações versionadas do schema (ver "Migrações" abaixo)
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx                    # landing
│   │   ├── auth/                       # login, registro, esqueci senha, reset, verificar e-mail
│   │   ├── dashboard/                  # lista de apps, admin, billing, editor (apps/[id]), criação (apps/new)
│   │   └── app/[id]/                   # app publicado (PWA pública, sem login de dono)
│   ├── components/
│   │   ├── AppRuntime.tsx              # renderiza o app de verdade (dono e público) + modo editável
│   │   ├── AppPreview.tsx              # celular do editor (usa AppRuntime em modo owner/editable)
│   │   ├── AddModulePanel.tsx          # tela de adicionar módulo, agrupada por categoria
│   │   ├── ModuleSettingsModal.tsx     # configurar ícone/nome/campos de cada módulo
│   │   ├── ItemsManager.tsx            # itens/categorias dos módulos de lista (cardápio, catálogo...)
│   │   ├── OrdersList.tsx              # pedidos de um módulo (ou de todos, na aba Pedidos) com status editável
│   │   ├── PushHistory.tsx             # histórico de notificações enviadas
│   │   └── PhoneFrame.tsx              # moldura de celular compartilhada
│   ├── lib/moduleFields.ts             # registro de campos e ícones por módulo
│   └── store/                          # useAuthStore, useAppStore (Zustand)
└── docker-compose.yml                  # Postgres local
```

## Como rodar

### 1. Banco de dados (Docker)

```bash
cd plataforma-apps
docker compose up -d
```

> O Postgres do container é exposto na porta **55432** do host (não 5432).

### 2. Backend

```bash
cd plataforma-apps/backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # ajuste JWT_SECRET/credenciais em produção

alembic upgrade head           # cria/atualiza o schema do banco
uvicorn app.main:app --reload --port 8000
```

Ao subir, o backend popula os módulos padrão automaticamente (idempotente — não duplica).

- API: http://localhost:8000
- Docs (Swagger): http://localhost:8000/docs

### 3. Frontend

```bash
cd plataforma-apps/frontend
npm install
npm run dev
```

- App: http://localhost:3000

## Migrações (Alembic)

O schema do banco é versionado — **não** rode `ALTER TABLE` manual. Qualquer mudança em `app/models.py` segue este fluxo:

```bash
cd plataforma-apps/backend
alembic revision --autogenerate -m "descrição da mudança"
# revisar o arquivo gerado em alembic/versions/ antes de aplicar
alembic upgrade head
```

`alembic/env.py` já lê a `DATABASE_URL` das mesmas `settings` do app e usa `Base.metadata` de `app/models.py` — não precisa duplicar nada no `alembic.ini`.

## Rate limiting

Rotas públicas sensíveis a abuso (`login`/`register`/`forgot-password` do dono da conta, `login`/`register` de usuário final) têm limite de 5 requisições por minuto por IP (`slowapi`, em memória — não precisa de Redis pra uma instância só). Passar do limite retorna `429`. Nos testes (`tests/conftest.py`), o limiter é desligado (`app.state.limiter.enabled = False`) pra não interferir entre os vários `register_user` de testes diferentes.

## Monitoramento de erro (Sentry) — preparado, inativo

O SDK já está integrado (backend: `sentry_sdk.init` em `app/main.py`; frontend: `sentry.client/server/edge.config.ts` + `instrumentation.ts`), mas sem DSN configurado **nada é coletado nem enviado** — é código morto de propósito até você ativar:

1. Crie um projeto em [sentry.io](https://sentry.io) (um projeto Python/FastAPI, um projeto Next.js).
2. Cole os DSNs: `SENTRY_DSN` no `backend/.env`, `NEXT_PUBLIC_SENTRY_DSN` no `frontend/.env.local`.
3. Pro lado do navegador (client-side), rode `npx @sentry/wizard@latest -i nextjs` dentro de `frontend/` com o DSN em mãos — a forma de inicializar no navegador varia entre versões do Next.js/Sentry, e o wizard detecta a certa pra versão instalada (o servidor/edge já funcionam sem isso, via `instrumentation.ts`).

## Repositório remoto e CI

O projeto já tem um repositório git local (`git log` mostra o histórico), mas sem remoto — sem isso, o workflow em `.github/workflows/tests.yml` (roda `pytest` e `vitest` a cada push/PR) não executa. Pra ativar:

```bash
cd plataforma-apps
git remote add origin <url-do-seu-repositorio-github-ou-gitlab>
git push -u origin master
```

Depois disso, todo `push`/PR roda a suíte de testes automaticamente contra um Postgres efêmero — sem precisar de mais nenhuma configuração.

## Pendências antes de um deploy real

- `JWT_SECRET` no `.env` ainda é o placeholder — trocar por uma chave forte gerada de verdade.
- `CORS_ORIGINS`/`FRONTEND_URL`/`BACKEND_URL` apontam pra `localhost` — ajustar pros domínios reais.
- SMTP, credenciais de gateway de pagamento (Mercado Pago/PayPal/PagSeguro) e Facebook App ID/Secret estão vazios — sem eles, e-mails só logam no console e os checkouts/login social retornam erro claro de "não configurado" (comportamento intencional, não é bug).
- Sentry sem DSN (ver seção acima) — nenhum erro é monitorado até isso ser configurado.
- Sem repositório remoto ainda (ver seção acima) — o workflow de CI existe mas não roda até o `git push` inicial.
- Sem Dockerfile pro backend/frontend ainda — hoje roda tudo local via `uvicorn`/`npm run dev`.

## Notas de implementação

- O driver Postgres usado é `psycopg` (v3), não `psycopg2` — o v2 apresentou um bug de decodificação Unicode neste ambiente Windows/Python 3.14.
- `params` de rotas dinâmicas no Next.js 16 são `Promise` mesmo em Client Components; páginas como `app/dashboard/apps/[id]/page.tsx` usam `use()` do React pra desembrulhar.
- O token JWT é hidratado de forma síncrona do `localStorage` no próprio módulo do `useAuthStore`, pra que requisições feitas logo após um reload de página já saiam com o header `Authorization`.
- `app/dashboard/layout.tsx` centraliza a checagem de autenticação pra todas as rotas `/dashboard/*`.
- Módulos de lista (cardápio, catálogo...) reaproveitam o mesmo par `ModuleCategory`/`ModuleItem` genérico — inclusive o módulo Mercado Livre, que faz upsert nesses itens via `extra.ml_item_id` pra sincronizar sem duplicar.
- Login de usuário final (`AppUser`) tem dois fluxos: e-mail/senha e OAuth2 via Facebook — nos dois casos emite o mesmo formato de JWT (`type: "end_user"`), namespace separado do JWT do dono da conta.
