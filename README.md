# Telegram Content Scraper / Cloner (Premium Edition)

A professional tool for cleaning and cloning content between Telegram channels in real-time.

## features

* **Real-time Cloning**: Instant transfer of posts from Donor to Target channels.
* **Media Support**: Photos, Videos, Documents, Audio, Albums (Media Groups).
* **Smart Modification**:
  * **Button Replacement**: Automatically replaces/removes buttons in posts.
  * **Link Replacement**: Intelligent text replacement (e.g., removing competitor names/links).
* **Admin Panel**: Full control via Telegram inline menu.
* **History Scraper**: Tools to scrape old messages (First N, Latest N, Full History).
* **Safe**: Uses official Telegram MTProto API.

## 🚀 Quick Start

### 1. Installation

Run the included installer:

```cmd
install.bat
```

Or manually:

```bash
pip install -r requirements.txt
```

### 2. Configuration

**Step A: API Keys**

1. Go to [my.telegram.org](https://my.telegram.org)
2. Create a new application
3. Open `keys.py` and paste your `API_ID` and `API_HASH`.

**Step B: Bot Token**

1. Go to @BotFather in Telegram
2. Create a new bot and get the Token
3. Open `.env` and paste your `BOT_TOKEN`.
4. Get your own Telegram ID (via @userinfobot) and paste it as `ADMIN_ID` in `.env`.

### 3. Usage

Run the bot:

```cmd
python main.py
```

1. **Login**: On first run, it will ask for your Phone Number (for the User Session). This is needed to read messages from donor channels.
2. **Setup**:
   * The Bot will send you an Admin Panel in PM.
   * Use **"➕ Add Channel Pair"** to configure scraping.
   * *(Important)*: Add the Bot as **Admin** in your Target Channel.
   * *(Important)*: Join the Donor Channel with your User account.

## ⚙️ Admin Commands

* `/start` - Open Admin Panel
* `/addpair` - Add a new pair (Donor -> Target)
* `/list` - Show active pairs

## 📝 License

Private/Commercial Usage.
