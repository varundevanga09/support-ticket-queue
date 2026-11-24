"""Public demo using the starter's queue schema and query."""
import os
import secrets
import sqlite3
from contextlib import closing, asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from service import initialize, QUEUE

DB = Path(os.getenv("DATABASE_PATH", "tickets.sqlite3"))
PACIFIC = ZoneInfo("America/Los_Angeles")


def connect():
    return sqlite3.connect(DB, timeout=10)


@asynccontextmanager
async def lifespan(app):
    with closing(connect()) as db, db:
        db.execute("PRAGMA journal_mode=WAL")
        initialize(db)
        db.execute("CREATE TABLE IF NOT EXISTS visits(day TEXT, token TEXT, PRIMARY KEY(day,token))")
    yield


app = FastAPI(title="Support Ticket Queue", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    now = datetime.now(PACIFIC)
    day = now.date().isoformat()
    token = request.cookies.get("queue_browser", "")
    if len(token) != 32 or any(c not in "0123456789abcdef" for c in token):
        token = secrets.token_hex(16)
    with closing(connect()) as db, db:
        db.execute("INSERT OR IGNORE INTO visits VALUES (?,?)", (day, token))
    response = HTMLResponse(Path(__file__).with_name("index.html").read_text(), headers={"Cache-Control":"no-store"})
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    response.set_cookie("queue_browser", token, max_age=max(1, int(tomorrow.timestamp()-now.timestamp())),
                        httponly=True, samesite="lax", secure=bool(os.getenv("RENDER")))
    return response


@app.get("/usage")
def usage():
    today = datetime.now(PACIFIC).date()
    with closing(connect()) as db:
        counts = dict(db.execute("SELECT day,count(*) FROM visits WHERE day BETWEEN ? AND ? GROUP BY day",
                                 ((today-timedelta(days=6)).isoformat(), today.isoformat())))
    days = [(today-timedelta(days=i)).isoformat() for i in range(7)]
    return {"timezone":"America/Los_Angeles", "daily_browsers":{d:counts.get(d,0) for d in days}}


class Ticket(BaseModel):
    title: str = Field(min_length=1, max_length=160)


@app.post("/tickets", status_code=201)
def create(ticket: Ticket):
    title = ticket.title.strip()
    if not title:
        raise HTTPException(422, "Enter a ticket title")
    with closing(connect()) as db, db:
        ticket_id = db.execute("INSERT INTO tickets(title,status) VALUES (?, 'open')",(title,)).lastrowid
    return {"id":ticket_id, "title":title, "status":"open"}


@app.get("/tickets")
def read(status: Literal["open","closed"]="open"):
    with closing(connect()) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute(QUEUE,(status,))]
