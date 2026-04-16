from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.routes import account_router, event_router, source_router, user_router

app = FastAPI(title="python-demo")
templates = Jinja2Templates(directory="app/templates")
app.include_router(account_router)
app.include_router(source_router)
app.include_router(user_router)
app.include_router(event_router)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})


@app.get("/health")
def health():
    return {"status": "ok"}
