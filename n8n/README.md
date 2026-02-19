# BTC Seer AI Marketing Automation

Autonomous AI marketing agent using n8n + Claude API to auto-generate and post content across 10 platforms, driving users to `@BTC_Seer_Bot` on Telegram.

**22 workflows** | **10 platforms** | **~$0.06/day Claude API cost** | **~$5/mo n8n hosting**

## Architecture

```
n8n (Railway)
  ├── Schedule Triggers (cron/interval)
  ├── BTC Seer API → Live prediction data
  ├── Claude API → AI-generated content (varied, on-brand)
  └── Platform APIs → Auto-post to 10 channels
```

Every AI workflow follows: **Trigger → Fetch Data → Check Post-Worthy → Claude API → Post → Log**

## Railway Deployment

### Option A: Deploy from Dockerfile (Recommended)

1. Create a new Railway project: `btc-seer-n8n`
2. Add service → From Repo → point to the `n8n/` directory
3. Railway auto-detects the Dockerfile

### Option B: Deploy Docker Image

1. Create Railway project → New Service → Docker Image
2. Image: `n8nio/n8n:latest`

### Environment Variables

Copy from `.env.example` and fill in your credentials:

```
# Core n8n
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=<secure-password>
N8N_ENCRYPTION_KEY=<openssl rand -hex 32>
N8N_PORT=5678
N8N_PROTOCOL=https
WEBHOOK_URL=https://<your-railway-domain>

# BTC Seer Backend
BTC_SEER_API_BASE=https://btc-oracle-production.up.railway.app

# Claude API
ANTHROPIC_API_KEY=sk-ant-api03-...
CLAUDE_MODEL=claude-sonnet-4-6-20250929
CLAUDE_DAILY_BUDGET_USD=5.00

# Platform credentials (see Platform Setup below)
```

### Volume

Add a volume mounted at `/home/node/.n8n` to persist workflows, credentials, and execution history.

### Domain

Generate a domain in Networking settings, then update `WEBHOOK_URL` to match.

## Workflows (22 total)

### Twitter/X (7 workflows)

| File | Trigger | What it does |
|------|---------|-------------|
| `twitter-morning-prediction-ai.json` | Daily 9:00 UTC | Claude generates varied morning prediction tweet |
| `twitter-evening-results-ai.json` | Daily 21:00 UTC | Claude summarizes actual vs predicted, transparent about misses |
| `twitter-weekly-thread.json` | Sunday 12:00 UTC | Claude generates 4-6 tweet thread (accuracy, insights) |
| `twitter-market-commentary.json` | Every 4h (event-gated) | Claude analyzes why price moved, only posts if noteworthy |
| `twitter-auto-reply.json` | Every 30min | Claude replies to @BTCSeerBot mentions |
| `twitter-quote-news.json` | Every 2h | Claude adds prediction angle to crypto news |
| `twitter-engage-hashtags.json` | Every 30min | Like + reply to #Bitcoin questions (max 3/run) |

### Telegram (4 workflows)

| File | Trigger | What it does |
|------|---------|-------------|
| `telegram-prediction-signal-ai.json` | Every 30min | Claude varies format, adds reasoning section |
| `telegram-daily-summary-ai.json` | Daily 22:00 UTC | Claude generates daily recap with insights |
| `telegram-breaking-news.json` | Every 5min (event-gated) | Only posts on >5% moves or whale activity |
| `telegram-weekly-report.json` | Sunday 20:00 UTC | Detailed performance report |

### Reddit (2 workflows)

| File | Trigger | What it does |
|------|---------|-------------|
| `reddit-weekly-value-post.json` | Tuesday 15:00 UTC | 500-1000 word analysis for r/CryptoCurrency |
| `reddit-daily-comments.json` | Every 6h | Answers BTC questions on crypto subreddits (max 2/run) |

### Facebook/Instagram (3 workflows)

| File | Trigger | What it does |
|------|---------|-------------|
| `facebook-daily-prediction.json` | Daily 10:00 UTC | AI caption + prediction to FB page |
| `instagram-prediction-post.json` | Daily 10:30 UTC | IG-optimized caption + media container |
| `facebook-group-weekly.json` | Wednesday 18:00 UTC | Discussion-focused post for crypto groups |

### LinkedIn (1 workflow)

| File | Trigger | What it does |
|------|---------|-------------|
| `linkedin-weekly-post.json` | Thursday 14:00 UTC | Thought-leadership article on AI + trading |

### Medium (1 workflow)

| File | Trigger | What it does |
|------|---------|-------------|
| `medium-weekly-article.json` | Saturday 10:00 UTC | 1500-2000 word market analysis article |

### Discord (1 workflow)

| File | Trigger | What it does |
|------|---------|-------------|
| `discord-auto-post.json` | Every 30min | Formatted prediction embed (no Claude needed) |

### YouTube (1 workflow)

| File | Trigger | What it does |
|------|---------|-------------|
| `youtube-community-post.json` | Sunday 16:00 UTC | Weekly summary community post |

### Quora (1 workflow)

| File | Trigger | What it does |
|------|---------|-------------|
| `quora-answer-questions.json` | Daily 12:00 UTC | Generates answers for manual posting (no public API) |

### Analytics (1 workflow)

| File | Trigger | What it does |
|------|---------|-------------|
| `analytics-cost-tracker.json` | Every 1h | Tracks Claude API costs, budget alerts via Discord |

## API Endpoints Used

All workflows call BTC Seer public endpoints (no auth required):

| Endpoint | Returns |
|----------|---------|
| `GET /api/marketing/daily-summary` | Price, predictions, accuracy, sentiment, signals, macro data |
| `GET /api/marketing/performance-card?days=7` | Weekly stats, best/worst calls, streak |
| `GET /api/marketing/trending-analysis` | Post-worthy events (price moves, whale activity) |
| `GET /api/predictions/current` | Direction, confidence per timeframe |
| `GET /api/signals/current` | Action, entry, target, stop-loss, reasoning |
| `GET /api/history/accuracy?days=N` | Accuracy by timeframe and confidence |
| `GET /api/news` | Latest crypto news with sentiment |
| `GET /api/market/price` | Current BTC price |

Base URL: `https://btc-oracle-production.up.railway.app`

## Platform Setup

### 1. Claude API (Required)
- Get key at [console.anthropic.com](https://console.anthropic.com)
- Set `ANTHROPIC_API_KEY` in n8n

### 2. Twitter/X Developer
- Apply at [developer.twitter.com](https://developer.twitter.com)
- Need **Elevated access** for posting (1-2 day approval)
- Create OAuth 2.0 app, get API Key + Secret + Access Token + Secret
- In n8n: Settings -> Credentials -> Add -> Twitter OAuth2
- Note the credential ID and update workflow files

### 3. Telegram
- Already have the bot. Create `@BTCSeerSignals` channel
- Bot must be admin of the channel
- In n8n: Settings -> Credentials -> Add -> Telegram
- Set `TELEGRAM_CHANNEL_ID=@BTCSeerSignals`

### 4. Reddit
- Create a bot account, build karma first
- Create app at [reddit.com/prefs/apps](https://reddit.com/prefs/apps) (script type)
- Set `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, credentials in env

### 5. Meta (Facebook + Instagram)
- Create FB page "BTC Seer" at [developers.facebook.com](https://developers.facebook.com)
- Connect IG business account
- Get Page Access Token with `pages_manage_posts` + `instagram_content_publish` scopes
- Set `META_PAGE_ID`, `META_IG_USER_ID`, `META_PAGE_ACCESS_TOKEN`

### 6. LinkedIn
- Create app at [linkedin.com/developers](https://linkedin.com/developers)
- Get access token with `w_member_social` scope
- Set `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_URN`

### 7. Medium
- Get integration token at [medium.com/me/settings](https://medium.com/me/settings)
- Set `MEDIUM_INTEGRATION_TOKEN`

### 8. Discord
- Create BTC Seer server + bot at [discord.com/developers](https://discord.com/developers)
- Add bot to server, get channel ID for #predictions
- Set `DISCORD_BOT_TOKEN`, `DISCORD_CHANNEL_ID`

### 9. YouTube
- Create channel, get API key at [console.cloud.google.com](https://console.cloud.google.com)
- Community posts require YouTube Studio API (limited access)
- Set `YOUTUBE_API_KEY`, `YOUTUBE_CHANNEL_ID`

### 10. Quora
- No public API — workflow generates answers for manual posting
- Optionally set `QUORA_SESSION_COOKIE` for browser automation

## Import Workflows

1. Open your n8n instance
2. Go to **Workflows** -> **Import from File**
3. Import each JSON from `workflows/` directory
4. Update credential IDs in each workflow (search for `REPLACE_WITH_CREDENTIAL_ID`)
5. **Activation order** (start with lowest risk):
   1. `analytics-cost-tracker.json` — monitor costs first
   2. `discord-auto-post.json` — test with your own Discord
   3. `telegram-*` workflows — your own channel
   4. `twitter-morning-prediction-ai.json` — first public post
   5. Remaining Twitter workflows
   6. Reddit, Facebook, LinkedIn, Medium, YouTube, Quora

## Cost Controls

- **Daily budget**: `$5.00` (set via `CLAUDE_DAILY_BUDGET_USD`)
- **Estimated daily cost**: ~$0.06 (9-10 Claude calls/day at ~$0.006/call)
- **Cost tracker**: `analytics-cost-tracker.json` runs hourly, alerts via Discord
- **Monitor actual usage**: [console.anthropic.com/account/usage](https://console.anthropic.com/account/usage)

## Troubleshooting

- **Workflow not triggering**: Check it's activated (toggle in n8n UI)
- **Claude API errors**: Verify `ANTHROPIC_API_KEY` is set correctly
- **Twitter 403**: Need Elevated access, not just Essential
- **Reddit 429**: Rate limited — reduce frequency or build more karma
- **Instagram media errors**: Requires a valid public image URL for the `image_url` field
- **Empty posts**: Check BTC Seer API is running (`/health` endpoint)
