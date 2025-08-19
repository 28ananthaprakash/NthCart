from fastapi import APIRouter, Header, Response, HTTPException
from typing import Optional
import utils
from models import LoginRequest, LoginResponse, UserOut

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, response: Response):
    """Login endpoint.

    Accepts JSON {"email": "...", "password": "..."} and returns an auth token
    in the `X-Token` header and the JSON body. 

    Example:
    POST /login
    {
      "email": "alex@quicktest.com",
      "password": "11111111"
    }

    Response headers: `X-Token: eyJhbG....`
    """
    user = utils.authenticate(payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid email or password")

    token = utils.create_token_for_user(user)
    # In case if jwt.encode returns bytes in some PyJWT versions
    if isinstance(token, bytes):
        token = token.decode()
    response.headers["X-Token"] = token

    return LoginResponse(token=token, user=UserOut(**{k: v for k, v in user.items() if k != "password"}))

# Only for testing - to be removed soon
@router.get("/protected/user")
async def protected_user(x_token: Optional[str] = Header(None)):
    """Example user-protected endpoint. Returns the username when a valid token is provided."""
    user = utils.require_user(x_token)
    return {"username": user["username"]}

# Only for testing - to be removed soon
@router.get("/protected/admin")
async def protected_admin(x_token: Optional[str] = Header(None)):
    """Example admin-protected endpoint. Requires an admin token."""
    user = utils.require_admin(x_token)
    return {"username": user["username"], "admin": True}
