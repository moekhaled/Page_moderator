from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import AppSetting, Conversation, Message

router = APIRouter(tags=["moderator"])
templates = Jinja2Templates(directory="app/templates")


def _is_authenticated(request: Request) -> bool:
    return bool(request.session.get("moderator_ok"))


@router.get("/moderator/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if _is_authenticated(request):
        return RedirectResponse(url="/moderator/conversations", status_code=302)
    return templates.TemplateResponse("moderator/login.html", {"request": request, "error": None})


@router.post("/moderator/login", response_class=HTMLResponse)
async def login_submit(request: Request, password: str = Form(...)):
    from app.config import settings

    if password == settings.moderator_shared_password:
        request.session["moderator_ok"] = True
        return RedirectResponse(url="/moderator/conversations", status_code=302)
    return templates.TemplateResponse(
        "moderator/login.html", {"request": request, "error": "Invalid password"}, status_code=401
    )


@router.get("/moderator/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/moderator/login", status_code=302)


@router.get("/moderator/conversations", response_class=HTMLResponse)
async def conversation_list(request: Request, db: AsyncSession = Depends(get_db)):
    if not _is_authenticated(request):
        return RedirectResponse(url="/moderator/login", status_code=302)

    rows = (await db.execute(select(Conversation).order_by(Conversation.last_message_at.desc()).limit(100))).scalars().all()
    global_pause = await db.get(AppSetting, "global_llm_paused")
    return templates.TemplateResponse(
        "moderator/conversations.html",
        {
            "request": request,
            "conversations": rows,
            "now": datetime.utcnow(),
            "global_llm_paused": bool(global_pause and global_pause.value.lower() == "true"),
        },
    )


@router.post("/moderator/llm/pause-global")
async def pause_global_llm(request: Request, db: AsyncSession = Depends(get_db)):
    if not _is_authenticated(request):
        return RedirectResponse(url="/moderator/login", status_code=302)

    value = "true" if request.query_params.get("value", "true").lower() == "true" else "false"
    setting = await db.get(AppSetting, "global_llm_paused")
    if not setting:
        setting = AppSetting(key="global_llm_paused", value=value)
        db.add(setting)
    else:
        setting.value = value
        setting.updated_at = datetime.utcnow()
    await db.commit()
    return RedirectResponse(url="/moderator/conversations", status_code=302)


@router.get("/moderator/conversations/{conversation_id}", response_class=HTMLResponse)
async def conversation_detail(conversation_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    if not _is_authenticated(request):
        return RedirectResponse(url="/moderator/login", status_code=302)

    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        return HTMLResponse("Conversation not found", status_code=404)

    messages = (
        await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(500)
        )
    ).scalars().all()
    return templates.TemplateResponse(
        "moderator/conversation_detail.html",
        {
            "request": request,
            "conversation": conversation,
            "messages": messages,
        },
    )


@router.post("/moderator/conversations/{conversation_id}/llm-pause")
async def pause_conversation_llm(conversation_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    if not _is_authenticated(request):
        return RedirectResponse(url="/moderator/login", status_code=302)

    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        return HTMLResponse("Conversation not found", status_code=404)

    value = request.query_params.get("value", "true").lower() == "true"
    conversation.llm_paused = value
    conversation.updated_at = datetime.utcnow()
    await db.commit()
    return RedirectResponse(url=f"/moderator/conversations/{conversation_id}", status_code=302)
