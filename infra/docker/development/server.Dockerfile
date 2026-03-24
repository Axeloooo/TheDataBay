FROM python:3.11.12-slim-bookworm

WORKDIR /code

COPY server/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY server/app /code/app

EXPOSE 8080

CMD ["fastapi", "dev", "app/main.py"]
