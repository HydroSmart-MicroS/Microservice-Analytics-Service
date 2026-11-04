FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY app app
COPY tests tests
RUN python -m unittest discover -s tests -v
COPY migrate.py .
COPY migrations migrations
USER 10001:10001
EXPOSE 8080
CMD ["sh", "-c", "python migrate.py && uvicorn app.main:app --host 0.0.0.0 --port 8080"]
