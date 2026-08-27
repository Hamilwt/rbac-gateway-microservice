FROM python:3.13-slim

WORKDIR /app

# Install dependencies first so Docker can cache this layer
# and skip reinstalling packages every time your code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the actual application code
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]