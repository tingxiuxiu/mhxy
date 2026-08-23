FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY init_db.py run.py ./

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
