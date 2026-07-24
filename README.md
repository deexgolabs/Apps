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
- **Cobrança da plataforma**: upgrade de plano via gateway próprio (Mercado Pago/PayPal/PagSeguro), limites por plano (`free`/`pro`/`business`).
- **Upload de imagem real**: logo, ícone, splash e imagens de item vão pro disco do backend (`/uploads`), servidos como arquivo estático.
- Suíte de testes (`pytest`) cobrindo apps, auth, admin, billing, público.

## Estrutura

```
plataforma-apps/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, seed dos módulos, monta /uploads
│   │   ├── config.py             # Settings (variáveis de ambiente)
│   │   ├── database.py           # Engine/Session SQLAlchemy
│   │   ├── models.py             # User, App, Module, AppConfig, AppUser, ModuleItem, FormSubmission...
│   │   ├── schemas.py            # Pydantic schemas
│   │   ├── constants.py          # PLAN_LIMITS, APP_TEMPLATES, catálogo de módulos (seed)
│   │   ├── seed.py               # popula módulos padrão (idempotente)
│   │   ├── payment_gateways.py   # Mercado Pago/PayPal/PagSeguro (compartilhado entre módulo de pagamento e billing)
│   │   ├── email_utils.py        # envio de e-mail (verificação, reset de senha)
│   │   └── routes/               # auth, users, apps, modules, module_config, module_items,
│   │                              #   submissions, end_users, oauth (Facebook), payments,
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

## Pendências antes de um deploy real

- `JWT_SECRET` no `.env` ainda é o placeholder — trocar por uma chave forte gerada de verdade.
- `CORS_ORIGINS`/`FRONTEND_URL`/`BACKEND_URL` apontam pra `localhost` — ajustar pros domínios reais.
- SMTP, credenciais de gateway de pagamento (Mercado Pago/PayPal/PagSeguro) e Facebook App ID/Secret estão vazios — sem eles, e-mails só logam no console e os checkouts/login social retornam erro claro de "não configurado" (comportamento intencional, não é bug).
- Sem Dockerfile/CI ainda — hoje roda tudo local via `uvicorn`/`npm run dev`; fica como próximo passo quando houver um repositório remoto pra rodar CI contra.

## Notas de implementação

- O driver Postgres usado é `psycopg` (v3), não `psycopg2` — o v2 apresentou um bug de decodificação Unicode neste ambiente Windows/Python 3.14.
- `params` de rotas dinâmicas no Next.js 16 são `Promise` mesmo em Client Components; páginas como `app/dashboard/apps/[id]/page.tsx` usam `use()` do React pra desembrulhar.
- O token JWT é hidratado de forma síncrona do `localStorage` no próprio módulo do `useAuthStore`, pra que requisições feitas logo após um reload de página já saiam com o header `Authorization`.
- `app/dashboard/layout.tsx` centraliza a checagem de autenticação pra todas as rotas `/dashboard/*`.
- Módulos de lista (cardápio, catálogo...) reaproveitam o mesmo par `ModuleCategory`/`ModuleItem` genérico — inclusive o módulo Mercado Livre, que faz upsert nesses itens via `extra.ml_item_id` pra sincronizar sem duplicar.
- Login de usuário final (`AppUser`) tem dois fluxos: e-mail/senha e OAuth2 via Facebook — nos dois casos emite o mesmo formato de JWT (`type: "end_user"`), namespace separado do JWT do dono da conta.
