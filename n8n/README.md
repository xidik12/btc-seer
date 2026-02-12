# n8n Marketing Automation for BTC Seer

Self-hosted n8n workflows for automated Twitter and Telegram channel posting.

## Railway Setup

### 1. Create Railway Project

- Go to [railway.app](https://railway.app) and create a new project named `btc-seer-n8n`

### 2. Add n8n Docker Service

- Click "New Service" → "Docker Image"
- Image: `n8nio/n8n:latest`

### 3. Environment Variables

Set the following variables in the service settings:

```
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=<your-secure-password>
N8N_PORT=5678
N8N_ENCRYPTION_KEY=<generate-a-random-key>
WEBHOOK_URL=https://<your-railway-domain>
N8N_PROTOCOL=https
```

### 4. Add Volume

- In service settings, add a volume mounted at `/home/node/.n8n`
- This persists workflows, credentials, and execution history across deployments

### 5. Expose Domain

- In service settings → Networking → Generate Domain
- Note the URL (e.g., `btc-seer-n8n-production.up.railway.app`)
- Update `WEBHOOK_URL` env var to match this domain

### 6. Configure Credentials in n8n UI

Open your n8n instance and add these credentials:

#### Twitter (X) OAuth2
1. Go to Settings → Credentials → Add Credential → Twitter OAuth2
2. Enter your Twitter API Key, Secret, Access Token, and Access Token Secret
3. These require a Twitter Developer account with Elevated access

#### Telegram Bot
1. Go to Settings → Credentials → Add Credential → Telegram
2. Enter the bot token for your BTC Seer Signals bot
3. The bot must be an admin of the `@BTCSeerSignals` channel

### 7. Import Workflows

1. Go to Settings → Import from File
2. Import each JSON file from the `workflows/` directory:
   - `morning-prediction-tweet.json` — Daily 9:00 UTC prediction tweet
   - `evening-results-tweet.json` — Daily 21:00 UTC results tweet
   - `weekly-stats-tweet.json` — Sunday 12:00 UTC weekly stats
   - `telegram-channel-prediction.json` — Every 30 min Telegram post
   - `daily-telegram-summary.json` — Daily 22:00 UTC Telegram digest
3. Activate each workflow after importing

## API Endpoints Used

All workflows call these public BTC Seer endpoints (no auth required):

| Endpoint | Returns |
|----------|---------|
| `GET /api/predictions/current` | direction, confidence, predicted_change_pct per timeframe |
| `GET /api/predictions/quant` | composite_score, action, signal breakdown |
| `GET /api/market/price` | price, change_24h_pct |
| `GET /api/history/accuracy?days=N` | accuracy_pct, by_timeframe |
| `GET /api/signals/current` | action, entry, target, stop_loss, reasoning |

Base URL: `https://btc-oracle-production.up.railway.app`
