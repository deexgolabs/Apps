# Plataforma de Apps — MVP

Plataforma de criação de aplicativos sem código (estilo Web Robot Apps): usuários criam apps escolhendo um template (restaurante, loja, serviço...) e ativando módulos (cardápio, delivery, agendamento...), sem escrever código.

> Projeto isolado dentro do repositório `igrejago`, sem relação com o sistema de gestão de igrejas que já existe em `../backend` e `../frontend`.

## Stack

- **Backend**: FastAPI + SQLAlchemy 2.0 + PostgreSQL (via `psycopg` v3) + JWT
- **Frontend**: Next.js 16 (App Router) + TypeScript + Tailwind CSS v4 + Zustand + Axios
- **Banco**: PostgreSQL 15 via Docker Compose

## Estrutura

```
plataforma-apps/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, CORS, cria tabelas e faz seed dos módulos
│   │   ├── config.py        # Settings (variáveis de ambiente)
│   │   ├── database.py      # Engine/Session SQLAlchemy
│   │   ├── models.py        # User, App, Module, AppConfig
│   │   ├── schemas.py       # Pydantic schemas
│   │   ├── dependencies.py  # get_current_user (JWT)
│   │   ├── utils.py         # hash/verify de senha, JWT
│   │   ├── constants.py     # limites de plano, módulos seed
│   │   ├── seed.py          # popula módulos padrão (idempotente)
│   │   └── routes/          # auth, users, apps, modules
│   └── requirements.txt
├── frontend/
│   ├── app/                 # páginas (App Router)
│   ├── lib/                 # api.ts (axios + interceptors), auth.ts
│   ├── store/                # useAuthStore, useAppStore (Zustand)
│   └── types/                # tipos compartilhados (User, App, Module)
└── docker-compose.yml        # Postgres local
```

## Como rodar

### 1. Banco de dados (Docker)

```bash
cd plataforma-apps
docker compose up -d
```

> O Postgres do container é exposto na porta **55432** do host (não 5432), pois a máquina já tinha instâncias nativas do Postgres ocupando 5432 e 5433.

### 2. Backend

```bash
cd plataforma-apps/backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # ajuste JWT_SECRET em produção

uvicorn app.main:app --reload --port 8000
```

Ao subir, o backend cria as tabelas automaticamente e popula os módulos padrão (cardápio, delivery, reviews, agendamento, catálogo, notificações).

- API: http://localhost:8000
- Docs (Swagger): http://localhost:8000/docs

### 3. Frontend

```bash
cd plataforma-apps/frontend
npm install
copy .env.local.example .env.local

npm run dev
```

- App: http://localhost:3000

## Funcionalidades do MVP

- Registro/login com JWT (senha com bcrypt)
- Dashboard com listagem de apps do usuário
- Criação de app escolhendo template (restaurante, loja, serviço, delivery, outro)
- Editor de app: nome, descrição, cores primária/secundária, módulos ativos
- Exclusão de app
- Limite de apps por plano: **free = 1**, **pro = 5**, **business = ilimitado**
- `GET/PUT /api/users/me` para dados do usuário autenticado

## Notas de implementação

- O driver Postgres usado é `psycopg` (v3), não `psycopg2` — o v2 apresentou um bug de decodificação Unicode neste ambiente Windows/Python 3.14.
- `params` de rotas dinâmicas no Next.js 16 são `Promise` mesmo em Client Components; a página `app/dashboard/apps/[id]/page.tsx` usa `use()` do React para desembrulhar.
- O token JWT é hidratado de forma síncrona do `localStorage` no próprio módulo do `useAuthStore`, para que requisições feitas logo após um reload de página (fora da home/dashboard) já saiam com o header `Authorization`.
- `app/dashboard/layout.tsx` centraliza a checagem de autenticação para todas as rotas `/dashboard/*`.
