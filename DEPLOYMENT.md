# Deployment Guide: Knowledge Base Graph

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Vercel (FE)    │────▶│  Render (BE)     │────▶│  Supabase (DB)  │
│  React + Vite   │     │  FastAPI + Uvicorn│     │  PostgreSQL +   │
│  Port: 443      │     │  Port: 10000     │     │  pgvector       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Step 1: Supabase Setup

1. **Create a Supabase project** at [supabase.com](https://supabase.com)

2. **Run the DDL schema** in Supabase SQL Editor:
   - In your project, go to **SQL Editor** → **New Query**
   - Copy the SQL from the `/api/schema` endpoint (or from `backend/database.py`)
   - Paste and run. This creates all tables, extensions, and RLS policies.

3. **Enable Auth providers** (optional):
   - Go to **Authentication** → **Providers**
   - Enable **Email** provider (disable "Confirm email" for development)

4. **Copy your keys**:
   - Go to **Settings** → **API**
   - Copy `Project URL` → `SUPABASE_URL`
   - Copy `service_role` key → `SUPABASE_SERVICE_ROLE_KEY`
   - Copy `anon` public key → `SUPABASE_ANON_KEY`

## Step 2: Backend Deployment (Render.com)

1. **Push your code to GitHub** (or connect your repo to Render)

2. **Create a new Web Service** on [render.com](https://render.com):
   - **Name:** `knowledge-base-backend`
   - **Root Directory:** `knowledge-base-app`
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `cd backend && python main.py`
   - **Environment:** Python 3

3. **Add Environment Variables** (in Render dashboard → Environment):
   ```
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...
   SUPABASE_ANON_KEY=eyJhbGciOi...
   SUPABASE_JWT_SECRET=<your-supabase-jwt-secret>    # From Supabase → Settings → API → JWT Secret
   DEEPSEEK_API_KEY=sk-your-deepseek-key             # Optional: for AI chat
   ENVIRONMENT=production
   ALLOWED_ORIGINS=https://your-frontend.vercel.app   # Set after frontend is deployed
   PORT=10000
   ```

4. **Deploy and note the URL**: `https://knowledge-base-backend.onrender.com`

## Step 3: Frontend Deployment (Vercel)

1. **Push your code to GitHub** (or connect your repo to Vercel)

2. **Create a new project** on [vercel.com](https://vercel.com):
   - **Framework:** Vite
   - **Root Directory:** `knowledge-base-app/frontend`
   - **Build Command:** `npm run build` (auto-detected)
   - **Output Directory:** `dist` (auto-detected)

3. **Add Environment Variables** (in Vercel → Settings → Environment Variables):
   ```
   VITE_SUPABASE_URL=https://your-project-id.supabase.co
   VITE_SUPABASE_ANON_KEY=eyJhbGciOi...
   VITE_API_URL=https://knowledge-base-backend.onrender.com
   ```

4. **Deploy**. Your frontend will be at `https://knowledge-base-graph.vercel.app`

5. **Update CORS**: Go back to Render and add the Vercel URL to `ALLOWED_ORIGINS`:
   ```
   ALLOWED_ORIGINS=https://knowledge-base-graph.vercel.app
   ```
   Redeploy the backend after this change.

## Alternative: Railway.app for Backend

1. Create a new project on [railway.app](https://railway.app)
2. Connect your GitHub repo
3. Set root directory to `knowledge-base-app`
4. Add a **Start Command**: `cd backend && python main.py`
5. Add all environment variables from Step 2 above
6. Railway automatically assigns `PORT` — the backend reads it from `os.environ`

## Environment Variables Reference

### Backend (`.env` in `backend/`)

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Production | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Production | Supabase service_role key (server-side only) |
| `SUPABASE_ANON_KEY` | Production | Supabase anon key (for JWT verification) |
| `SUPABASE_JWT_SECRET` | Production | Supabase JWT signing secret |
| `DEEPSEEK_API_KEY` | Optional | DeepSeek API key for AI chat |
| `ENVIRONMENT` | Yes | `development` or `production` |
| `ALLOWED_ORIGINS` | Production | Comma-separated CORS origins |
| `PORT` | Yes | Server port (Render sets this automatically) |

### Frontend (`.env` in `frontend/`)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_SUPABASE_URL` | Production | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Production | Supabase anon key |
| `VITE_API_URL` | Production | Backend API URL (falls back to `/api` proxy) |

## Local Development

No environment variables needed for local development! The app runs with:
- **Local filesystem storage** (no Supabase)
- **No authentication required**
- **TF-IDF semantic search** (no API key needed)
- **Vite proxy** to `localhost:8000`

```bash
cd knowledge-base-app

# Terminal 1: Backend
python backend/main.py

# Terminal 2: Frontend
cd frontend && npm run dev
```

Open http://localhost:5173

## Verify Deployment

1. Visit your Vercel URL
2. You should see the login page (since Supabase is configured)
3. Create an account (or use the email provider)
4. Create some notes with `[[Wiki Links]]`
5. Verify the graph visualizes connections
6. Open the 🤖 chatbot and ask: "Summarize my knowledge base"