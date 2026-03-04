FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY frontend/package.json frontend/package-lock.json frontend/
RUN cd frontend && npm ci

COPY frontend/ frontend/
RUN cd frontend && npm run build

COPY backend/ backend/

RUN mkdir -p logs

RUN git clone https://github.com/nasa/NASTRAN-95.git codebases/nastran95

EXPOSE 8000

CMD ["python", "-c", "import os; port = os.environ.get('PORT', '8000'); os.execvp('uvicorn', ['uvicorn', 'backend.app:app', '--host', '0.0.0.0', '--port', port])"]
