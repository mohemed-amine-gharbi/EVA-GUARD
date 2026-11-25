FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 MPLBACKEND=Agg
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
# Par défaut : évaluation complète + figures + dashboard + PDF (voir docker-compose.yml pour les autres services)
CMD ["python", "run_all.py"]
