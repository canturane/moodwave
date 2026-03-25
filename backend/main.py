from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
import os
import json
import re

load_dotenv()

app = FastAPI(title="Moodwave API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class MoodRequest(BaseModel):
    mood: str

class Recommendation(BaseModel):
    title: str
    creator: str
    reason: str

class MoodResponse(BaseModel):
    mood_summary: str
    mood_color: str
    mood_category: str
    songs: list[Recommendation]
    movies: list[Recommendation]
    books: list[Recommendation]

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.8,
)

@tool
def analyze_mood(mood_text: str) -> str:
    """Kullanıcının yazdığı metni analiz ederek ruh halini kategorize eder.
    Kategori: mutlu, üzgün, enerjik, nostaljik, stresli, huzurlu, romantik, öfkeli
    Ayrıca ruh haline uygun bir hex renk kodu ve kısa analiz döndürür."""

    response = llm.invoke(
        f"""Kullanıcının ruh hali metni: "{mood_text}"
        
        SADECE şu JSON formatında yanıt ver:
        {{
            "category": "mutlu|üzgün|enerjik|nostaljik|stresli|huzurlu|romantik|öfkeli",
            "mood_color": "#HEXKOD",
            "mood_summary": "ruh halinin 1-2 cümlelik Türkçe analizi"
        }}"""
    )
    return response.content

@tool
def get_recommendations(mood_category: str, mood_summary: str) -> str:
    """Ruh hali kategorisine göre müzik, film ve kitap önerileri üretir."""

    response = llm.invoke(
        f"""Ruh hali kategorisi: {mood_category}
Ruh hali özeti: {mood_summary}

Bu ruh haline uygun öneriler üret. SADECE şu JSON formatında yanıt ver:
{{
    "songs": [
        {{"title": "şarkı adı", "creator": "sanatçı", "reason": "neden uygun"}},
        {{"title": "şarkı adı", "creator": "sanatçı", "reason": "neden uygun"}},
        {{"title": "şarkı adı", "creator": "sanatçı", "reason": "neden uygun"}}
    ],
    "movies": [
        {{"title": "film adı", "creator": "yönetmen", "reason": "neden uygun"}},
        {{"title": "film adı", "creator": "yönetmen", "reason": "neden uygun"}},
        {{"title": "film adı", "creator": "yönetmen", "reason": "neden uygun"}}
    ],
    "books": [
        {{"title": "kitap adı", "creator": "yazar", "reason": "neden uygun"}},
        {{"title": "kitap adı", "creator": "yazar", "reason": "neden uygun"}},
        {{"title": "kitap adı", "creator": "yazar", "reason": "neden uygun"}}
    ]
}}"""
    )
    return response.content

@tool
def enrich_recommendations(recommendations_json: str, mood_category: str) -> str:
    """Üretilen önerileri zenginleştirir. Her öneriye neden bu ruh haliyle
    özellikle uyumlu olduğuna dair daha derin bir bağlam ekler."""

    response = llm.invoke(
        f"""Ruh hali kategorisi: {mood_category}
Mevcut öneriler: {recommendations_json}

Bu önerilerdeki her "reason" alanını daha derin, kişisel ve duygusal bir bağlamla zenginleştir.
Aynı JSON formatını koru, sadece reason alanlarını güncelle. SADECE JSON döndür."""
    )
    return response.content

# LangGraph ReAct agent
agent = create_react_agent(
    model=llm,
    tools=[analyze_mood, get_recommendations, enrich_recommendations],
    prompt="""Sen bir kültür küratörü agent'sın. Kullanıcının ruh halini analiz etmek ve 
kişiselleştirilmiş öneriler sunmak için şu adımları TAKİP ET:

1. ÖNCE analyze_mood tool'unu çağır → ruh halini kategorize et
2. SONRA get_recommendations tool'unu çağır → kategori bazlı öneriler al  
3. SON OLARAK enrich_recommendations tool'unu çağır → önerileri zenginleştir
4. Tüm sonuçları birleştirerek final JSON'u döndür

Her adımı sırayla tamamla, hiçbir adımı atlama."""
)

@app.get("/health")
def health():
    return {"status": "ok", "agent": "LangGraph ReAct Agent — 3 Tools"}

@app.post("/api/recommend", response_model=MoodResponse)
async def recommend(request: MoodRequest):
    if not request.mood.strip():
        raise HTTPException(status_code=400, detail="Mood boş olamaz")

    try:
        result = await agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": f"Kullanıcının ruh hali: '{request.mood}'. Lütfen tüm adımları sırayla uygula ve final sonucu döndür."
            }]
        })

        # Agent mesajlarından verileri topla
        mood_data = {}
        recommendations = {}
        enriched = {}

        for message in result["messages"]:
            if not hasattr(message, "content") or not message.content:
                continue
            content = message.content
            if not isinstance(content, str):
                continue

            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                continue

            try:
                parsed = json.loads(json_match.group())

                if "category" in parsed:
                    mood_data = parsed
                elif "songs" in parsed and "enrich" not in content.lower():
                    recommendations = parsed
                elif "songs" in parsed:
                    enriched = parsed
            except json.JSONDecodeError:
                continue

        # En son songs içeren JSON'u kullan
        final_recs = enriched if enriched else recommendations

        if not mood_data or not final_recs:
            raise HTTPException(status_code=500, detail="Agent yanıtı parse edilemedi")

        return MoodResponse(
            mood_summary=mood_data.get("mood_summary", ""),
            mood_color=mood_data.get("mood_color", "#a78bfa"),
            mood_category=mood_data.get("category", ""),
            songs=[Recommendation(**s) for s in final_recs.get("songs", [])],
            movies=[Recommendation(**m) for m in final_recs.get("movies", [])],
            books=[Recommendation(**b) for b in final_recs.get("books", [])],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))