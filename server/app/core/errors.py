from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = []
    for err in exc.errors():
        loc = [str(part) for part in err.get("loc", []) if part != "body"]
        field = ".".join(loc) if loc else "request"
        details.append(
            {
                "field": field,
                "message": err.get("msg", "Invalid value"),
                "type": err.get("type", "validation_error"),
            }
        )

    return JSONResponse(
        status_code=422,
        content={
            "code": "validation_error",
            "message": "One or more inputs are invalid.",
            "details": details,
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "http_error")
        message = exc.detail.get("message", "Request failed.")
        details = exc.detail.get("details")
        payload = {"code": code, "message": message}
        if details is not None:
            payload["details"] = details
        for key, value in exc.detail.items():
            if key not in payload and key not in {"code", "message", "details"}:
                payload[key] = value
        return JSONResponse(status_code=exc.status_code, content=payload)

    if isinstance(exc.detail, str):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": "http_error", "message": exc.detail},
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={"code": "http_error", "message": "Request failed."},
    )


def unauthorized(message: str = "Authentication required") -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"code": "unauthorized", "message": message},
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden(message: str = "You do not have permission to perform this action") -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"code": "forbidden", "message": message},
    )
