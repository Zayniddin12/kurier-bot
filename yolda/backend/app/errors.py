from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(HTTPException):
    def __init__(self, status: int, detail: str, field: str | None = None):
        super().__init__(status, detail)
        self.field = field


def install(app: FastAPI):
    @app.exception_handler(ApiError)
    async def _api(_: Request, e: ApiError):
        body = {"detail": e.detail}
        if e.field:
            body["field"] = e.field
        return JSONResponse(body, status_code=e.status_code)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        d = e.detail if isinstance(e.detail, str) else "Xatolik"
        if e.status_code == 404 and d == "Not Found":
            d = "Topilmadi"
        return JSONResponse({"detail": d}, status_code=e.status_code, headers=getattr(e, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _val(_: Request, e: RequestValidationError):
        errs = e.errors()
        first = errs[0] if errs else {}
        loc = ".".join(str(x) for x in first.get("loc", []) if x not in ("body", "query"))
        return JSONResponse({"detail": f"Maydon noto'g'ri: {loc} — {first.get('msg', '')}".strip(), "field": loc or None,
                             "errors": [{"loc": list(x["loc"]), "msg": x["msg"]} for x in errs]}, status_code=422)
