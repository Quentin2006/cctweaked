FROM python:3.11-slim

# Install opencode CLI (standalone ELF binary)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://opencode.ai/install | bash -s -- --no-modify-path \
    && ln -s /root/.opencode/bin/opencode /usr/local/bin/opencode

WORKDIR /app

# Copy requirements first for Docker layer caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py /app/
COPY server/ /app/server/
COPY web/ /app/web/

EXPOSE 3000 3001
CMD ["python", "server.py"]
