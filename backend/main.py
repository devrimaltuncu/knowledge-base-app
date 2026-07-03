"""
AI-Driven Markdown Knowledge Base & Graph Visualizer - Backend v4.0
FastAPI server with Supabase multi-user auth, AI-powered semantic search,
Graph-RAG chat, and production deployment ready.
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

from database import (
    USE_SUPABASE,
    get_all_notes,
    get_note,
    create_note,
    update_note,
    delete_note,
    build_graph,
    get_all_tags,
    SCHEMA_SQL,
    NoteData,
)
from embeddings import (
    generate_embedding,
    search_similar_notes,
    rag_retrieve_and_answer,
    DEEPSEEK_API_KEY,
)
from auth import get_current_user

# ---------- Configuration ----------
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
PORT = int(os.environ.get("PORT", "8000"))
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*")

# Parse allowed origins (comma-separated)
origins = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]

# ---------- FastAPI App ----------
app = FastAPI(
    title="Knowledge Base Graph API",
    version="4.0.0",
    docs_url="/docs" if ENVIRONMENT == "development" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Pydantic Models ----------
class NoteCreate(BaseModel):
    title: str
    content: str = ""


class NoteUpdate(BaseModel):
    content: str


class ChatQuery(BaseModel):
    question: str
    top_k: int = 5


# ---------- API Endpoints ----------

@app.get("/")
async def root():
    """Root endpoint - confirms the API is running."""
    return {"message": "Knowledge Base API v4.0 is running", "endpoints": "/api/health, /api/notes, /api/graph, /api/chat/graph"}

@app.get("/api/health")
async def health():
    """Return server health, storage mode, AI status, and environment."""
    return {
        "status": "ok",
        "environment": ENVIRONMENT,
        "storage": "supabase" if USE_SUPABASE else "local_filesystem",
        "ai_enabled": bool(DEEPSEEK_API_KEY),
    }


@app.get("/api/notes")
async def list_notes(user_id: Optional[str] = Depends(get_current_user)):
    """Return all notes for the current user."""
    return [n.to_dict() for n in get_all_notes(user_id)]


@app.get("/api/notes/{note_id}")
async def read_note(
    note_id: str,
    user_id: Optional[str] = Depends(get_current_user),
):
    """Return a single note by its ID (scoped to current user)."""
    note = get_note(note_id, user_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note.to_dict()


@app.post("/api/notes")
async def create_new_note(
    body: NoteCreate,
    user_id: Optional[str] = Depends(get_current_user),
):
    """Create a new note. Stores embedding when Supabase is configured."""
    try:
        note = create_note(body.title, body.content, user_id)
        if USE_SUPABASE and body.content:
            try:
                from database import supabase_client
                emb = generate_embedding(body.content)
                supabase_client.table("notes").update(
                    {"embedding": emb}
                ).eq("id", note.id).execute()
            except Exception:
                pass
        return note.to_dict()
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/notes/{note_id}")
async def update_existing_note(
    note_id: str,
    body: NoteUpdate,
    user_id: Optional[str] = Depends(get_current_user),
):
    """Update a note's content. Re-syncs tags, wiki-links, and embedding."""
    note = update_note(note_id, body.content, user_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if USE_SUPABASE and body.content:
        try:
            from database import supabase_client
            emb = generate_embedding(body.content)
            supabase_client.table("notes").update(
                {"embedding": emb}
            ).eq("id", note_id).execute()
        except Exception:
            pass
    return note.to_dict()


@app.delete("/api/notes/{note_id}")
async def delete_existing_note(
    note_id: str,
    user_id: Optional[str] = Depends(get_current_user),
):
    """Delete a note by its ID (scoped to current user)."""
    success = delete_note(note_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "deleted", "id": note_id}


@app.get("/api/graph")
async def get_graph(user_id: Optional[str] = Depends(get_current_user)):
    """Return graph data (nodes and edges) for the current user."""
    return build_graph(user_id)


@app.get("/api/tags")
async def list_tags(user_id: Optional[str] = Depends(get_current_user)):
    """Return all unique tags across the user's notes."""
    return {"tags": get_all_tags(user_id)}


@app.get("/api/schema")
async def get_schema_sql():
    """Return the SQL DDL (with RLS policies) for Supabase setup."""
    return {"sql": SCHEMA_SQL}


# ---------- AI Endpoints ----------

@app.get("/api/notes/{note_id}/suggested")
async def get_suggested_connections(
    note_id: str,
    user_id: Optional[str] = Depends(get_current_user),
    top_k: int = 5,
):
    """AI-suggested semantically similar notes."""
    note = get_note(note_id, user_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    all_notes = get_all_notes(user_id)
    note_dicts = [n.to_dict() for n in all_notes]
    suggestions = search_similar_notes(note_id, note.content, note_dicts, top_k=top_k)
    return {"note_id": note_id, "suggestions": suggestions}


@app.post("/api/chat/graph")
async def chat_with_graph(
    body: ChatQuery,
    user_id: Optional[str] = Depends(get_current_user),
):
    """Global Graph-RAG Chat over the user's knowledge base."""
    all_notes = get_all_notes(user_id)
    note_dicts = [n.to_dict() for n in all_notes]
    return rag_retrieve_and_answer(body.question, note_dicts, top_k=body.top_k)


@app.post("/api/chat/graph/stream")
async def chat_with_graph_stream(
    body: ChatQuery,
    user_id: Optional[str] = Depends(get_current_user),
):
    """Streaming Graph-RAG Chat (SSE) with DeepSeek."""
    all_notes = get_all_notes(user_id)
    note_dicts = [n.to_dict() for n in all_notes]

    if not DEEPSEEK_API_KEY:
        result = rag_retrieve_and_answer(body.question, note_dicts, top_k=body.top_k)
        from fastapi.responses import JSONResponse
        return JSONResponse(content=result)

    async def stream_response():
        from openai import OpenAI
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
        from embeddings import _simple_tokenize, _build_vocabulary, _text_to_tfidf_vector, _cosine_sim

        texts = [body.question] + [n["content"] for n in note_dicts]
        vocab = _build_vocabulary(texts)
        N = len(texts)
        doc_freq = {w: sum(1 for t in texts if w in _simple_tokenize(t)) for w in vocab}
        query_vec = _text_to_tfidf_vector(body.question, vocab, N, doc_freq)
        scored = []
        for note in note_dicts:
            score = _cosine_sim(query_vec, _text_to_tfidf_vector(note["content"], vocab, N, doc_freq))
            if score > 0.02:
                scored.append({"content": note["content"], "title": note["title"], "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        top_notes = scored[:body.top_k]
        context = "\n\n".join(f"### {n['title']}\n{n['content'][:800]}" for n in top_notes)

        system_prompt = """Sen hem kullanicinin kisisel bilgi tabanindaki notlari bilen hem de genel dunya bilgisine sahip hibrit bir AI asistansin. 

ONEMLI KURALLAR:
1. Kullanici sana hangi dilde yazarsa yazsin, HER ZAMAN TURKCE cevap ver.
2. Once verilen "Ilgili Notlar" bolumunu incele. Eger soruyla ilgili not varsa, bu notlardaki bilgileri kullan ve not basliklarina atifta bulun.
3. EGER baglamda yeterli bilgi yoksa veya kullanici genel bir soru soruyorsa (kodlama, bilim, tarih, gundelik sohbet vb.), kendi genel bilgi dagarcigini kullanarak soruyu KAPSAMLI bir sekilde yanitla.
4. Hem notlardan gelen bilgileri hem de kendi bilgini birlestirerek en zengin cevabi ver."""

        user_prompt = f"""Soru: {body.question}

Ilgili Notlar (varsa):
{context}

TURKCE Cevap (notlari ve genel bilgini kullan):"""

        try:
            stream = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
                temperature=0.7, max_tokens=1000, stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield f"data: {chunk.choices[0].delta.content}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ---------- Entrypoint ----------
if __name__ == "__main__":
    mode = "Supabase" if USE_SUPABASE else "Local Filesystem"
    ai = "enabled" if DEEPSEEK_API_KEY else "disabled"
    print(f"Environment: {ENVIRONMENT}")
    print(f"Storage: {mode} | AI: {ai}")
    print(f"Listening on 0.0.0.0:{PORT}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=(ENVIRONMENT == "development"),
    )