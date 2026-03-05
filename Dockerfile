FROM python:3.10-slim

WORKDIR /app

COPY kernel_status_server.py .

RUN pip install fastapi uvicorn kubernetes

EXPOSE 9000

CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9000"]