import os
import hmac
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from fastmcp import Client


# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

YARGI_MCP_URL = os.getenv(
    "YARGI_MCP_URL",
    "https://yargimcp.surucu.dev/mcp",
)

BRIDGE_API_KEY = os.getenv("BRIDGE_API_KEY")


# ---------------------------------------------------------
# FASTAPI
# ---------------------------------------------------------

app = FastAPI(
    title="Yargi MCP - ChatGPT Actions Bridge",
    description=(
        "ChatGPT Actions ile Yargi MCP arasinda guvenli REST koprusu. "
        "Yargi MCP araclarini listeler ve secilen araci calistirir."
    ),
    version="1.1.0",
)


# ---------------------------------------------------------
# AUTH
# ---------------------------------------------------------

def verify_api_key(
    x_bridge_key: Optional[str] = Header(
        default=None,
        alias="X-Bridge-Key",
    ),
):
    if not BRIDGE_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="BRIDGE_API_KEY sunucu ortam degiskeni tanimlanmamis.",
        )

    if not x_bridge_key:
        raise HTTPException(
            status_code=401,
            detail="X-Bridge-Key API anahtari gerekli.",
        )

    if not hmac.compare_digest(
        x_bridge_key,
        BRIDGE_API_KEY,
    ):
        raise HTTPException(
            status_code=401,
            detail="Gecersiz API anahtari.",
        )

    return True


# ---------------------------------------------------------
# MODELS
# ---------------------------------------------------------

class ToolCallRequest(BaseModel):
    tool_name: str = Field(
        ...,
        description="Calistirilacak Yargi MCP aracinin tam adi.",
    )

    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="MCP aracina gonderilecek parametreler.",
    )


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def make_json_safe(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]

    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except Exception:
            return value.model_dump()

    if hasattr(value, "__dict__"):
        return make_json_safe(value.__dict__)

    return str(value)


# ---------------------------------------------------------
# PUBLIC HEALTH ENDPOINT
# Railway bunu kullanacak.
# ---------------------------------------------------------

@app.get(
    "/health",
    operation_id="healthCheck",
    tags=["System"],
)
async def health_check():
    return {
        "status": "ok",
        "service": "yargi-mcp-chatgpt-bridge",
    }


# ---------------------------------------------------------
# ROOT
# ---------------------------------------------------------

@app.get(
    "/",
    operation_id="serviceInfo",
    tags=["System"],
)
async def root():
    return {
        "service": "Yargi MCP ChatGPT Actions Bridge",
        "status": "running",
        "mcp_server": YARGI_MCP_URL,
        "docs": "/docs",
        "openapi": "/openapi.json",
        "authentication": "X-Bridge-Key",
    }


# ---------------------------------------------------------
# LIST MCP TOOLS
# ---------------------------------------------------------

@app.get(
    "/tools",
    operation_id="listYargiTools",
    tags=["Yargi MCP"],
    dependencies=[Depends(verify_api_key)],
)
async def list_yargi_tools():
    try:
        client = Client(YARGI_MCP_URL)

        async with client:
            tools = await client.list_tools()

        result = []

        for tool in tools:
            result.append(
                {
                    "name": getattr(tool, "name", None),
                    "description": getattr(tool, "description", None),
                    "inputSchema": make_json_safe(
                        getattr(tool, "inputSchema", {})
                    ),
                }
            )

        return {
            "count": len(result),
            "tools": result,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Yargi MCP arac listesi alinamadi: {exc}",
        )


# ---------------------------------------------------------
# CALL MCP TOOL
# ---------------------------------------------------------

@app.post(
    "/call",
    operation_id="callYargiTool",
    tags=["Yargi MCP"],
    dependencies=[Depends(verify_api_key)],
)
async def call_yargi_tool(request: ToolCallRequest):
    try:
        client = Client(YARGI_MCP_URL)

        async with client:
            result = await client.call_tool(
                request.tool_name,
                request.arguments,
                timeout=120.0,
            )

        return {
            "tool_name": request.tool_name,
            "result": make_json_safe(result),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Yargi MCP araci calistirilamadi "
                f"({request.tool_name}): {exc}"
            ),
        )
