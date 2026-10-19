import uuid
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import chat, dataset, db, detector, report

ROOT = Path(__file__).resolve().parent.parent
ANN = ROOT / "data" / "annotated"
ANN.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app):
    db.init()
    dataset.ensure_dataset()
    yield


app = FastAPI(title="DefectEye", lifespan=lifespan)
app.mount("/files", StaticFiles(directory=ANN), name="files")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


def _process(img, name, part_type):
    res = detector.inspect(img, part_type)
    fname = f"{uuid.uuid4().hex}.jpg"
    cv2.imwrite(str(ANN / fname), res["annotated"])
    cv2.imwrite(str(ANN / f"raw_{fname}"), img)
    rid = db.add(name, part_type, res["defects"], res["decision"], res["action"], fname)
    return {"id": rid, "name": name, "part_type": part_type, "defects": res["defects"],
            "decision": res["decision"], "action": res["action"], "image": f"/files/{fname}", "raw": f"/files/raw_{fname}"}


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.post("/api/inspect")
async def inspect_upload(file: UploadFile = File(...), part_type: str = Form("part")):
    img = cv2.imdecode(np.frombuffer(await file.read(), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Not a valid image")
    return _process(img, file.filename, part_type)


@app.get("/api/samples")
def samples():
    return dataset.list_samples()


@app.post("/api/inspect-sample/{name}")
def inspect_sample(name: str):
    p = dataset.SAMPLES / Path(name).name
    if not p.exists():
        raise HTTPException(404, "Sample not found")
    return _process(cv2.imread(str(p)), p.name, "lens" if p.name.startswith("lens") else "part")


@app.get("/api/stats")
def stats(day: str = ""):
    return db.stats(day or date.today().isoformat())


@app.get("/api/history")
def history(day: str = ""):
    return db.rows(day or date.today().isoformat())


@app.post("/api/verify/{rid}")
def verify(rid: int):
    db.verify(rid)
    return {"ok": True}


class Msg(BaseModel):
    message: str


@app.post("/api/chat")
async def chat_api(m: Msg):
    return {"reply": await chat.reply(m.message, db.stats(date.today().isoformat()))}


@app.get("/api/report")
def pdf(day: str = ""):
    day = day or date.today().isoformat()
    data = report.build_pdf(day, db.rows(day), db.stats(day), ANN)
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=defecteye_report_{day}.pdf"})
