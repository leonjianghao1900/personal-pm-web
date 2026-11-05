from fastapi import Depends, HTTPException, Request

from app.authutil import decode_jwt
from app.services import store


async def current_user(request: Request) -> dict:
    settings = request.state.settings
    if not settings.jwt_secret or len(settings.jwt_secret) < 16:
        raise HTTPException(status_code=500, detail="JWT_SECRET 未配置")
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    try:
        payload = decode_jwt(token, settings.jwt_secret)
        user_id = int(payload["sub"])
    except Exception as exc:
        raise HTTPException(status_code=401, detail="未登录") from exc
    user = await store.get_user(request.state.db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录")
    return user


async def workspace_user(user: dict = Depends(current_user)) -> dict:
    if not user.get("workspace_id"):
        raise HTTPException(status_code=403, detail="当前账号未分配工作区")
    return user


async def admin_user(user: dict = Depends(current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
