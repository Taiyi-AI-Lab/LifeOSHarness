FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md /app/lifeostomanyagent/
COPY lifeostomanyagent /app/lifeostomanyagent/lifeostomanyagent

WORKDIR /app/lifeostomanyagent
RUN uv pip install --system .

ENV LIFEOS_DATA_ROOT=/data

EXPOSE 8000
CMD ["uvicorn", "lifeostomanyagent.server.main:app", "--host", "0.0.0.0", "--port", "8000"]
