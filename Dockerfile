FROM python:3.11-slim
WORKDIR /app
COPY boundarycast-personal-weather/services/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY boundarycast-personal-weather /app/boundarycast-personal-weather
WORKDIR /app/boundarycast-personal-weather/services/api
EXPOSE 8787
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8787}"]
