"""ShopBot IA — chatbot de vente propulsé par Claude (web + WhatsApp Business)."""
import os

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import catalog
from .bot import ShopBot

app = FastAPI(title="ShopBot IA")
templates = Jinja2Templates(directory="app/templates")

_bot: ShopBot | None = None


def get_bot() -> ShopBot:
    global _bot
    if _bot is None:
        _bot = ShopBot()
    return _bot


class ChatIn(BaseModel):
    session_id: str
    message: str


@app.get("/", response_class=HTMLResponse)
def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.post("/api/chat")
def chat(body: ChatIn):
    """Réponse du bot en streaming (texte brut, token par token)."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(503, "ANTHROPIC_API_KEY non configurée — voir README")
    return StreamingResponse(
        get_bot().reply_stream(body.session_id, body.message),
        media_type="text/plain; charset=utf-8",
    )


@app.get("/api/products")
def products():
    return catalog.PRODUCTS


@app.get("/api/orders")
def orders():
    return catalog.ORDERS


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "ShopBot IA"}


# ---------- Webhook WhatsApp Business ----------

WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "shopbot-verify")


@app.get("/webhook/whatsapp")
def whatsapp_verify(
    hub_mode: str = Query("", alias="hub.mode"),
    hub_token: str = Query("", alias="hub.verify_token"),
    hub_challenge: str = Query("", alias="hub.challenge"),
):
    """Vérification du webhook par Meta (configuration initiale)."""
    if hub_mode == "subscribe" and hub_token == WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(403, "Token de vérification invalide")


@app.post("/webhook/whatsapp")
async def whatsapp_message(request: Request):
    """Reçoit les messages WhatsApp entrants et répond via le bot.

    En production, la réponse est renvoyée via l'API Graph de Meta
    (POST /{phone_number_id}/messages). Ici la réponse est retournée
    dans le corps pour faciliter les tests.
    """
    payload = await request.json()
    try:
        message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
        sender = message["from"]
        text = message["text"]["body"]
    except (KeyError, IndexError):
        return {"status": "ignored"}

    answer = get_bot().reply(f"wa-{sender}", text)
    return {"status": "ok", "to": sender, "reply": answer}
