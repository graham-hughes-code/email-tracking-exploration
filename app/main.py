from fastapi import FastAPI, Request, Depends
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

import logging
import json
from datetime import datetime, timezone
import uuid
from uuid import UUID

import sqlalchemy
from sqlalchemy import create_engine, Column, String
from sqlalchemy.dialects.sqlite import DATETIME
from sqlalchemy.orm import sessionmaker, Session

# Database setup
DATABASE_URL = "sqlite:///./main.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = sqlalchemy.orm.declarative_base()


class Tracking(Base):
    __tablename__ = "tracking"
    id = Column(String, primary_key=True, index=True)
    ts = Column(DATETIME, primary_key=True, index=True)
    ip = Column(String)
    user_agent = Column(String)
    headers = Column(String)

    def as_dict(self):
        return {"id": self.id, "ts": str(self.ts), "ip": self.ip, "headers": self.headers}


Base.metadata.create_all(bind=engine)


# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


logger = logging.getLogger(__name__)
app = FastAPI()


@app.get("/")
async def root(request: Request):
    return RedirectResponse(f"{request.base_url}new")


@app.get("/image/{id}")
async def get_image(id: UUID, request: Request, db: Session = Depends(get_db)):
    track = Tracking(
        id=str(id),
        ts=datetime.now(timezone.utc),
        ip=request.headers.get("x-forwarded-for") or request.client.host,
        user_agent=request.headers.get("user-agent"),
        headers=json.dumps(dict(request.headers)),
    )
    db.add(track)
    db.commit()
    return FileResponse("images/small.png")


@app.get("/new_image")
async def new_image(request: Request):
    new_uuid = uuid.uuid4()
    html_content = f"""
      <div style="display: flex;">
        <div id="url">{request.base_url}image/{new_uuid}</div>
        <button onclick=\"copy()\">Copy</button>
        <a href="{request.base_url}track_show/{new_uuid}">track</a>
      </div>
    """
    return HTMLResponse(html_content)


@app.get("/track/{id}")
async def read_tracking(id: UUID, db: Session = Depends(get_db)):
    track = db.query(Tracking).filter(Tracking.id == str(id)).all()
    current_track = "".join(
        f"""<details>
              <summary>
                {t.ts} | {t.ip} | {t.user_agent}
              </summary>
              {json.dumps(t.as_dict())}
            </details>"""
        for t in track
    )
    return HTMLResponse(f'<div id="events">{current_track}</div>')


@app.get("/new")
async def new_page():
    html_content = """
    <html>
      <head>
        <script src="https://unpkg.com/htmx.org@1.9.10"></script>
        <script>
          const copy = () => {{
            navigator.clipboard.writeText(document.getElementById(\"url\").innerHTML)
          }}
        </script>
      </head>
      <body>
        <div id="new_url"></div>
        <button hx-get="/new_image" hx-target="#new_url">
          New Image
        </button>
      </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/track_show/{id}")
async def show_tracking(id: UUID, db: Session = Depends(get_db)):
    html_content = f"""
    <html>
        <head>
            <title>tracking {id}</title>
            <script src="https://unpkg.com/htmx.org@1.9.10"></script>
        </head>
        <body>
            <h1>Tracking events:</h1>
            <button hx-get="/track/{id}" hx-target="#events">
              refresh
            </button>
            <div hx-get="/track/{id}" hx-trigger="load" hx-swap="outerHTML"></div>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)
