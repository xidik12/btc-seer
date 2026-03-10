"""Share endpoints — upload image for HTTPS download + send image to user's Telegram chat."""

import base64
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException

from app.telegram_auth import _verify_telegram_init_data

router = APIRouter(prefix="/api/share", tags=["share"])

UPLOADS_DIR = Path("/data/uploads")


def _decode_data_url(data_url: str) -> bytes:
    """Strip data URL prefix and decode base64 to raw bytes."""
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    return base64.b64decode(data_url)


@router.post("/upload")
async def upload_share_image(request: Request):
    """Accept a base64 data URL, save as PNG, return HTTPS-accessible path."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    _verify_telegram_init_data(init_data, max_age=86400)

    body = await request.json()
    image_data = body.get("image")
    if not image_data:
        raise HTTPException(status_code=400, detail="Missing 'image' field")

    try:
        img_bytes = _decode_data_url(image_data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    filepath = UPLOADS_DIR / filename
    filepath.write_bytes(img_bytes)

    return {"url": f"/uploads/{filename}"}


@router.post("/send-to-chat")
async def send_image_to_chat(request: Request):
    """Decode base64 image and send it to the user's Telegram chat via Bot API."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    user_data = _verify_telegram_init_data(init_data, max_age=86400)
    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(status_code=400, detail="Could not determine Telegram user ID")

    body = await request.json()
    image_data = body.get("image")
    if not image_data:
        raise HTTPException(status_code=400, detail="Missing 'image' field")

    try:
        img_bytes = _decode_data_url(image_data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")

    bot = getattr(request.app.state, "bot", None)
    if not bot:
        raise HTTPException(status_code=503, detail="Telegram bot not available")

    from aiogram.types import BufferedInputFile

    photo = BufferedInputFile(img_bytes, filename="btc-seer.png")
    try:
        await bot.send_photo(chat_id=telegram_id, photo=photo)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to send photo: {e}")

    return {"ok": True}
