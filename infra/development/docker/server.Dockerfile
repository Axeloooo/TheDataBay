FROM python:3.11

WORKDIR /code

COPY server/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY server/app /code/app

EXPOSE 8080

CMD ["fastapi", "dev", "app/main.py", "--host", "0.0.0.0", "--port", "8080"]