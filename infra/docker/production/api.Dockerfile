FROM python:3.11.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /code

COPY api/requirements.txt /code/requirements.txt
RUN pip install --upgrade pip \
  && pip install -r /code/requirements.txt

COPY api/app /code/app
COPY api/alembic /code/alembic
COPY api/alembic.ini /code/alembic.ini
COPY shared /code/shared

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/', timeout=3).read()" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
