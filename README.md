# Topup Telegram Bot

A Telegram automation bot that manages prepaid game credits for Mobile Legends and Free Fire. It supports self-service ordering for end users, reseller tier pricing, automated or manual KHQR deposits, and a lightweight admin console operated through custom Telegram keyboards.

## Features

- **Admin-controlled reseller program** – elevate or revoke reseller status and synchronize pricing between normal users and resellers.
- **Dynamic product catalog** – update base items or bundled packages for Mobile Legends, Free Fire, and the ML PH catalog without redeploying the bot.
- **Balance management** – track user balances in an embedded SQLite database, export balances, and approve or reject deposit slips inside Telegram.
- **Deposit automation** – create KHQR codes with `bakong_khqr`, poll payment status, and broadcast successful deposits to a Telegram group.
- **Guided user experience** – localized Khmer prompts, quick-reply keyboards, and formatted product lists tailored to the current user role.
- **Order fulfillment notifications** – validate ML player IDs, deduct balances, and relay purchase details to operational Telegram channels.

## Prerequisites

- Python 3.9+
- Telegram Bot token with access to the [Bot API](https://core.telegram.org/bots/api)
- Bakong KHQR API credentials
- SQLite available on the host machine (bundled with Python)

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install pillow pytelegrambotapi requests qrcode bakong-khqr python-dotenv
```

> Create a `requirements.txt` if you intend to deploy the bot; pin versions that work for your environment. `python-dotenv` is optional in production if you load secrets through another mechanism.

## Configuration

The bot now boots entirely from environment variables, with optional `.env` loading when `python-dotenv` is available (@bot.py#1-90). All secrets **must** be provided before starting the process.

1. Create a `.env` file (or supply the same keys via your host's secret manager):

   ```env
   BOT_TOKEN="your-telegram-bot-token"
   BAKONG_API_TOKEN="your-bakong-api-token"

   ADMIN_IDS="7507149806,1234567890"          # Comma-separated Telegram user IDs
   DEPOSIT_GROUP_ID="-1002721271109"          # Required
   GROUP_OPERATIONS_ID="-1002840078804"       # Optional
   GROUP_FF_ID="-1002840078804"               # Optional
   GROUP_MLBB_ID="-1002840078804"             # Optional

   KHQR_BANK_ACCOUNT="..."
   KHQR_MERCHANT_NAME="..."
   KHQR_MERCHANT_CITY="..."
   KHQR_CURRENCY="USD"                        # Defaults shown
   KHQR_STORE_LABEL="MShop"
   KHQR_PHONE_NUMBER=""                      # Leave blank if unused
   KHQR_BILL_NUMBER="TRX019283775"
   KHQR_TERMINAL_LABEL="Cashier-01"
   KHQR_STATIC="false"                        # Accepts "true" or "false"
   ```

   Integer values (IDs, static flag) are parsed automatically; malformed numbers will raise clear startup errors (@bot.py#23-81).

2. Generate a Bakong KHQR API token and ensure the merchant metadata passed to `khqr.create_qr` matches your account (@bot.py#87-118, @bot.py#1079-1127).

3. Upload branding assets such as `logo.jpg` and `qr.jpg` to the project root; the bot attempts to send these when greeting users or confirming manual deposits (@bot.py#665-693, @bot.py#1194-1208).

## Running the Bot

The entry point initializes the SQLite schema and starts the long-polling loop (@bot.py#104-167, @bot.py#1296-1299).

```bash
python bot.py
```

SQLite data is stored in `user_balances.db` in the project root. Back it up regularly if you expect to migrate servers.

## Admin Commands & Panels

### Slash Commands

| Command | Description |
| --- | --- |
| `/addre <user_id>` | Promote a user to reseller pricing (@bot.py#170-183). |
| `/delre <user_id>` | Revoke reseller status (@bot.py#185-198). |
| `/set_ml <item_id> <normal> <reseller>` | Update Mobile Legends pricing (@bot.py#199-233). |
| `/set_ff <item_id> <normal> <reseller>` | Update Free Fire pricing (same handler as above). |
| `/addpdr <game> <product_id> <normal> <reseller>` | Insert new catalog items (@bot.py#234-291). |
| `/addpack <game> <name> <items> <normal> <reseller>` | Create package bundles (@bot.py#292-375). |
| `/checkuser <user_id>` | Inspect balance, reseller status, and profile (@bot.py#376-438). |
| `/allusers` | Dump all users with balances and statistics (@bot.py#439-505). |
| `/finduser <term>` | Search users by ID, username, or name (@bot.py#505-585). |
| `/allbal` | Export balances as CSV-like text (@bot.py#586-611). |
| `/addb <user_id> <amount>` | Credit balances manually (@bot.py#612-637). |

### Admin Keyboards

After `/start`, admins receive a custom keyboard for navigation (@bot.py#641-782), exposing quick shortcuts such as:

- **User Management** – find, view, or list users.
- **Balance Control** – add/remove balances, export data.
- **Reseller Control** – manage reseller tiers.
- **Price Control** – browse price lists and insert new SKUs.
- **Statistics** – retrieve aggregate metrics (total balance, resellers, active users) (@bot.py#784-836).

Each button displays usage instructions or triggers the relevant slash command handler (@bot.py#884-976).

## User Flows

- **Welcome & Navigation:** `/start` serves localized Khmer guidance and quick action buttons (@bot.py#641-715).
- **Account Snapshot:** "👤 គណនី" returns Telegram username, ID, and wallet balance (@bot.py#698-705).
- **Catalog Browsing:** "🎮 Game" lets users browse ML, FF, or ML PH pricing with tier-aware formatting (@bot.py#706-1013).
- **Deposits:** "💰 ដាក់ប្រាក់" launches the KHQR payment flow, generates a QR code, polls for payment, and posts a group notification when successful (@bot.py#1015-1121).
- **Manual Proofs:** Users who submit screenshots trigger admin approval callbacks that auto-credit balances when confirmed (@bot.py#1133-1207).
- **Purchasing:** Orders consist of `player_id server_id item_id`. The bot validates IDs (for ML via external API), deducts balances, and notifies operations groups (@bot.py#1225-1288).

## Data Storage

Balances and reseller flags persist in `user_balances.db` with a single `balances` table (@bot.py#104-167). All helper functions encapsulate reads and writes around new SQLite connections to keep handlers stateless.

## Deployment Notes

- **Disable logging noise** by adjusting `logging.basicConfig` or routing logs to a file (@bot.py#18-20).
- **Thread safety:** `pytelegrambotapi` spawns worker threads; SQLite’s default settings can handle these short-lived connections, but heavy load may require a dedicated DB server.
- **Timeouts:** KHQR polling uses a simple 30-second loop. Adjust `range(30)` in `check_payment` for different retry windows (@bot.py#1123-1132).
- **Resilience:** Wrap external calls (`requests.get`, `khqr.check_payment`) with additional error handling or backoff if network conditions are unreliable.

## Contact

Have questions or want to share feedback? Reach out via Telegram: [@CHHEAN0](https://t.me/CHHEAN0).

## Support the project

If this gateway is useful in your workflow, feel free to support future maintenance via KHQR. Scan either code below with your preferred wallet.

| KHQR (KHR) | KHQR (USD) |
| --- | --- |
| ![KHQR KHR payment code](https://storage.perfectcdn.com/axz9n1/phmp0ofcq4eu4gdh.jpg) | ![KHQR USD payment code](https://storage.perfectcdn.com/axz9n1/g3ccceb3ng7o9431.jpg) |
