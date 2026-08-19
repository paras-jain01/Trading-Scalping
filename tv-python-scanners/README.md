# TV Python Scanners 📊

Free, cloud-native Python port of TradingView Pine Script scanners.
Runs on **GitHub Actions (daily)** + **Render.com free tier (intraday)**.
Sends alerts to **Telegram**.

## 🎯 Features

| Scanner | Timeframe | Schedule | Platform |
|---------|-----------|----------|----------|
| **Pre-Breakout AI Scanner** | Daily | 16:00 IST (post-market) | GitHub Actions |
| **15m Intraday Scalper** | 15-minute | Every 15 min (9:15-15:30 IST) | Render.com |

Both are **exact logic replicas** of the Pine Scripts — same parameters, same conditions, same signals.

---

## 🚀 Quick Deploy (5 minutes)

### 1. Fork This Repo
Click **Fork** → your GitHub account.

### 2. Add Secrets (GitHub)
Go to your fork → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Value |
|-------------|-------|
| `TELEGRAM_BOT_TOKEN` | Your bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your numeric chat ID from @userinfobot |

### 3. Enable GitHub Actions
- Go to **Actions** tab → Enable workflows
- The `daily_scan.yml` will run automatically at **16:00 IST, Mon-Fri**

### 4. Deploy Intraday to Render (Free)
1. Go to [render.com](https://render.com) → Sign up with GitHub
2. **New → Web Service** → Connect this repo
3. Render auto-detects `render.yaml` → **Apply**
4. In Render dashboard → **Environment** → Add:
   - `TELEGRAM_BOT_TOKEN` = your token
   - `TELEGRAM_CHAT_ID` = your chat ID
5. **Deploy** → Runs 24/7 on free tier (spins down after 15 min inactivity, wakes on cron)

---

## 📱 Telegram Bot Setup (2 minutes)

```bash
# 1. Create bot
# Message @BotFather → /newbot → name it → copy TOKEN

# 2. Get your chat ID
# Message @userinfobot → /start → copy Chat ID (e.g., 1445588145)

# 3. Test
curl "https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=Test"
```

---

## 📊 What You'll Receive

### Daily Scan (16:00 IST)
```
📊 Daily Pre-Breakout Scan - 20 Aug 2025
Universe: 30 | Scanned: 28
✅ Qualified (≥10/12): 2
⚠️ Close (9-10/12): 1

QUALIFIED:
  • ICICIBANK: 11/12 @ ₹1400.50
  • TRENT: 10/12 @ ₹2965.00

WATCHLIST (close):
  • RELIANCE: 9/12 @ ₹1315.00
```

### Intraday Alerts (Real-time)
```
🟢 INTRADAY BUY ALERT

⚡ INTRADAY SCALPER: ICICIBANK
Price: ₹1402.50 | 8/8 buy conditions
✅ BUY SIGNAL ACTIVE

🟢 BUY CONDITIONS:
  ✅ Price > EMA 50
  ✅ EMA 9 > EMA 21
  ✅ Near VWAP/EMA21
  ✅ RSI 45-68
  ✅ RSI Rising
  ✅ Volume OK
  ✅ Bullish Candle
  ✅ Not at High

📈 LEVELS:
  VWAP: ₹1398.50
  EMA 9/21/50: 1401.2 / 1399.8 / 1395.5
  RSI: 58.3
  Session H/L: 1410.0 / 1392.0
  Target (+1.5%): ₹1423.54
  Stop (-0.8%): ₹1391.28
```

---

## ⚙️ Configuration

Edit `src/config.py` or override via environment:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `scan_universe` | 30 liquid NSE stocks | Symbols to scan |
| `min_conditions_pre_breakout` | 10 | Min conditions for alert (12 total) |
| `min_conditions_intraday` | 7 | Min conditions for alert (8 total) |
| `pre_breakout.proximity_pct` | 0.25 | 52W high proximity (25%) |
| `pre_breakout.consol_threshold` | 0.15 | Consolidation ratio (15%) |
| `intraday_scalper.target_pct` | 0.015 | Target 1.5% |
| `intraday_scalper.stop_pct` | 0.008 | Stop 0.8% |

---

## 🔧 Local Development

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/tv-python-scanners.git
cd tv-python-scanners

# Install
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your token/chat_id

# Run daily scan locally
python -m src.daily_scan

# Run intraday scanner locally (Ctrl+C to stop)
python -m src.intraday_scan
```

---

## 📁 Project Structure

```
tv-python-scanners/
├── src/
│   ├── config.py           # All settings & parameters
│   ├── data.py             # Data fetching (yfinance + nsepython)
│   ├── indicators.py       # pandas-ta indicator wrappers
│   ├── pre_breakout.py     # Daily Pre-Breakout Scanner
│   ├── intraday_scalper.py # 15m Intraday Scalper
│   ├── telegram.py         # Telegram bot sender
│   ├── daily_scan.py       # GitHub Actions entry point
│   └── intraday_scan.py    # Render service entry point
├── .github/workflows/
│   └── daily_scan.yml      # Daily cron (16:00 IST)
├── render.yaml             # Render.com deployment config
├── requirements.txt
├── .env.example
└── README.md
```

---

## 💰 Cost Breakdown

| Component | Cost |
|-----------|------|
| GitHub Actions | **Free** (2,000 min/mo) |
| Render.com Web Service | **Free** (750 hrs/mo, spins down) |
| Render.com Cron Job | **Free** (included) |
| Telegram Bot API | **Free** |
| Data (yfinance/nsepython) | **Free** |
| **Total** | **₹0 / month** |

---

## ⚠️ Limitations & Notes

1. **Data Source**: Uses `yfinance` (15m limited to 60 days) + `nsepython` (daily). For production, consider paid APIs (TwelveData, Alpha Vantage, TrueData).

2. **Render Free Tier**: Service spins down after 15 min inactivity. First request after spin-down takes ~30s to wake. Intraday scanner handles this gracefully.

3. **Rate Limits**: `yfinance` has implicit limits. Scanner uses top 15 symbols for intraday to stay safe.

4. **Timezone**: Assumes system runs in IST. GitHub Actions runners are UTC (cron adjusted). Render Singapore region is UTC+8 (close to IST).

5. **No Broker Execution**: This is **alert-only**. You manually execute trades.

---

## 🛡️ Security

- **Never commit `.env` or secrets**
- **Use GitHub/Render secrets** for tokens
- **Rotate bot token** if exposed: `@BotFather → /revoke → /newbot`

---

## 🤝 Contributing

1. Fork → Create branch → Add feature → PR
2. Keep Pine-to-Python logic exact
3. Add tests for new indicators

---

## 📄 License

MIT — Free for personal use. Not financial advice.

---

## 🙏 Credits

- Original Pine Scripts: TradingView community
- Python libs: `pandas-ta`, `yfinance`, `nsepython`, `pandas`, `numpy`
- Deployment: GitHub Actions, Render.com

---

**Built for traders who want cloud alerts without the cloud bill.** 🚀