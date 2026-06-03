FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY lifeostomanyagent/pyproject.toml lifeostomanyagent/README.md /app/lifeostomanyagent/
COPY lifeostomanyagent/lifeostomanyagent /app/lifeostomanyagent/lifeostomanyagent
COPY 003-life-os /app/003-life-os

WORKDIR /app/lifeostomanyagent
RUN uv pip install --system .

ENV BWS_FUXIAN_ROOT=/app/003-life-os
ENV LIFEOS_DATA_ROOT=/data

EXPOSE 8000
CMD ["uvicorn", "lifeostomanyagent.server.main:app", "--host", "0.0.0.0", "--port", "8000"]
