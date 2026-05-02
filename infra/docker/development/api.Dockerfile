FROM python:3.11.12-slim-bookworm

WORKDIR /code

COPY api/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY api/app /code/app
COPY api/alembic /code/alembic
COPY api/alembic.ini /code/alembic.ini
COPY shared /code/shared

EXPOSE 8080

CMD ["fastapi", "dev", "app/main.py"]
