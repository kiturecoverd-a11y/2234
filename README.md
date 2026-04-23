# 🤖 DM File Bot

A **professional, production-ready** Discord bot that securely forwards files and messages directly to users' DMs.

Perfect for distributing `.rar`, `.zip`, `.apk`, `.msg`, and many more file types to your community.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📁 **File Transfer** | Send any supported file directly to user DMs |
| 💬 **DM Messaging** | Broadcast text messages to users or roles |
| 🔒 **Owner-Only** | Commands restricted to configured bot owners |
| 📏 **File Validation** | Automatic type & size checking before sending |
| ⚡ **Rate Limiting** | Built-in cooldowns to respect Discord limits |
| 📊 **Detailed Reports** | Success/failure summary after every operation |
| 🌐 **Railway Ready** | Health-check server included for Railway deployment |
| 📝 **Professional Logging** | File + console logging with daily rotation |

---

## 📋 Supported File Types

`.rar` `.zip` `.7z` `.tar` `.gz` `.bz2`  
`.apk` `.ipa`  
`.msg` `.eml`  
`.exe` `.msi` `.bin` `.iso` `.dmg`  
`.pdf` `.doc` `.docx` `.xls` `.xlsx`  
`.txt` `.json` `.xml` `.csv`  
`.mp4` `.mov` `.avi` `.mkv`  
`.jpg` `.jpeg` `.png` `.gif` `.webp`  
`.mp3` `.wav` `.flac` `.aac`

---

## 🚀 Quick Start (Local)

### 1. Prerequisites
- Python **3.11+**
- A [Discord Bot Token](https://discord.com/developers/applications)

### 2. Install Dependencies
```bash
cd discord_file_bot
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
copy .env.example .env
```
Edit `.env` and set:
```env
DISCORD_TOKEN=your_bot_token_here
OWNER_IDS=your_discord_user_id
```

### 4. Run
```bash
python main.py
```

---

## 🛠 Commands

| Command | Aliases | Description | Example |
|---------|---------|-------------|---------|
| `!sendfile` | `sf`, `send`, `dmfile` | Send attached files to user(s) | `!sendfile @user` (attach files) |
| `!sendmsg` | `sm`, `dm`, `senddm` | Send a DM message to user(s) | `!sendmsg @user Hello!` |
| `!sendrole` | — | DM all members of a role | `!sendrole @role Announcement` |
| `!fileinfo` | `finfo` | Show file limits & info | `!fileinfo` |
| `!ping` | — | Check bot latency | `!ping` |
| `!info` | `about` | Show bot stats | `!info` |
| `!help` | `h` | Show help menu | `!help sendfile` |

> Replace `!` with your configured prefix if changed.

---

## ⚙️ Configuration

All settings are controlled via **environment variables**:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_TOKEN` | ✅ | — | Your Discord bot token |
| `OWNER_IDS` | ✅ | — | Comma-separated owner Discord IDs |
| `COMMAND_PREFIX` | ❌ | `!` | Command prefix |
| `MAX_FILE_SIZE_MB` | ❌ | `500` | Max file size (MB) |
| `COOLDOWN_SECONDS` | ❌ | `3` | Command cooldown |
| `MAX_FILES_PER_COMMAND` | ❌ | `10` | Max files per command |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level |
| `PORT` | ❌ | `8080` | Health-check port |

---

## 🚂 Deploy on Railway

Railway requires an open port to keep the service alive. This bot includes a built-in health-check server.

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/discord_file_bot.git
git push -u origin main
```

### Step 2: Create Railway Project
1. Go to [railway.app](https://railway.app) and log in
2. Click **New Project**
3. Choose **Deploy from GitHub repo**
4. Select your repository

### Step 3: Add Environment Variables
1. Go to your project **Variables** tab
2. Add the following:
   - `DISCORD_TOKEN` → your bot token
   - `OWNER_IDS` → your Discord user ID(s)
   - `MAX_FILE_SIZE_MB` → `500` (or `50` if no Nitro)
   - Any other optional variables

### Step 4: Deploy
Railway will auto-detect `requirements.txt` and `runtime.txt` and deploy your bot.

### Step 5: Verify
- Check **Deploy Logs** to see `✅ Bot is ready and online!`
- The health-check server runs on the internal `PORT` assigned by Railway

---

## 🔐 Required Discord Intents

Go to your bot's **Bot** settings in the [Developer Portal](https://discord.com/developers/applications) and enable:

- ✅ **Message Content Intent**
- ✅ **Server Members Intent**
- ✅ **Presence Intent** (optional)

### Required Bot Permissions

| Permission | Why |
|------------|-----|
| `Send Messages` | Send confirmation embeds in channels |
| `Read Message History` | Read commands in channels |
| `Attach Files` | Read attached files to forward |
| `Embed Links` | Send rich embed responses |
| `Use External Emojis` | Display emoji in embeds |
| `Add Reactions` | Confirmation reactions for `!sendrole` |

**Recommended OAuth2 URL:**
```
https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot&permissions=76864
```

---

## 📁 Project Structure

```
discord_file_bot/
├── commands/
│   ├── __init__.py
│   ├── file_handler.py      # File & message DM commands
│   └── utility.py           # Utility commands (ping, help, info)
├── config/
│   ├── __init__.py
│   └── config.py            # Centralized configuration
├── events/
│   ├── __init__.py
│   ├── bot_events.py        # on_ready, guild join/leave
│   └── message_events.py    # Error handling & logging
├── utils/
│   ├── __init__.py
│   ├── file_utils.py        # File validation & streaming
│   ├── helpers.py           # Embed builder, decorators
│   └── logger.py            # Professional logging setup
├── logs/                    # Daily log files (auto-created)
├── .env.example             # Environment template
├── .gitignore               # Git ignore rules
├── main.py                  # Entry point + health server
├── Procfile                 # Railway process definition
├── railway.json             # Railway deployment config
├── requirements.txt         # Python dependencies
├── runtime.txt              # Python version
└── README.md                # This file
```

---

## 🛡 Security Notes

- **NEVER** commit your `.env` file or expose your `DISCORD_TOKEN`
- Only configure **trusted** users in `OWNER_IDS`
- The bot streams files **in-memory** — nothing is saved to disk
- All commands are owner-restricted by default

---

## 📝 License

This project is provided as-is for educational and commercial use.

---

**Version:** 2.1.0  
**Made with ❤️ for Discord communities**
