from io import BytesIO
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))


import os
print("OPENAI_API_KEY starts with:", (os.getenv("OPENAI_API_KEY") or "")[:5])


from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader

from agents import Runner
from agent import build_agent

from db import SessionLocal, Resume, init_db

# ----- App setup -----
app = FastAPI(title="Capstone Resume Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: set to your GitHub Pages domain in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
agent = build_agent()


# ----- Helpers -----
def pdf_to_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def save_resume(filename: str, extracted_text: str, analysis: str) -> int:
    db = SessionLocal()
    try:
        row = Resume(
            filename=filename,
            extracted_text=extracted_text,
            analysis=analysis,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    finally:
        db.close()


# ----- Routes -----
#@app.get("/health")
#def health():
 #   return {"ok": True}


@app.post("/UploadResume")
async def analyze_resume(file: UploadFile = File(...)):
    try:
        pdf_bytes = await file.read()
        resume_text = pdf_to_text(pdf_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF read/extract failed: {e}")

    if not resume_text:
        raise HTTPException(status_code=400, detail="No text extracted (PDF may be scanned).")

#prompt given to the agent for analysis. The agent also has a prompt
# defined in agent.py but this one is more specific to ATS-focused review.
#it basically is the prompt that tells the agent how to act
   #change this prompt later if you want more detail
    prompt = (
      "Return ONLY valid JSON. No extra text.\n\n"
    "Schema:\n"
    "{\n"
    "  \"suitable_jobs\": [\n"
    "    {\n"
    "      \"job_title\": \"string\",\n"
    "      \"company\": \"string\",\n"
    "      \"link\": \"URL or 'NOT_FOUND'\",\n"
    "      \"days_posted\": number,\n"
    "      \"match_percentage\": number from 0 to 100\n"
    "    }\n"
    "  ]\n"
    "}\n\n"
    "Rules:\n"
    "- Return exactly 5 jobs.\n"
    "- Every job must come from a WebSearchTool result.\n"
    "- Do not omit any field.\n"
    "- If a field is unknown, use 'NOT_FOUND' or 0.\n\n"
    "Resume:\n"
        f"{resume_text}\n"
    )

    try:
        result = await Runner.run(agent, prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent failed: {e}")

    analysis = result.final_output

    resume_id = save_resume(file.filename, resume_text, analysis)

    return {
        "id": resume_id,
        "filename": file.filename,
        "analysis": analysis,
    }


#@app.get("/history")
#def history(limit: int = 25):
    db = SessionLocal()
    try:
        rows = (
            db.query(Resume)
            .order_by(Resume.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "filename": r.filename,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    finally:
        db.close()


# #@app.get("/resume/{resume_id}")
# def get_resume(resume_id: int):
#     db = SessionLocal()
#     try:
#         r = db.query(Resume).filter(Resume.id == resume_id).first()
#         if not r:
#             raise HTTPException(status_code=404, detail="Not found.")
#         return {
#             "id": r.id,
#             "filename": r.filename,
#             "created_at": r.created_at.isoformat(),
#             "analysis": r.analysis,
#             # include text if you want:
#             # "extracted_text": r.extracted_text,
#         }
#     finally:
#         db.close()
