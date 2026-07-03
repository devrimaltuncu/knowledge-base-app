"""
AI Embeddings & Semantic Search using DeepSeek API (OpenAI-compatible).

Handles:
- Generating vector embeddings for note content
- Cosine similarity search via pgvector in Supabase
- Local fallback using simple TF-IDF-like cosine similarity
"""

import os
import re
import math
from pathlib import Path
from typing import Optional
from collections import Counter

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
EMBEDDING_MODEL = "deepseek-chat"  # DeepSeek doesn't have a dedicated embedding model; we use chat model with a prompt

# We'll use a local sentence-level embedding approach with simple TF-IDF vectors
# since DeepSeek doesn't provide embeddings. For production, switch to OpenAI text-embedding-3-small.

# For the local fallback, we use sklearn if available, otherwise a simple bag-of-words
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


def _normalize_turkish(text: str) -> str:
    """
    Normalize Turkish characters to ASCII equivalents for better cross-lingual matching.
    Also strips accents from non-Turkish Latin characters.
    """
    text = text.lower()
    # Turkish -> ASCII mapping
    replacements = {
        'ı': 'i', 'i̇': 'i',      # dotless/dotted i
        'ğ': 'g', 'ģ': 'g',
        'ü': 'u', 'ù': 'u', 'ú': 'u', 'û': 'u',
        'ş': 's', 'ș': 's',
        'ö': 'o', 'ò': 'o', 'ó': 'o', 'ô': 'o',
        'ç': 'c', 'ĉ': 'c',
        'i̇': 'i', 'ı̇': 'i',
    }
    for tr_char, ascii_char in replacements.items():
        text = text.replace(tr_char, ascii_char)
    return text


# Turkish-English tech term mapping for cross-lingual search
_TR_EN_TECH_TERMS = {
    # AI / ML
    "makine": "machine", "ogrenmesi": "learning", "ogrenme": "learning",
    "yapay": "artificial", "zeka": "intelligence", "zekasi": "intelligence",
    "derin": "deep", "sinir": "neural", "agi": "network", "aglari": "networks",
    "algoritma": "algorithm", "algoritmalar": "algorithms", "algoritmalari": "algorithms",
    "algoritmalardan": "algorithms",
    "veri": "data", "veriler": "data", "verisi": "data",
    "egitim": "training", "egitimi": "training",
    "model": "model", "modeller": "models", "modeli": "model",
    "tahmin": "prediction", "siniflandirma": "classification",
    "regresyon": "regression", "kumeleme": "clustering",
    # Software / DevOps
    "yazilim": "software", "gelistirme": "development",
    "dagitim": "deployment", "altyapi": "infrastructure",
    "izleme": "monitoring", "guvenlik": "security",
    "otomasyon": "automation", "test": "testing",
    "surum": "version", "kod": "code",
    "veritabani": "database", "sunucu": "server",
    "bulut": "cloud", "mikroservis": "microservice",
    # General tech
    "teknoloji": "technology", "sistem": "system", "sistemleri": "systems",
    "uygulama": "application", "arac": "tool", "araclari": "tools",
    "dokumantasyon": "documentation", "rehber": "guide",
    "proje": "project", "mimari": "architecture", "tasarim": "design",
    "desen": "pattern", "desenleri": "patterns",
    "ipucu": "tip", "ipuclari": "tips", "puf": "tip",
    "notlarimda": "notes", "notlar": "notes", "notu": "note",
    "hangi": "what", "nedir": "what", "nasil": "how",
    "bahsediliyor": "mentioned", "anlatiyor": "explains",
    "ozetle": "summarize", "ozet": "summary",
    "baglanti": "link", "baglantilar": "links",
    "icerik": "content", "konu": "topic", "konular": "topics",
    "ornek": "example", "ornekler": "examples",
    "kullanim": "usage", "kullanimi": "usage",
    "ortak": "common", "benzer": "similar",
    "fark": "difference", "karsilastirma": "comparison",
}


def _simple_tokenize(text: str) -> list[str]:
    """
    Simple word tokenizer. Normalizes Turkish characters to ASCII equivalents
    and adds English translations of known Turkish tech terms.
    """
    normalized = _normalize_turkish(text)
    tokens = re.findall(r"[a-zA-Z0-9_\-\u00C0-\u024F]+", normalized)
    # Add English translations of Turkish tech terms
    extra = []
    for token in tokens:
        if token in _TR_EN_TECH_TERMS:
            extra.append(_TR_EN_TECH_TERMS[token])
    return tokens + extra


def _build_vocabulary(all_texts: list[str]) -> list[str]:
    """
    Build sorted vocabulary from a corpus. Also adds normalized ASCII versions
    of Turkish words to improve cross-lingual matching.
    """
    vocab = set()
    for text in all_texts:
        vocab.update(_simple_tokenize(text))
        # Also add normalized ASCII versions
        normalized = _normalize_turkish(text)
        vocab.update(re.findall(r"[a-zA-Z0-9_\-\u00C0-\u024F]+", normalized))
    return sorted(vocab)


def _text_to_tfidf_vector(text: str, vocab: list[str], doc_count: int, doc_freq: dict) -> list[float]:
    """Convert text to a TF-IDF vector given vocabulary and corpus stats."""
    tokens = _simple_tokenize(text)
    tf = Counter(tokens)
    vec = []
    N = max(doc_count, 1)
    for word in vocab:
        term_freq = tf.get(word, 0)
        if term_freq == 0:
            vec.append(0.0)
        else:
            df = doc_freq.get(word, 1)
            idf = math.log(N / df)
            vec.append(term_freq * idf)
    # Normalize
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    return max(0.0, min(1.0, dot))


def generate_embedding(text: str) -> list[float]:
    """
    Generate an embedding vector for the given text.
    Uses local TF-IDF when no external embedding API is configured.
    For production, replace this with OpenAI's text-embedding-3-small or similar.
    
    Returns a list of floats (fixed dimension based on vocabulary).
    """
    # For now, we generate a normalized TF-IDF vector from a fixed vocabulary.
    # This is lightweight and works without external API calls.
    # The dimension will be consistent within a session.
    
    # Use a fixed feature set for consistency
    tokens = _simple_tokenize(text)
    if not tokens:
        return [0.0] * 256
    
    # Build a pseudo-embedding using hash-based feature hashing
    # This creates a 256-dim vector that captures term presence
    DIM = 256
    vec = [0.0] * DIM
    for token in set(tokens):
        h = hash(token) % DIM
        # Use TF (term frequency) weighted by inverse doc frequency approximation
        count = tokens.count(token)
        vec[h] += count / max(1, len(tokens))
    
    # Normalize
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def generate_embedding_deepseek(text: str) -> list[float]:
    """
    Generate embedding using DeepSeek API (if configured).
    Since DeepSeek doesn't have a native embedding endpoint yet,
    we fall back to local embedding generation.
    """
    if DEEPSEEK_API_KEY and False:  # Disabled until DeepSeek adds embeddings API
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
            )
            # Placeholder: when DeepSeek adds embeddings, use:
            # response = client.embeddings.create(model="deepseek-embedding", input=text)
            # return response.data[0].embedding
        except Exception:
            pass
    
    return generate_embedding(text)


def search_similar_notes(
    note_id: str,
    content: str,
    all_notes: list[dict],
    top_k: int = 5,
) -> list[dict]:
    """
    Find the top-k semantically similar notes to the given note.
    
    Args:
        note_id: ID of the source note (to exclude from results)
        content: Content of the source note
        all_notes: List of all notes with 'id', 'title', 'content' keys
        top_k: Number of results to return
    
    Returns:
        List of {id, title, score} dicts sorted by descending similarity
    """
    if not all_notes:
        return []
    
    # Build TF-IDF vectors for all notes
    texts = [n["content"] for n in all_notes]
    vocab = _build_vocabulary(texts)
    N = len(texts)
    doc_freq = {}
    for word in vocab:
        doc_freq[word] = sum(1 for t in texts if word in _simple_tokenize(t))
    
    # Compute vector for source
    source_vec = _text_to_tfidf_vector(content, vocab, N, doc_freq)
    
    # Score all other notes
    scored = []
    for note in all_notes:
        if note["id"] == note_id:
            continue
        target_vec = _text_to_tfidf_vector(note["content"], vocab, N, doc_freq)
        score = _cosine_sim(source_vec, target_vec)
        if score > 0.05:  # Minimum threshold
            scored.append({
                "id": note["id"],
                "title": note["title"],
                "score": round(score, 4),
            })
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def rag_retrieve_and_answer(
    query: str,
    all_notes: list[dict],
    top_k: int = 5,
) -> dict:
    """
    RAG: Retrieve relevant notes by semantic similarity and generate an answer.
    
    Uses DeepSeek API if available, otherwise returns a structured summary
    of the most relevant notes.
    """
    if not all_notes:
        return {
            "answer": "Bilgi tabaninda hic not bulunamadi. Once bir kac not olusturun!",
            "sources": [],
        }
    
    # Build query vector
    texts = [query] + [n["content"] for n in all_notes]
    vocab = _build_vocabulary(texts)
    N = len(texts)
    doc_freq = {}
    for word in vocab:
        doc_freq[word] = sum(1 for t in texts if word in _simple_tokenize(t))
    
    query_vec = _text_to_tfidf_vector(query, vocab, N, doc_freq)
    
    # Score all notes against query
    scored = []
    for note in all_notes:
        note_vec = _text_to_tfidf_vector(note["content"], vocab, N, doc_freq)
        score = _cosine_sim(query_vec, note_vec)
        if score > 0.002:
            scored.append({
                "id": note["id"],
                "title": note["title"],
                "content": note["content"],
                "score": round(score, 4),
            })
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    top_notes = scored[:top_k]
    
    if DEEPSEEK_API_KEY:
        # Use DeepSeek to generate a comprehensive answer
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
            )
            
            # Build context from top notes
            context_parts = []
            for n in top_notes:
                snippet = n["content"][:800]  # Truncate long notes
                context_parts.append(f"### {n['title']}\n{snippet}")
            context = "\n\n".join(context_parts)
            
            system_prompt = """Sen hem kullanicinin kisisel bilgi tabanindaki notlari bilen hem de genel dunya bilgisine sahip hibrit bir AI asistansin. 

ONEMLI KURALLAR:
1. Kullanici sana hangi dilde yazarsa yazsin, HER ZAMAN TURKCE cevap ver.
2. Once verilen "Bilgi Tabanindaki Ilgili Notlar" bolumunu incele. Eger soruyla ilgili not varsa, bu notlardaki bilgileri kullan ve not basliklarina atifta bulun.
3. EGER baglamda (context) yeterli bilgi yoksa veya kullanici genel bir soru soruyorsa (kodlama, bilim, tarih, gundelik sohbet vb.), kendi genel bilgi dagarcigini kullanarak soruyu KAPSAMLI bir sekilde yanitla. Kullanicinin notlariyla ortusen yerler varsa bunlari belirt.
4. Hem notlardan gelen bilgileri hem de kendi bilgini birlestirerek en zengin cevabi ver.
5. Yanitlarinda dostane, yardimsever ve profesyonel ol."""
            
            user_prompt = f"""Kullanici Sorusu: {query}

Bilgi Tabanindaki Ilgili Notlar (varsa):
{context}

Yukaridaki notlari ve kendi genel bilgini kullanarak kapsamli bir TURKCE cevap ver. Eger baglamda yeterli bilgi yoksa genel bilginle cevapla."""

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            
            answer = response.choices[0].message.content
            return {
                "answer": answer,
                "sources": [{"id": n["id"], "title": n["title"], "score": n["score"]} for n in top_notes],
            }
        except Exception as e:
            # Fall back to local summary
            pass
    
    # Local fallback (no DeepSeek API key configured)
    if not top_notes:
        # Keyword-based fallback: try matching individual words from query
        query_tokens = set(_simple_tokenize(query))
        keyword_notes = []
        for note in all_notes:
            note_tokens = set(_simple_tokenize(note["content"]))
            overlap = query_tokens & note_tokens
            if overlap:
                keyword_notes.append({
                    "id": note["id"],
                    "title": note["title"],
                    "content": note["content"],
                    "score": round(len(overlap) / max(1, len(query_tokens)), 4),
                })
        keyword_notes.sort(key=lambda x: x["score"], reverse=True)
        top_notes = keyword_notes[:top_k]
        
        if not top_notes:
            return {
                "answer": "Bilgi tabanimda bu konuyla ilgili bir not bulamadim. Ancak genel bir soruysa, DeepSeek API anahtari ekleyerek yapay zeka destekli cevaplar alabilirsiniz. Su an API anahtari olmadigi icin sadece notlarinizda arama yapabiliyorum.",
                "sources": [],
            }
    
    summary_parts = ["# Bilgi Tabani Ozeti\n"]
    summary_parts.append(f"Sorgunuzla en ilgili notlar: *{query}*\n")
    
    for i, n in enumerate(top_notes, 1):
        snippet = n["content"][:300].replace("\n", " ").strip()
        summary_parts.append(f"\n**{i}. [{n['title']}](note:{n['id']})** (ilgi puani: {n['score']})")
        summary_parts.append(f"> {snippet}...\n")
    
    summary_parts.append("\n---")
    summary_parts.append("*AI destekli cevaplar icin .env dosyasina DeepSeek API anahtarinizi ekleyin.*")
    
    return {
        "answer": "\n".join(summary_parts),
        "sources": [{"id": n["id"], "title": n["title"], "score": n["score"]} for n in top_notes],
    }