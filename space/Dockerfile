# Hugging Face Space (Docker, free CPU) for the engine API. Research use only.
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
WORKDIR /app
RUN pip install --no-cache-dir torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
COPY requirements-engine.txt .
RUN pip install --no-cache-dir -r requirements-engine.txt
USER user
ENV HOME=/home/user TOTALSEG_HOME_DIR=/home/user/.totalsegmentator ENGINE_THREADS=2 \
    ENGINE_DATA=/home/user/data/scans ENGINE_STATE=/home/user/data/state
# model weights (GitHub releases of TotalSegmentator)
RUN totalseg_download_weights -t lung_nodules && totalseg_download_weights -t total_fast
COPY --chown=user engine /app/engine
COPY --chown=user results/cases.json /app/results/cases.json
COPY --chown=user space/start.sh /app/start.sh
EXPOSE 7860
CMD ["bash", "/app/start.sh"]
