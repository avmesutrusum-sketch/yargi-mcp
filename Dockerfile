FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

RUN pip install --no-cache-dir \
    "fastapi>=0.115.14" \
    "uvicorn[standard]>=0.30.0" \
    "fastmcp>=2.10.5" \
    "pydantic>=2.11.4"

COPY gpt_actions_bridge.py ./

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/health', timeout=5)" || exit 1

CMD ["sh", "-c", "uvicorn gpt_actions_bridge:app --host 0.0.0.0 --port ${PORT:-8000}"]
