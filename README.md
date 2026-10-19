# DefectEye
FastAPI + OpenCV defect inspection (scrap/flash, gate cuts, lens fingerprints) with dashboard, AI chatbot and daily PDF report.

## Run (VS Code terminal)
    python -m venv venv
    venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
    pip install -r requirements.txt
    uvicorn app.main:app --reload
Open http://127.0.0.1:8000

Optional smarter chatbot (Groq): set GROQ_API_KEY before starting. Optional: GROQ_MODEL (default llama-3.3-70b-versatile).
