import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import db
from security import verify_password

ADMIN_PASSWORD = "Fadi!!@@11"

def create_app(bot_sender=None):
    app = FastAPI()
    templates = Jinja2Templates(directory="templates")

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SECRET_KEY", "change-me")
    )

    db.init_db()

    def require_login(request: Request):
        return request.session.get("uid")

    def require_admin(request: Request):
        return request.session.get("admin_auth") == True

    @app.get("/", response_class=HTMLResponse)
    async def login_page(request: Request):
        return templates.TemplateResponse("login.html", {"request": request, "error": None})

    @app.post("/login")
    async def login(request: Request, phone: str = Form(...), password: str = Form(...)):
        user = db.get_user_by_phone(phone)
        if not user or not verify_password(password, user["password_hash"]):
            return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
        request.session["uid"] = int(user["id"])
        return RedirectResponse("/dashboard", status_code=302)

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request):
        uid = require_login(request)
        if not uid:
            return RedirectResponse("/", status_code=302)

        user = db.get_user_by_id(uid)
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "phone": user["phone"],
                "balance": db.fmt_lbp(int(user["balance"])),
                "packages": db.list_packages(),
                "orders": db.list_user_orders(uid),
                "fmt": db.fmt_lbp,
            }
        )

    # -------- SECTIONS --------
    @app.get("/alfa", response_class=HTMLResponse)
    async def alfa_page(request: Request):
        return RedirectResponse("/dashboard", status_code=302)

    @app.get("/netflix", response_class=HTMLResponse)
    async def netflix_page(request: Request):
        uid = require_login(request)
        if not uid:
            return RedirectResponse("/", status_code=302)
        return templates.TemplateResponse("netflix.html", {"request": request})

    @app.get("/shahid", response_class=HTMLResponse)
    async def shahid_page(request: Request):
        uid = require_login(request)
        if not uid:
            return RedirectResponse("/", status_code=302)
        return templates.TemplateResponse("shahid.html", {"request": request})

    # -------- BUY --------
    @app.post("/buy")
    async def buy(request: Request, package_id: int = Form(...), user_number: str = Form(...)):
        uid = require_login(request)
        if not uid:
            return RedirectResponse("/", status_code=302)
        db.create_order(uid, package_id, user_number)
        return RedirectResponse("/dashboard", status_code=302)

    # -------- ADMIN --------
    @app.get("/admin", response_class=HTMLResponse)
    async def admin_login_page(request: Request):
        return templates.TemplateResponse("admin.html", {"request": request, "error": None})

    @app.post("/admin")
    async def admin_login(request: Request, password: str = Form(...)):
        if password == ADMIN_PASSWORD:
            request.session["admin_auth"] = True
            return RedirectResponse("/admin/panel", status_code=302)
        return templates.TemplateResponse("admin.html", {"request": request, "error": "Wrong password"})

    @app.get("/admin/panel", response_class=HTMLResponse)
    async def admin_panel(request: Request):
        if not require_admin(request):
            return RedirectResponse("/admin", status_code=302)
        return templates.TemplateResponse("admin_panel.html", {"request": request})

    @app.post("/admin/add-account")
    async def admin_add_account(request: Request, phone: str = Form(...), email: str = Form(...), password: str = Form(...)):
        if not require_admin(request):
            return RedirectResponse("/admin", status_code=302)
        user = db.get_user_by_phone(phone)
        if not user:
            return HTMLResponse("User not found", status_code=404)
        db.create_account(user["id"], email, password)
        return RedirectResponse("/admin/panel", status_code=302)

    @app.get("/admin/logout")
    async def admin_logout(request: Request):
        request.session.pop("admin_auth", None)
        return RedirectResponse("/admin", status_code=302)

    return app
