"""Local support queue API. Run with Python 3.10 or newer."""
import json
import sqlite3
from contextlib import closing
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

DATABASE = Path("tickets.sqlite3")
STATUSES = ("open", "closed")
QUEUE = "SELECT id, title, status FROM tickets WHERE status = ? ORDER BY id DESC LIMIT 50"
INDEX = "CREATE INDEX IF NOT EXISTS tickets_status_id ON tickets(status, id DESC)"


def initialize(db):
    db.execute("""CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY, title TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('open', 'closed')))""")
    db.execute(INDEX)


class Tickets(BaseHTTPRequestHandler):
    def reply(self, code, value):
        body = json.dumps(value).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/tickets":
            return self.reply(404, {"error": "Unknown route"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4096:
                raise ValueError
            payload = json.loads(self.rfile.read(size))
            title = payload.get("title") if isinstance(payload, dict) else None
            if not isinstance(title, str) or not 1 <= len(title.strip()) <= 160:
                raise ValueError
        except (ValueError, UnicodeError):
            return self.reply(400, {"error": "Expected JSON with a title of 1–160 characters"})
        with closing(sqlite3.connect(DATABASE)) as db, db:
            ticket_id = db.execute("INSERT INTO tickets(title,status) VALUES (?, 'open')",
                                   (title.strip(),)).lastrowid
        self.reply(HTTPStatus.CREATED, {"id": ticket_id, "title": title.strip(), "status": "open"})

    def do_GET(self):
        route = urlsplit(self.path)
        if route.path != "/tickets":
            return self.reply(404, {"error": "Unknown route"})
        status = parse_qs(route.query, keep_blank_values=True).get("status", ["open"])[0]
        if status not in STATUSES:
            return self.reply(400, {"error": "status must be open or closed"})
        with closing(sqlite3.connect(DATABASE)) as db:
            db.row_factory = sqlite3.Row
            rows = [dict(row) for row in db.execute(QUEUE, (status,))]
        self.reply(200, rows)


if __name__ == "__main__":
    with closing(sqlite3.connect(DATABASE)) as connection, connection:
        initialize(connection)
    print("Serving http://127.0.0.1:8000", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8000), Tickets).serve_forever()
