from fastapi import APIRouter, Header, Response, HTTPException
from typing import Optional
import utils
from models import LoginRequest, LoginResponse, UserOut
from models import AddToCartRequest, CartView, CartLineItem, CheckoutRequest, OrderOut
from fastapi import Body
from fastapi import Query
import uuid
from models import AdminGenerateDiscountRequest

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


@router.get("/items")
async def list_items(x_token: Optional[str] = Header(None)):
    """List available items. Requires authentication.

    Response: JSON list of items from `data.json`.
    """
    utils.require_user(x_token)
    data = utils.load_data()
    return data.get("items", [])


@router.post("/cart/add")
async def add_to_cart(payload: AddToCartRequest, x_token: Optional[str] = Header(None)):
    """Add item to user's cart.

    Body: {"item_id": int, "qty": int}
    Merges quantity into existing cart lines.
    """
    user = utils.require_user(x_token)
    data = utils.load_data()

    # find item
    item = next((i for i in data.get("items", []) if i.get("id") == payload.item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="item not found")
    if payload.qty <= 0:
        raise HTTPException(status_code=400, detail="qty must be > 0")

    # merge into cart
    cart = user.get("cart", [])
    existing = next((c for c in cart if c.get("item_id") == payload.item_id), None)
    if existing:
        existing["qty"] += payload.qty
    else:
        cart.append({"item_id": payload.item_id, "qty": payload.qty})

    # persist
    data["users"][user["username"]]["cart"] = cart
    utils.save_data(data)
    return {"success": True, "cart": cart}


@router.get("/cart", response_model=CartView)
async def view_cart(x_token: Optional[str] = Header(None)):
    """View expanded cart. Returns line items with name, price, qty, line_total and cart total."""
    user = utils.require_user(x_token)
    data = utils.load_data()
    cart = user.get("cart", [])
    items_by_id = {i["id"]: i for i in data.get("items", [])}
    lines = []
    total = 0.0
    for line in cart:
        it = items_by_id.get(line["item_id"])
        if not it:
            continue
        line_total = it["price"] * line["qty"]
        total += line_total
        lines.append({"item_id": it["id"], "name": it["name"], "price": it["price"], "qty": line["qty"], "line_total": line_total})
    return {"items": lines, "total": total}


@router.post("/cart/checkout", response_model=OrderOut)
async def checkout(payload: CheckoutRequest = Body(...), x_token: Optional[str] = Header(None)):
    """Checkout the current cart. Optional body: {"discount_code": "CODE"}.

    Applies a single coupon if valid and unused, decrements stock, creates an order, clears cart, and increments order_count_until_coupon.
    """
    user = utils.require_user(x_token)
    data = utils.load_data()
    cart = user.get("cart", [])
    if not cart:
        raise HTTPException(status_code=400, detail="cart is empty")

    # build subtotal and check stock
    items_by_id = {i["id"]: i for i in data.get("items", [])}
    subtotal = 0.0
    for line in cart: # Checks if the item is purchased by someone else and is run out of stock
        it = items_by_id.get(line["item_id"])
        if not it:
            raise HTTPException(status_code=400, detail=f"item {line['item_id']} not found")
        if it.get("stock", 0) < line["qty"]:
            raise HTTPException(status_code=400, detail=f"insufficient stock for item {it['id']}")
        subtotal += it["price"] * line["qty"]

    discount = 0.0
    if payload and payload.discount_code:
        coupon = data.get("coupons", {}).get(payload.discount_code)
        if not coupon:
            raise HTTPException(status_code=400, detail="invalid coupon")
        if coupon.get("used"):
            raise HTTPException(status_code=400, detail="coupon already used")
        # coupon must belong to user
        if coupon.get("user_id") != user.get("id"):
            raise HTTPException(status_code=400, detail="coupon does not belong to user")
        percent = coupon.get("percent_discount", 0)
        discount = round(subtotal * (percent / 100.0), 2)
        # mark used
        data["coupons"][payload.discount_code]["used"] = True

    total = round(subtotal - discount, 2)

    # decrement stock and create order items
    order_items = []
    for line in cart:
        it = items_by_id[line["item_id"]]
        it["stock"] -= line["qty"]
        order_items.append({"item_id": it["id"], "qty": line["qty"]})

    # create order id
    existing_orders = data.get("orders", [])
    order_id = f"order-{user['username']}-{len(existing_orders)+1}"
    order = {"id": order_id, "username": user["username"], "items": order_items, "subtotal": subtotal, "discount": discount, "total": total}
    data.setdefault("orders", []).append(order)

    # clear cart
    data["users"][user["username"]]["cart"] = []
    # increment order_count_until_coupon and total_spent
    data["users"][user["username"]]["order_count_until_coupon"] = data["users"][user["username"]].get("order_count_until_coupon", 0) + 1
    data["users"][user["username"]]["total_spent"] = round(data["users"][user["username"]].get("total_spent", 0.0) + total, 2)

    utils.save_data(data)

    return order


@router.post("/admin/generate_discount")
async def admin_generate_discount(payload: AdminGenerateDiscountRequest = Body(...), x_token: Optional[str] = Header(None)):
    """Generate a coupon for a user. Admin-only.

    Body: {"email": "...", "override": true|false} and returns a coupon
    Creates a single-use coupon with percent taken from config (`coupon_percent`).
    If `override` is true the admin may create a coupon regardless of eligibility.
    Eligibility (non-override): user's `order_count_until_coupon` must be >= config[`nth_order`].
    """
    admin = utils.require_admin(x_token)
    email = payload.email
    override = payload.override

    data = utils.load_data()
    user = next((u for u in data.get("users", {}).values() if u.get("email") == email), None)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    cfg = data.get("config", {})
    nth = cfg.get("nth_order", 5)
    percent = cfg.get("coupon_percent", 10)

    eligible = user.get("order_count_until_coupon", 0) >= nth
    if not eligible and not override:
        raise HTTPException(status_code=400, detail="user not eligible for coupon")

    # generate a reasonably unique coupon code
    code = f"C{uuid.uuid4().hex[:7].upper()}"
    coupon = {
        "user_id": user.get("id"),
        "percent_discount": percent,
        "used": False,
        "expires_on": "2025-12-31",
    }
    data.setdefault("coupons", {})[code] = coupon
    # subtract nth_order so the user has to wait for the next nth orders before another coupon
    prev = data["users"][user["username"]].get("order_count_until_coupon", 0)
    data["users"][user["username"]]["order_count_until_coupon"] = max(prev - nth, 0)
    utils.save_data(data)
    return {"coupon_code": code}


@router.get("/admin/stats")
async def admin_stats(x_token: Optional[str] = Header(None), email: Optional[str] = Query(None)):
    """Admin statistics endpoint.

    Query: `?email=...` to limit stats to a specific user by email.

    Returns per-user stats including items_purchased_count, total_purchase_amount, coupons (list), and total_discount_amount.
    If `email` query param is provided, returns only that user's stats.
    """
    admin = utils.require_admin(x_token)
    data = utils.load_data()

    # precompute orders by username
    orders = data.get("orders", [])
    orders_by_user: dict = {}
    for o in orders:
        u = o.get("username")
        orders_by_user.setdefault(u, []).append(o)

    # map coupons by user_id
    coupons = data.get("coupons", {})
    coupons_by_user: dict = {}
    for code, c in coupons.items():
        uid = c.get("user_id")
        coupons_by_user.setdefault(uid, []).append(code)

    results = []
    for uname, u in data.get("users", {}).items():
        # allow filtering by email instead of username
        if email and u.get("email") != email:
            continue
        user_orders = orders_by_user.get(uname, [])
        items_purchased_count = 0
        total_purchase_amount = 0.0
        total_discount_amount = 0.0
        for o in user_orders:
            # sum quantities
            for li in o.get("items", []):
                items_purchased_count += li.get("qty", 0)
            total_purchase_amount += float(o.get("total", 0.0))
            total_discount_amount += float(o.get("discount", 0.0))

        user_coupons = coupons_by_user.get(u.get("id"), [])

        results.append({
            "username": uname,
            "email": u.get("email"),
            "items_purchased_count": items_purchased_count,
            "total_purchase_amount": round(total_purchase_amount, 2),
            "coupons": user_coupons,
            "total_discount_amount": round(total_discount_amount, 2),
        })

    # if email was requested, return single object
    if email:
        if not results:
            raise HTTPException(status_code=404, detail="user not found")
        return results[0]
    return results
