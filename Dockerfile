FROM python:3.11-slim

# Install opencode CLI (standalone ELF binary)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://opencode.ai/install | bash -s -- --no-modify-path \
    && ln -s /root/.opencode/bin/opencode /usr/local/bin/opencode

WORKDIR /app

# Copy application code
COPY server.py TurtleManager.py ai_agent.py bootstrap.py requirements.txt /app/
COPY web/ /app/web/
COPY data.defaults/ /app/data.defaults/

EXPOSE 3000 3001
CMD ["python", "server.py"]
