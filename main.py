from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
import anthropic
import json
from dotenv import load_dotenv # 이 줄 추가!

# .env 파일에 적어둔 API 키를 자동으로 불러옵니다.
load_dotenv() 


app = FastAPI(title="Synthesis Agent API")

# 크롬 익스텐션과 통신하기 위한 CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 로컬 벡터 DB 초기화 (M4 램 상주)
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="research_tabs")

# 텍스트 청킹 설정
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
    separators=["\n\n", "\n", ".", " ", ""]
)

# Claude API 클라이언트 세팅 (아까 등록한 환경변수를 자동으로 불러와)
try:
    claude_client = anthropic.Anthropic()
except Exception as e:
    print("⚠️ Anthropic API 키 연결에 문제가 있습니다.")

class TabPayload(BaseModel):
    tabId: int
    url: str
    title: str
    content: str
    timestamp: str

@app.post("/api/ingest")
async def ingest_tab_data(payload: TabPayload):
    print(f"\n[{payload.timestamp}] 📥 데이터 수신: {payload.title}")
    
    if len(payload.content.strip()) < 50:
        return {"status": "skipped", "message": "Content too short"}

    chunks = text_splitter.split_text(payload.content)
    print(f"➔ 총 {len(chunks)}개의 청크로 분할 완료.")

    ids = [f"tab_{payload.tabId}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"tabId": payload.tabId, "url": payload.url, "title": payload.title, "timestamp": payload.timestamp} for _ in range(len(chunks))]
    
    collection.add(
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )

    # 수정됨: URL 정보도 함께 넘겨줍니다.
    audit_result = run_consistency_auditor(payload.tabId, payload.title, payload.timestamp, payload.url, chunks[0])

    return {
        "status": "success", 
        "audit_result": audit_result
    }

def run_consistency_auditor(current_tab_id: int, current_tab_title: str, current_timestamp: str, current_url: str, new_text_chunk: str):
    """
    Consistency Auditor: 여러 소스의 정보를 비교하고 Claude를 통해 영어로 판단 결과를 생성함
    """
    results = collection.query(
        query_texts=[new_text_chunk],
        n_results=1,
        where={"url": {"$ne": current_url}},
        include=["documents", "metadatas", "distances"]
    )
    
    if not results['documents'] or not results['documents'][0]:
        return {"status": "no_comparison", "message": "No other tabs found for comparison yet."}
        
    past_text = results['documents'][0][0]
    past_title = results['metadatas'][0][0]['title']
    past_timestamp = results['metadatas'][0][0].get('timestamp', 'Unknown')
    distance = results['distances'][0][0]

    # 로컬 필터링 (주제가 다를 경우)
    if distance > 1.2:
        return {"status": "skipped", "message": "Different topics, skipping analysis."}

    # [수정됨] 영어 출력을 위한 프롬프트
    prompt = f"""
    You are the 'Consistency Auditor' agent, acting as a Control Plane to resolve information noise and conflicts.
    Compare the following two research tabs and identify any inconsistencies (Conflicts).
    Beyond summarizing differences, you must judge which information is closer to the truth based on source reliability and timeliness.

    [Tab A (Existing)]
    - Title/Source: {past_title}
    - Collected At: {past_timestamp}
    - Content: {past_text}

    [Tab B (New)]
    - Title/Source: {current_tab_title}
    - Collected At: {current_timestamp}
    - Content: {new_text_chunk}

    Respond ONLY in JSON format. Both 'message' and 'decision' MUST be written in English.
    Keep 'message' and 'decision' concise (max 3 sentences each).
    {{
        "conflict_detected": true or false,
        "message": "Summary of the inconsistency between Tab A and Tab B.",
        "decision": "Agent's judgement on which source is more reliable or up-to-date."
    }}
    """

    try:
        response = claude_client.messages.create(
            model="claude-haiku-4-5", 
            max_tokens=1000, 
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        
        raw_text = response.content[0].text
        start_idx = raw_text.find('{')
        end_idx = raw_text.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            clean_json_str = raw_text[start_idx:end_idx+1]
            audit_json = json.loads(clean_json_str)
            print(f"🚨 [Auditor Result] Conflict: {audit_json.get('conflict_detected')}")
            return audit_json
        
        return {"status": "error", "message": "JSON Format Error"}

    except Exception as e:
        print(f"⚠️ Claude API Error: {e}")
        return {"status": "error", "message": str(e)}