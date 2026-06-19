FROM python:3.11-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/

FROM base AS test
RUN pip install --no-cache-dir pytest pytest-cov httpx
COPY tests/ ./tests/
CMD ["pytest", "-v", "--cov=app", "--cov-report=term"]

FROM base AS production
EXPOSE 5005
CMD ["python", "app/main.py", "--host", "0.0.0.0", "--port", "5005"]