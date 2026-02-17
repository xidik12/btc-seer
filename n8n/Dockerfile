FROM n8nio/n8n:latest

# Run as root to handle Railway volume permissions
USER root

# Default user folder — n8n creates .n8n inside this path
ENV N8N_USER_FOLDER=/home/node

# Fix volume permissions at startup, then run n8n
ENTRYPOINT []
CMD ["sh", "-c", "chown -R node:node /home/node/.n8n 2>/dev/null; N8N_PORT=${PORT:-5678} exec n8n start"]
