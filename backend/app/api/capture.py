"""Capture state endpoints for controlling glasses image capture."""

from fastapi import APIRouter, Depends

from app.auth import CurrentUser, get_current_user

router = APIRouter(prefix="/capture", tags=["capture"])

# In-memory capture state per Supabase user_id (demo quality, resets on restart)
_capture_state: dict[str, bool] = {}


@router.post("/start")
async def start_capture(current_user: CurrentUser = Depends(get_current_user)):
    _capture_state[str(current_user.id)] = True
    return {"capturing": True}


@router.post("/stop")
async def stop_capture(current_user: CurrentUser = Depends(get_current_user)):
    _capture_state[str(current_user.id)] = False
    return {"capturing": False}


@router.get("/state")
async def get_my_capture_state(current_user: CurrentUser = Depends(get_current_user)):
    return {"capturing": _capture_state.get(str(current_user.id), False)}


@router.get("/state/{user_id}")
async def get_capture_state_by_user(user_id: str):
    """Polled by the glasses app to check if capture is active for a given user."""
    return {"capturing": _capture_state.get(user_id, False)}


@router.post("/toggle/{user_id}")
async def toggle_capture_by_user(user_id: str):
    """Called by the glasses app physical button to toggle capture without needing a JWT."""
    current = _capture_state.get(user_id, False)
    _capture_state[user_id] = not current
    return {"capturing": not current}
