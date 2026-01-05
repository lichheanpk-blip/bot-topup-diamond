
import sqlite3
from PIL import Image
from telebot import TeleBot
from io import BytesIO
import threading
import time
import logging
import requests
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import os
import qrcode
from bakong_khqr import KHQR

# Set up logging
logging.basicConfig(level=logging.INFO)

# Telegram Bot Token
bot_token = "7807833216:AAHgNaQZEDWPG8iBcD9SnDZ7We8HLEZ_V7g"  # Replace with your actual bot token
bot = TeleBot(bot_token)

# API Token Bakong
api_token_bakong = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiNmFmM2FlMWU3Yzg4NDQ3OCJ9LCJpYXQiOjE3NDM1MTE4MjUsImV4cCI6MTc1MTI4NzgyNX0.ShQ-iQ96VKcqktZZnigUgqaDuooeuPGpnduzdtNxBGA"
khqr = KHQR(api_token_bakong)

user_last_interaction = {}
user_states = {}

def handle_rate_limit(user_id):
    if user_id in user_last_interaction and time.time() - user_last_interaction[user_id] < 2:
        return False
    user_last_interaction[user_id] = time.time()
    return True

# List of admin user IDs
ADMIN_IDS = [7507149806]

# Telegram group ID for deposit notifications
DEPOSIT_GROUP_ID = -1002721271109  # Replace with your group ID

# Item prices (key: item_id, value: price in $)
ITEM_PRICES = {
    "11": {"normal": 0.25, "reseller": 0.22},
    "22": {"normal": 0.50, "reseller": 0.44},
    "86": {"normal": 1.25, "reseller": 1.15},
    "172": {"normal": 2.45, "reseller": 2.25},
    "257": {"normal": 3.50, "reseller": 3.20},
    "343": {"normal": 4.63, "reseller": 3.33},
    "429": {"normal": 5.70, "reseller": 5.43},
    "514": {"normal": 6.80, "reseller": 6.42},
    "600": {"normal": 7.90, "reseller": 7.53},
    "706": {"normal": 9.10, "reseller": 8.61},
    "792": {"normal": 9.95, "reseller": 9.65},
    "878": {"normal": 12.10, "reseller": 10.38},
    "963": {"normal": 12.10, "reseller": 11.55},
    "1050": {"normal": 13.40, "reseller": 12.80},
    "1135": {"normal": 14.42, "reseller": 13.75},
    "1412": {"normal": 17.80, "reseller": 16.75},
    "1584": {"normal": 19.99, "reseller": 18.99},
    "1755": {"normal": 23.28, "reseller": 21.28},
    "1926": {"normal": 24.89, "reseller": 22.89},
    "2195": {"normal": 27.37, "reseller": 25.32},
    "2538": {"normal": 31.60, "reseller": 29.35},
    "2901": {"normal": 35.72, "reseller": 33.55},
    "4394": {"normal": 52.80, "reseller": 50.60},
    "5532": {"normal": 65.80, "reseller": 63.60},
    "6238": {"normal": 77.15, "reseller": 71.90},
    "6944": {"normal": 85.50, "reseller": 79.83},
    "8433": {"normal": 0.0, "reseller": 0.0},
    "9288": {"normal": 116.00, "reseller": 113.00},
    "Weekly": {"normal": 1.40, "reseller": 1.37},
    "2Weekly": {"normal": 2.80, "reseller": 2.70},
    "3Weekly": {"normal": 4.20, "reseller": 4.10},
    "4Weekly": {"normal": 5.60, "reseller": 5.40},
    "5Weekly": {"normal": 7.00, "reseller": 6.20},
    "Twilight": {"normal": 7.35, "reseller": 6.85},
    "50x2": {"normal": 0.90, "reseller": 0.80},
    "150x2": {"normal": 2.40, "reseller": 2.20},
    "250x2": {"normal": 3.85, "reseller": 3.55},
    "500x2": {"normal": 7.19, "reseller": 6.90},
}

ITEM_FF_PRICES = {
    "25": {"normal": 0.28, "reseller": 0.25},
    "100": {"normal": 0.90, "reseller": 0.85},
    "310": {"normal": 2.65, "reseller": 2.55},
    "520": {"normal": 4.25, "reseller": 4.10},
    "1060": {"normal": 8.65, "reseller": 8.25},
    "2180": {"normal": 16.50, "reseller": 16.15},
    "5600": {"normal": 43.00, "reseller": 41.00},
    "11500": {"normal": 85.00, "reseller": 82.00},
    "Weekly": {"normal": 0.0, "reseller": 1.45},
    "WeeklyLite": {"normal": 0.40, "reseller": 0.35},
    "Monthly": {"normal": 7.00, "reseller": 6.72},
    "Evo3D": {"normal": 0.60, "reseller": 0.56},
    "Evo7D": {"normal": 0.90, "reseller": 0.82},
    "Evo30D": {"normal": 2.45, "reseller": 2.33},
    "Levelpass": {"normal": 3.45, "reseller": 3.30},
}


# Database setup
def init_db():
    conn = sqlite3.connect('user_balances.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS balances (
            user_id INTEGER PRIMARY KEY,
            balance REAL NOT NULL DEFAULT 0,
            is_reseller INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# Function to get user balance
def get_user_balance(user_id):
    conn = sqlite3.connect('user_balances.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM balances WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

# Function to update user balance
def update_user_balance(user_id, amount):
    current_balance = get_user_balance(user_id)
    new_balance = current_balance + amount
    conn = sqlite3.connect('user_balances.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO balances (user_id, balance) VALUES (?, ?)', (user_id, new_balance))
    conn.commit()
    conn.close()

# Check if a user is a reseller
def is_reseller(user_id):
    try:
        conn = sqlite3.connect("user_balances.db")
        cursor = conn.cursor()
        cursor.execute("SELECT is_reseller FROM balances WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] == 1 if result else False
    except Exception as e:
        logging.error(f"Error checking reseller status for user {user_id}: {e}")
        return False       

# Set a user as a reseller
def add_reseller(user_id):
    conn = sqlite3.connect("user_balances.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO balances (user_id) VALUES (?)", (user_id,))
    cursor.execute("UPDATE balances SET is_reseller = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Unset a user as a reseller
def remove_reseller(user_id):
    conn = sqlite3.connect("user_balances.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO balances (user_id) VALUES (?)", (user_id,))
    cursor.execute("UPDATE balances SET is_reseller = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()        

# Command to set a user as a reseller
@bot.message_handler(commands=['addre'])
def add_reseller_handler(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to use this command.")
        return

    try:
        target_user_id = int(message.text.split()[1])
        add_reseller(target_user_id)
        bot.reply_to(message, f"✅ User {target_user_id} is now a reseller.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Usage: /addre <user_id>")

# Command to unset a user as a reseller
@bot.message_handler(commands=['delre'])
def remove_reseller_handler(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to use this command.")
        return

    try:
        target_user_id = int(message.text.split()[1])
        remove_reseller(target_user_id)
        bot.reply_to(message, f"✅ User {target_user_id} is no longer a reseller.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Usage: /delre <user_id>")

# Command to set item prices
def set_price_handler(message, item_prices):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to use this command.")
        return

    try:
        args = message.text.split()
        if len(args) != 4:
            bot.reply_to(message, "Usage: /set_price <item_id> <normal_price> <reseller_price>")
            return

        item_id = args[1]
        normal_price = float(args[2])
        reseller_price = float(args[3])

        if item_id in item_prices:
            item_prices[item_id]["normal"] = normal_price
            item_prices[item_id]["reseller"] = reseller_price
            bot.reply_to(message, f"✅ Prices updated for item {item_id}:\nNormal Price: ${normal_price}\nReseller Price: ${reseller_price}")
        else:
            bot.reply_to(message, f"Item ID {item_id} does not exist.")

    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid input. Please ensure you provide valid prices.")

@bot.message_handler(commands=['set_ml'])
def set_ml_handler(message):
    set_price_handler(message, ITEM_PRICES)

@bot.message_handler(commands=['set_ff'])
def set_ff_handler(message):
    set_price_handler(message, ITEM_FF_PRICES)

@bot.message_handler(commands=['addpdr'])
def add_product_handler(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to use this command.")
        return

    try:
        args = message.text.split()
        if len(args) != 5:
            bot.reply_to(message, "Usage: /addpdr <game> <product_id> <normal_price> <reseller_price>\nGames: ml, ff, mlph")
            return

        game = args[1].lower()
        product_id = args[2]
        normal_price = float(args[3])
        reseller_price = float(args[4])

        if normal_price <= 0 or reseller_price <= 0:
            bot.reply_to(message, "Prices must be greater than 0.")
            return

        # Select the appropriate price dictionary
        if game == "ml":
            price_dict = ITEM_PRICES
            game_name = "Mobile Legends"
        elif game == "ff":
            price_dict = ITEM_FF_PRICES
            game_name = "Free Fire"
        elif game == "mlph":
            price_dict = ITEM_MLPH_PRICES
            game_name = "Mobile Legends PH"
        else:
            bot.reply_to(message, "Invalid game. Use: ml (Mobile Legends), ff (Free Fire), or mlph (Mobile Legends PH)")
            return

        # Add the new product
        price_dict[product_id] = {
            "normal": normal_price,
            "reseller": reseller_price
        }

        success_message = (
            f"✅ **PRODUCT ADDED SUCCESSFULLY**\n\n"
            f"🎮 **Game:** {game_name}\n"
            f"🆔 **Product ID:** {product_id}\n"
            f"💰 **Normal Price:** ${normal_price:.2f}\n"
            f"🏪 **Reseller Price:** ${reseller_price:.2f}\n\n"
            f"Product is now available for purchase!"
        )

        bot.reply_to(message, success_message, parse_mode='Markdown')

    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid input. Please ensure you provide valid prices.\nUsage: /addpdr <game> <product_id> <normal_price> <reseller_price>")
    except Exception as e:
        bot.reply_to(message, f"❌ Error adding product: {str(e)}")

@bot.message_handler(commands=['addpack'])
def add_package_handler(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to use this command.")
        return

    try:
        # Get the command arguments
        command_text = message.text.replace('/addpack', '').strip()
        
        if not command_text:
            bot.reply_to(message, (
                "📦 **ADD PACKAGE**\n\n"
                "**Format:** `/addpack <game> <package_name> <items> <normal_price> <reseller_price>`\n\n"
                "**Examples:**\n"
                "`/addpack ml starter_pack 86+Weekly 2.50 2.30`\n"
                "`/addpack ff diamond_pack 310+WeeklyLite 3.00 2.80`\n"
                "`/addpack mlph premium_pack 172+2Weekly 4.80 4.50`\n\n"
                "**Games:** ml, ff, mlph\n"
                "**Items:** Use + to combine multiple items"
            ), parse_mode='Markdown')
            return

        args = command_text.split()
        if len(args) < 5:
            bot.reply_to(message, "Usage: /addpack <game> <package_name> <items> <normal_price> <reseller_price>")
            return

        game = args[0].lower()
        package_name = args[1]
        items = args[2]
        normal_price = float(args[3])
        reseller_price = float(args[4])

        if normal_price <= 0 or reseller_price <= 0:
            bot.reply_to(message, "Prices must be greater than 0.")
            return

        # Select the appropriate price dictionary
        if game == "ml":
            price_dict = ITEM_PRICES
            game_name = "Mobile Legends"
        elif game == "ff":
            price_dict = ITEM_FF_PRICES
            game_name = "Free Fire"
        elif game == "mlph":
            price_dict = ITEM_MLPH_PRICES
            game_name = "Mobile Legends PH"
        else:
            bot.reply_to(message, "Invalid game. Use: ml (Mobile Legends), ff (Free Fire), or mlph (Mobile Legends PH)")
            return

        # Validate that all items in the package exist
        item_list = items.split('+')
        for item in item_list:
            if item not in price_dict:
                bot.reply_to(message, f"❌ Item '{item}' does not exist in {game_name}. Please check your item list.")
                return

        # Add the new package
        price_dict[package_name] = {
            "normal": normal_price,
            "reseller": reseller_price,
            "package_items": items  # Store the items for reference
        }

        success_message = (
            f"📦 **PACKAGE ADDED SUCCESSFULLY**\n\n"
            f"🎮 **Game:** {game_name}\n"
            f"📋 **Package Name:** {package_name}\n"
            f"🎁 **Items Included:** {items.replace('+', ' + ')}\n"
            f"💰 **Normal Price:** ${normal_price:.2f}\n"
            f"🏪 **Reseller Price:** ${reseller_price:.2f}\n\n"
            f"Package is now available for purchase!"
        )

        bot.reply_to(message, success_message, parse_mode='Markdown')

    except (IndexError, ValueError) as e:
        bot.reply_to(message, f"Invalid input. Error: {str(e)}\nUsage: /addpack <game> <package_name> <items> <normal_price> <reseller_price>")
    except Exception as e:
        bot.reply_to(message, f"❌ Error adding package: {str(e)}")

@bot.message_handler(commands=['checkuser', 'viewuser'])
def checkuser_handler(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to use this command.")
        return

    try:
        target_user_id = int(message.text.split()[1])

        # Get user balance and reseller status
        conn = sqlite3.connect('user_balances.db')
        cursor = conn.cursor()
        cursor.execute('SELECT balance, is_reseller FROM balances WHERE user_id = ?', (target_user_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            balance, is_reseller_status = result
            reseller_text = "✅ Yes" if is_reseller_status == 1 else "❌ No"
            reseller_emoji = "🏪" if is_reseller_status == 1 else "👤"
        else:
            balance = 0.0
            reseller_text = "❌ No"
            reseller_emoji = "👤"

        # Try to get user info from Telegram
        try:
            user_info = bot.get_chat(target_user_id)
            username = f"@{user_info.username}" if user_info.username else "❌ No username"
            first_name = user_info.first_name or "Unknown"
            last_name = user_info.last_name or ""
            full_name = f"{first_name} {last_name}".strip()
            user_type = user_info.type
        except:
            username = "🔒 Private/Unknown"
            full_name = "🔒 Private/Unknown"
            user_type = "Unknown"

        # Get current time
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        user_details = (
            f"═══════════════════════\n"
            f"{reseller_emoji} **USER INFORMATION** {reseller_emoji}\n"
            f"═══════════════════════\n\n"
            f"🆔 **User ID:** `{target_user_id}`\n"
            f"📝 **Name:** {full_name}\n"
            f"🔗 **Username:** {username}\n"
            f"👥 **Account Type:** {user_type.title()}\n"
            f"💰 **Balance:** `${balance:.2f} USD`\n"
            f"🏪 **Reseller Status:** {reseller_text}\n"
            f"⏰ **Checked At:** {current_time}\n\n"
            f"═══════════════════════"
        )

        bot.reply_to(message, user_details, parse_mode='Markdown')

    except (IndexError, ValueError):
        bot.reply_to(message, "📋 **Usage:** `/checkuser <user_id>` or `/viewuser <user_id>`", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ **Error checking user:** {str(e)}", parse_mode='Markdown')

@bot.message_handler(commands=['allusers'])
def allusers_handler(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to use this command.")
        return

    conn = sqlite3.connect('user_balances.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, balance, is_reseller FROM balances ORDER BY balance DESC')
    results = cursor.fetchall()
    conn.close()

    if not results:
        bot.reply_to(message, "❌ No users found in database.")
        return

    current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    user_list = f"👥 **ALL USERS DATABASE** 👥\n"
    user_list += f"═══════════════════════\n"
    user_list += f"📊 **Total Users:** {len(results)}\n"
    user_list += f"⏰ **Generated:** {current_time}\n"
    user_list += f"═══════════════════════\n\n"

    total_balance = 0
    reseller_count = 0

    for user_id, balance, is_reseller_status in results:
        total_balance += balance
        if is_reseller_status == 1:
            reseller_count += 1

        reseller_badge = "🏪" if is_reseller_status == 1 else "👤"

        # Try to get username
        try:
            user_info = bot.get_chat(user_id)
            username = f"@{user_info.username}" if user_info.username else "No username"
        except:
            username = "Private/Unknown"

        user_list += f"{reseller_badge} **ID:** `{user_id}`\n"
        user_list += f"💰 **Balance:** `${balance:.2f}`\n"
        user_list += f"🔗 **Username:** {username}\n"
        user_list += f"─────────────────\n"

    user_list += f"\n📈 **STATISTICS**\n"
    user_list += f"💰 **Total Balance:** `${total_balance:.2f}`\n"
    user_list += f"🏪 **Resellers:** {reseller_count}\n"
    user_list += f"👤 **Normal Users:** {len(results) - reseller_count}\n"

    # Split message if too long
    if len(user_list) > 4096:
        # Send as file
        file_content = user_list.replace("**", "").replace("`", "").replace("*", "")
        file_path = f"all_users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(file_path, "w", encoding='utf-8') as file:
            file.write(file_content)

        with open(file_path, "rb") as file:
            bot.send_document(admin_id, file, caption="📊 **Complete Users Database**", parse_mode='Markdown')

        os.remove(file_path)
    else:
        bot.reply_to(message, user_list, parse_mode='Markdown')

@bot.message_handler(commands=['finduser'])
def finduser_handler(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to use this command.")
        return

    try:
        search_term = message.text.split()[1]

        conn = sqlite3.connect('user_balances.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, balance, is_reseller FROM balances')
        results = cursor.fetchall()
        conn.close()

        found_users = []

        for user_id, balance, is_reseller_status in results:
            try:
                user_info = bot.get_chat(user_id)
                username = user_info.username or ""
                first_name = user_info.first_name or ""
                last_name = user_info.last_name or ""

                # Search by user ID, username, or name
                if (str(user_id) == search_term or 
                    (username and search_term.lower() in username.lower()) or
                    (first_name and search_term.lower() in first_name.lower()) or
                    (last_name and search_term.lower() in last_name.lower())):

                    found_users.append({
                        'user_id': user_id,
                        'balance': balance,
                        'is_reseller': is_reseller_status,
                        'username': username,
                        'first_name': first_name,
                        'last_name': last_name
                    })
            except:
                # If can't get user info, still check user ID
                if str(user_id) == search_term:
                    found_users.append({
                        'user_id': user_id,
                        'balance': balance,
                        'is_reseller': is_reseller_status,
                        'username': 'Private/Unknown',
                        'first_name': 'Private/Unknown',
                        'last_name': ''
                    })

        if not found_users:
            bot.reply_to(message, f"❌ No users found matching: `{search_term}`", parse_mode='Markdown')
            return

        search_results = f"🔍 **SEARCH RESULTS** 🔍\n"
        search_results += f"═══════════════════════\n"
        search_results += f"📝 **Search Term:** `{search_term}`\n"
        search_results += f"📊 **Found:** {len(found_users)} user(s)\n"
        search_results += f"═══════════════════════\n\n"

        for user in found_users:
            reseller_badge = "🏪" if user['is_reseller'] == 1 else "👤"
            full_name = f"{user['first_name']} {user['last_name']}".strip()
            username_display = f"@{user['username']}" if user['username'] and user['username'] != 'Private/Unknown' else user['username']

            search_results += f"{reseller_badge} **User Found**\n"
            search_results += f"🆔 **ID:** `{user['user_id']}`\n"
            search_results += f"📝 **Name:** {full_name}\n"
            search_results += f"🔗 **Username:** {username_display}\n"
            search_results += f"💰 **Balance:** `${user['balance']:.2f}`\n"
            search_results += f"🏪 **Reseller:** {'✅ Yes' if user['is_reseller'] == 1 else '❌ No'}\n"
            search_results += f"─────────────────\n"

        bot.reply_to(message, search_results, parse_mode='Markdown')

    except (IndexError, ValueError):
        bot.reply_to(message, "📋 **Usage:** `/finduser <user_id or username or name>`", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ **Error searching users:** {str(e)}", parse_mode='Markdown')

@bot.message_handler(commands=['allbal'])
def allbal_handler(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to use this command.")
        return

    conn = sqlite3.connect('user_balances.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, balance FROM balances')
    results = cursor.fetchall()
    conn.close()

    file_content = "User ID, Balance\n"
    for user_id, balance in results:
        file_content += f"{user_id}, {balance:.2f}\n"

    file_path = "user_balances.txt"
    with open(file_path, "w") as file:
        file.write(file_content)

    with open(file_path, "rb") as file:
        bot.send_document(admin_id, file, caption="Love You")

    os.remove(file_path)

# Command to add balance to a user
@bot.message_handler(commands=['addb'])
def addb_handler(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to use this command.")
        return

    try:
        args = message.text.split()
        if len(args) != 3:
            bot.reply_to(message, "Usage: /addb <user_id> <amount>")
            return

        target_user_id = int(args[1])
        amount = float(args[2])

        if amount <= 0:
            bot.reply_to(message, "Amount must be greater than 0.")
            return

        update_user_balance(target_user_id, amount)
        bot.reply_to(message, f"✅ Added ${amount:.2f} to user {target_user_id}'s balance.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid input. Please ensure you provide a valid user ID and amount.")

# Initialize the database
init_db()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    nickname = message.from_user.first_name or "អ្នកប្រើប្រាស់"
    
    # Check if user is admin
    if user_id in ADMIN_IDS:
        admin_welcome_message = (
            f"🔐 **ADMIN PANEL** 🔐\n\n"
            f"Welcome back, {nickname}!\n"
            f"Admin ID: {user_id}\n\n"
            f"Use the buttons below to manage the bot:"
        )
        
        markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        admin_users = KeyboardButton('👥 User Management')
        admin_balance = KeyboardButton('💰 Balance Control')
        admin_reseller = KeyboardButton('🏪 Reseller Control')
        admin_prices = KeyboardButton('💵 Price Control')
        admin_stats = KeyboardButton('📊 Statistics')
        normal_mode = KeyboardButton('👤 Normal Mode')
        markup.add(admin_users, admin_balance, admin_reseller, admin_prices, admin_stats, normal_mode)
        
        try:
            with open("logo.jpg", "rb") as photo:
                bot.send_photo(message.chat.id, photo, caption=admin_welcome_message, reply_markup=markup, parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Failed to send logo image: {e}")
            bot.send_message(message.chat.id, admin_welcome_message, reply_markup=markup, parse_mode='Markdown')
    else:
        # Normal user welcome
        welcome_message = (
            f"✅ សូមស្វាគមន៍ {nickname} ដែលបានមកកាន់ bot របស់យើងខ្ញុំ 🙏✨\n\n"
            "👉 សុវត្ថិភាពជូនអតិថិជន\n"
            "👉 តម្លៃសមរម្យ\n"
            "👉 មិនមានការបែនអាខោន\n"
            "👉 ដាក់បានលឿនរហ័សទាន់ចិត្ដ\n\n"
            "➡️Channel: t.me/krisst0re\n"
            "➡️Owner: @Kris_st0re\n\n"
            "➡️ប្រតិបត្តិការ: t.me/vieworder\n\n"
        )

        markup = ReplyKeyboardMarkup(row_width=4, resize_keyboard=True)
        button1 = KeyboardButton('👤 គណនី')
        button2 = KeyboardButton('🎮 Game')
        button3 = KeyboardButton('💰 ដាក់ប្រាក់')
        button4 = KeyboardButton('♻️ របៀបទិញ')
        markup.add(button1, button2, button3, button4)

        try:
            with open("logo.jpg", "rb") as photo:
                bot.send_photo(message.chat.id, photo, caption=welcome_message, reply_markup=markup)
        except Exception as e:
            logging.error(f"Failed to send logo image: {e}")
            # Fallback to text message if image fails
            bot.send_message(message.chat.id, welcome_message, reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '👤 គណនី')
def handle_account(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    user_balance = get_user_balance(chat_id)
    bot.send_message(chat_id, f"Name: {username}\nID: {user_id}\nBalance: ${user_balance:.2f} USD")

@bot.message_handler(func=lambda message: message.text == '🎮 Game')
def handle_game(message):
    markup = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    button1 = KeyboardButton('Mobile Legends')
    button2 = KeyboardButton('Free Fire')
    button3 = KeyboardButton('Mobile PH')
    button_back = KeyboardButton('🔙 Back')  # Unified Back button
    markup.add(button1, button2, button3, button_back)
    bot.send_message(message.chat.id, "Select product category", reply_markup=markup)

# Admin button handlers
@bot.message_handler(func=lambda message: message.text == '👥 User Management')
def admin_user_management(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")
        return
    
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = KeyboardButton('🔍 Find User')
    btn2 = KeyboardButton('👁️ View User')
    btn3 = KeyboardButton('📋 All Users')
    btn4 = KeyboardButton('📊 Users Export')
    back_btn = KeyboardButton('🔙 Admin Menu')
    markup.add(btn1, btn2, btn3, btn4, back_btn)
    
    bot.send_message(message.chat.id, "👥 **USER MANAGEMENT**\nSelect an option:", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '💰 Balance Control')
def admin_balance_control(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")
        return
    
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = KeyboardButton('➕ Add Balance')
    btn2 = KeyboardButton('➖ Remove Balance')
    btn3 = KeyboardButton('💾 Export Balances')
    back_btn = KeyboardButton('🔙 Admin Menu')
    markup.add(btn1, btn2, btn3, back_btn)
    
    bot.send_message(message.chat.id, "💰 **BALANCE CONTROL**\nSelect an option:", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '🏪 Reseller Control')
def admin_reseller_control(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")
        return
    
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = KeyboardButton('➕ Add Reseller')
    btn2 = KeyboardButton('➖ Remove Reseller')
    btn3 = KeyboardButton('📋 List Resellers')
    back_btn = KeyboardButton('🔙 Admin Menu')
    markup.add(btn1, btn2, btn3, back_btn)
    
    bot.send_message(message.chat.id, "🏪 **RESELLER CONTROL**\nSelect an option:", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '💵 Price Control')
def admin_price_control(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")
        return
    
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = KeyboardButton('🎮 ML Prices')
    btn2 = KeyboardButton('🔥 FF Prices')
    btn3 = KeyboardButton('📱 MLPH Prices')
    btn4 = KeyboardButton('➕ Add Product')
    btn5 = KeyboardButton('📦 Add Package')
    back_btn = KeyboardButton('🔙 Admin Menu')
    markup.add(btn1, btn2, btn3, btn4, btn5, back_btn)
    
    bot.send_message(message.chat.id, "💵 **PRICE CONTROL**\nSelect game to manage prices:", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '📊 Statistics')
def admin_statistics(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")
        return
    
    try:
        conn = sqlite3.connect('user_balances.db')
        cursor = conn.cursor()
        
        # Get total users
        cursor.execute('SELECT COUNT(*) FROM balances')
        total_users = cursor.fetchone()[0]
        
        # Get total balance
        cursor.execute('SELECT SUM(balance) FROM balances')
        total_balance = cursor.fetchone()[0] or 0
        
        # Get reseller count
        cursor.execute('SELECT COUNT(*) FROM balances WHERE is_reseller = 1')
        reseller_count = cursor.fetchone()[0]
        
        # Get users with balance > 0
        cursor.execute('SELECT COUNT(*) FROM balances WHERE balance > 0')
        active_users = cursor.fetchone()[0]
        
        conn.close()
        
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        stats_message = (
            f"📊 **BOT STATISTICS** 📊\n"
            f"══════════════════════\n\n"
            f"👥 **Total Users:** {total_users}\n"
            f"💰 **Total Balance:** ${total_balance:.2f} USD\n"
            f"🏪 **Resellers:** {reseller_count}\n"
            f"👤 **Normal Users:** {total_users - reseller_count}\n"
            f"⚡ **Active Users:** {active_users}\n"
            f"💸 **Users with Balance:** {active_users}\n\n"
            f"⏰ **Generated:** {current_time}\n"
            f"══════════════════════"
        )
        
        markup = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        back_btn = KeyboardButton('🔙 Admin Menu')
        markup.add(back_btn)
        
        bot.send_message(message.chat.id, stats_message, reply_markup=markup, parse_mode='Markdown')
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error generating statistics: {str(e)}")

@bot.message_handler(func=lambda message: message.text == '👤 Normal Mode')
def admin_normal_mode(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")
        return
    
    # Send normal user interface
    nickname = message.from_user.first_name or "អ្នកប្រើប្រាស់"
    welcome_message = (
        f"✅ សូមស្វាគមន៍ {nickname} ដែលបានមកកាន់ bot របស់យើងខ្ញុំ 🙏✨\n\n"
        "👉 សុវត្ថិភាពជូនអតិថិជន\n"
        "👉 តម្លៃសមរម្យ\n"
        "👉 មិនមានការបែនអាខោន\n"
        "👉 ដាក់បានលឿនរហ័សទាន់ចិត្ដ\n\n"
        "➡️Channel: t.me/krisst0re\n"
        "➡️Owner: @Kris_st0re\n\n"
        "➡️ប្រតិបត្តិការ: t.me/vieworder\n\n"
        "🔐 Admin Mode Available"
    )

    markup = ReplyKeyboardMarkup(row_width=4, resize_keyboard=True)
    button1 = KeyboardButton('👤 គណនី')
    button2 = KeyboardButton('🎮 Game')
    button3 = KeyboardButton('💰 ដាក់ប្រាក់')
    button4 = KeyboardButton('♻️ របៀបទិញ')
    admin_btn = KeyboardButton('🔐 Admin Panel')
    markup.add(button1, button2, button3, button4, admin_btn)

    bot.send_message(message.chat.id, welcome_message, reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '🔐 Admin Panel')
def admin_panel_access(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")
        return
    send_welcome(message)

@bot.message_handler(func=lambda message: message.text == '🔙 Admin Menu')
def back_to_admin_menu(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")
        return
    send_welcome(message)

# Quick action handlers
@bot.message_handler(func=lambda message: message.text == '➕ Add Balance')
def quick_add_balance(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")
        return
    bot.send_message(message.chat.id, "💰 **ADD BALANCE**\n\nFormat: `/addb <user_id> <amount>`\nExample: `/addb 123456789 10.50`", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '🔍 Find User')
def quick_find_user(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")
        return
    bot.send_message(message.chat.id, "🔍 **FIND USER**\n\nFormat: `/finduser <search_term>`\nExample: `/finduser john123`", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '👁️ View User')
def quick_view_user(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")
        return
    bot.send_message(message.chat.id, "👁️ **VIEW USER**\n\nFormat: `/checkuser <user_id>`\nExample: `/checkuser 123456789`", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '📋 All Users')
def quick_all_users(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")
        return
    allusers_handler(message)

@bot.message_handler(func=lambda message: message.text == '➕ Add Reseller')
def quick_add_reseller(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")
        return
    bot.send_message(message.chat.id, "🏪 **ADD RESELLER**\n\nFormat: `/addre <user_id>`\nExample: `/addre 123456789`", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '➖ Remove Reseller')
def quick_remove_reseller(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")
        return
    bot.send_message(message.chat.id, "🏪 **REMOVE RESELLER**\n\nFormat: `/delre <user_id>`\nExample: `/delre 123456789`", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '➕ Add Product')
def quick_add_product(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")
        return
    
    instruction_message = (
        "➕ **ADD PRODUCT**\n\n"
        "**Format:** `/addpdr <game> <product_id> <normal_price> <reseller_price>`\n\n"
        "**Games:**\n"
        "• `ml` - Mobile Legends\n"
        "• `ff` - Free Fire\n"
        "• `mlph` - Mobile Legends PH\n\n"
        "**Example:**\n"
        "`/addpdr ml 1200 15.50 14.00`\n"
        "`/addpdr ff 2500 25.00 23.50`"
    )
    
    bot.send_message(message.chat.id, instruction_message, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '📦 Add Package')
def quick_add_package(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Unauthorized access.")
        return
    
    instruction_message = (
        "📦 **ADD PACKAGE**\n\n"
        "**Format:** `/addpack <game> <package_name> <items> <normal_price> <reseller_price>`\n\n"
        "**Games:**\n"
        "• `ml` - Mobile Legends\n"
        "• `ff` - Free Fire\n"
        "• `mlph` - Mobile Legends PH\n\n"
        "**Examples:**\n"
        "`/addpack ml starter_pack 86+Weekly 2.50 2.30`\n"
        "`/addpack ff diamond_pack 310+WeeklyLite 3.00 2.80`\n"
        "`/addpack mlph premium_pack 172+2Weekly 4.80 4.50`\n\n"
        "**Note:** Use + to combine multiple items in a package"
    )
    
    bot.send_message(message.chat.id, instruction_message, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '🔙 Back')
def handle_back(message):
    user_id = message.from_user.id
    if not handle_rate_limit(user_id):
        bot.send_message(message.chat.id, "Please wait a moment before trying again.")
        return
    if user_id in user_states:
        del user_states[user_id]  # Clear any deposit state
    send_welcome(message)

@bot.message_handler(func=lambda message: message.text == 'Mobile Legends')
def handle_game_choice(message):
    user_id = message.from_user.id
    if is_reseller(user_id):
        product_list = "\n".join([f"{item_id} - {data['reseller']:.2f}" for item_id, data in ITEM_PRICES.items()])
        bot.send_message(message.chat.id, f"""Products List Mobile Legends (Reseller)\n\n{product_list}\n\nExample format order:
 123456789 12345 Weekly
 userid serverid item""")
    else:
        product_list1 = "\n".join([f"{item_id} - ${data['normal']:.2f}" for item_id, data in ITEM_PRICES.items()])
        bot.send_message(message.chat.id, f"""Products List Mobile Legends\n\n{product_list1}\n\nExample format order:
 123456789 12345 Weekly
 userid serverid item""")

@bot.message_handler(func=lambda message: message.text == 'Free Fire')
def handle_free_fire(message):
    user_id = message.from_user.id
    if is_reseller(user_id):
        product_list2 = "\n".join([f"{item_id} - {data['reseller']:.2f}" for item_id, data in ITEM_FF_PRICES.items()])
        bot.send_message(message.chat.id, f"""Products List Free Fire (Reseller)\n\n{product_list2}\n\nExample format order:
 123456789 0 Weekly
 userid serverid item""")
    else:
        product_list3 = "\n".join([f"{item_id} - ${data['normal']:.2f}" for item_id, data in ITEM_FF_PRICES.items()])
        bot.send_message(message.chat.id, f"""Products List Free Fire\n\n{product_list3}\n\nExample format order:
 123456789 0 Weekly
 userid serverid item""")

@bot.message_handler(func=lambda message: message.text == "💰 ដាក់ប្រាក់")
def deposit_handler(message):
    user_id = message.chat.id
    bot.send_message(user_id, " សូមបញ្ចូលចំនួនប្រាក់ដែលអ្នកចង់បង់ ជាលុយ$ ex: 0.01$ ឬ 1$")
    bot.register_next_step_handler(message, get_amount)

def get_amount(message):
    user_id = message.chat.id
    amount_text = message.text.strip()

    try:
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError("Amount must be greater than 0.")

        qr_data = khqr.create_qr(
            bank_account='sihourhuy_phearum@wing',
            merchant_name='SOKLAT SAN',
            merchant_city='Phnom Penh',
            amount=amount,
            currency='USD',
            store_label='MShop',
            phone_number='855 097 slashing 8845445',
            bill_number='TRX019283775',
            terminal_label='Cashier-01',
            static=False
        )

        md5_item = khqr.generate_md5(qr_data)
        qr_image = qrcode.make(qr_data)
        qr_image_io = BytesIO()
        qr_image.save(qr_image_io, 'PNG')
        qr_image_io.seek(0)

        caption = (
            "Here is your payment 𝐐𝐑 code\n"
            "Note: Expires in 3 minutes."
        )

        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        check_button = KeyboardButton("✅ពិនិត្យការទូទាត់")
        back_button = KeyboardButton("🔙 Back")  # Unified Back button
        markup.add(check_button, back_button)

        sent_qr_message = bot.send_photo(user_id, qr_image_io, caption=caption)
        bot.send_message(
            user_id,
            "✅ សូមចុច 'ពិនិត្យការទូទាត់' ដើម្បីពិនិត្យការបង់ប្រាក់។\n⚠️ បញ្ជាក់សូមកុំផ្ញើ វិក័យប័ត្រ មកកាន់ខ្ញុំវិញ!",
            reply_markup=markup
        )

        bot.register_next_step_handler_by_chat_id(user_id, lambda m: check_payment(m, md5_item, sent_qr_message, amount))

    except ValueError:
        bot.send_message(user_id, "❌ចំនួនមិនត្រឹមត្រូវ សូមបញ្ចូលចំនួនត្រឹមត្រូវដែលធំជាង 0.01")
    except Exception as e:
        bot.send_message(user_id, f"Error generating QR Code: {str(e)}")

def check_payment_automated(user_id, md5_item, sent_qr_message, amount):
    try:
        result_transaction = khqr.check_payment(md5_item)

        if result_transaction == "PAID":
            update_user_balance(user_id, amount)

            current_time = datetime.now().strftime("%d/%m/%Y %H:%M")
            username = bot.get_chat(user_id).username or "Unknown"

            success_message = (
                "Automated Deposit System ⚙️\n\n"
                f"Currency : USD 💵\n\n"
                f"Balance Added :\n"
                f"${amount:.2f} ✅\n\n"
                f"Time Now :\n"
                f"{current_time} ⏰\n\n"
                f"Payment :\n"
                f"KHQR PAYMENT SCAN\n\n"
                f"Telegram : @{username}\n"
                f"Telegram ID : {user_id}"          
            )

            bot.send_message(user_id, success_message)
            bot.delete_message(user_id, sent_qr_message.message_id)
            
            # Send notification to group
            group_message = (
                "💰 DEPOSIT COMPLETED 💰\n\n"
                f"👤 User: @{username}\n"
                f"🆔 ID: {user_id}\n"
                f"💵 Amount: ${amount:.2f} USD\n"
                f"⏰ Time: {current_time}\n"
                f"🔄 Method: KHQR Auto Payment"
            )
            send_group_message(DEPOSIT_GROUP_ID, group_message)
            
            return True

        elif result_transaction == "UNPAID":
            return False

        else:
            bot.send_message(user_id, f"Unexpected response: {result_transaction}")
            return False

    except Exception as e:
        bot.send_message(user_id, f"Error checking payment: {str(e)}")
        return False

def check_payment(message, md5_item, sent_qr_message, amount):
    user_id = message.chat.id

    for _ in range(30):
        time.sleep(1)
        if check_payment_automated(user_id, md5_item, sent_qr_message, amount):
            break
    else:
        bot.send_message(user_id, "❌ ការទូទាត់មិនសម្រេច។ សូមព្យាយាមម្តងទៀត។")

@bot.message_handler(func=lambda message: message.text.replace('.', '', 1).isdigit())
def amount_handler(message):
    amount = message.text
    user_id = message.from_user.id
    username = message.from_user.username or "អ្នកប្រើប្រាស់"

    user_states[user_id] = {"amount": amount}

    with open("qr.jpg", "rb") as photo:
        bot.send_photo(message.chat.id, photo, caption=f"⏳ ផុតកំណត់ក្នុងរយៈពេល 3 នាទី!\n\n📩 ផ្ញើវិក័យប័ត្រមកកាន់ខ្ញុំ")

    if user_id in user_states:
        user_states[user_id]["photo_id"] = message.photo[-1].file_id if message.photo else None
        bot.send_message(message.chat.id, "✅ រូបភាពត្រូវបានទទួល។ សូមចុចប៊ូតុង '✔️ យល់ព្រម' ដើម្បីបញ្ជូនទិន្នន័យទៅ admin។")
    else:
        bot.send_message(message.chat.id, "❌ មិនមានទិន្នន័យដាក់ប្រាក់។ សូមព្យាយាមម្តងទៀត។")

@bot.message_handler(func=lambda message: message.text == "✔️ យល់ព្រម")
def confirm_handler(message):
    user_id = message.from_user.id
    username = message.from_user.username or "អ្នកប្រើប្រាស់"

    if user_id in user_states and "amount" in user_states[user_id] and "photo_id" in user_states[user_id]:
        amount = user_states[user_id]["amount"]
        photo_id = user_states[user_id]["photo_id"]

        markup = InlineKeyboardMarkup()
        wrong_button = InlineKeyboardButton("❌ ខុស", callback_data=f"wrong_{user_id}_{amount}")
        correct_button = InlineKeyboardButton("✔️ ត្រូវ", callback_data=f"correct_{user_id}_{amount}")
        markup.add(wrong_button, correct_button)

        for admin_id in ADMIN_IDS:
            bot.send_photo(admin_id, photo_id, caption=f"📩 ការដាក់ប្រាក់ថ្មី\n\n👤 អ្នកប្រើប្រាស់: @{username}\n🆔 User ID: {user_id}\n💰 ចំនួនទឹកប្រាក់: {amount}$", reply_markup=markup)

        send_welcome(message)
        del user_states[user_id]
    else:
        bot.send_message(message.chat.id, "❌ មិនមានទិន្នន័យដាក់ប្រាក់ឬរូបភាព។ សូមព្យាយាមម្តងទៀត។")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data.split("_")
    action = data[0]
    target_user_id = int(data[1])
    amount = float(data[2])

    if action == "wrong":
        bot.answer_callback_query(call.id, "❌ ការដាក់ប្រាក់នេះខុស។")
        bot.send_message(target_user_id, f"❌ ការដាក់ប្រាក់ទទួលបានបរាជ័យ។")

    elif action == "correct":
        bot.answer_callback_query(call.id, "✅ ការដាក់ប្រាក់នេះត្រឹមត្រូវ។")
        update_user_balance(target_user_id, amount)
        bot.send_message(target_user_id, f"🎉🎊 ការដាក់ប្រាក់ទទួលបានជោគជ័យ: ${amount:.2f}។")
        
        # Get username for group notification
        try:
            username = bot.get_chat(target_user_id).username or "Unknown"
        except:
            username = "Unknown"
            
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        # Send notification to group
        group_message = (
            "💰 DEPOSIT APPROVED 💰\n\n"
            f"👤 User: @{username}\n"
            f"🆔 ID: {target_user_id}\n"
            f"💵 Amount: ${amount:.2f} USD\n"
            f"⏰ Time: {current_time}\n"
            f"🔄 Method: Manual Verification"
        )
        send_group_message(DEPOSIT_GROUP_ID, group_message)

    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    user_id = message.from_user.id
    username = message.from_user.username or "អ្នកប្រើប្រាស់"

    if user_id in user_states:
        amount = user_states[user_id]["amount"]
        photo_id = message.photo[-1].file_id

        for admin_id in ADMIN_IDS:
            bot.send_photo(admin_id, photo_id, caption=f"📩 ការដាក់ប្រាក់ថ្មី\n\n👤 អ្នកប្រើប្រាស់: @{username}\n🆔 User ID: {user_id}\n💰 ចំនួនទឹកប្រាក់: {amount}$")

        send_welcome(message)
    else:
        bot.send_message(message.chat.id, "❌ មិនមានទិន្នន័យដាក់ប្រាក់។ សូមព្យាយាមម្តងទៀត។")

@bot.message_handler(func=lambda message: len(message.text.split()) == 3)
def buy_item_handler(message):
    try:
        user_id = message.from_user.id
        args = message.text.split()

        try:
            server_id = int(args[0])
            zone_id = int(args[1])
            item_id = args[2]
        except ValueError:
            bot.send_message(message.chat.id, "Invalid server ID or zone ID. Please enter valid numbers.")
            return

        price_list = ITEM_FF_PRICES if zone_id == 0 else ITEM_PRICES

        if item_id not in price_list:
            bot.send_message(message.chat.id, f"Item ID {item_id} does not exist.")
            return

        price = price_list[item_id]["reseller"] if is_reseller(user_id) else price_list[item_id]["normal"]

        balance = get_user_balance(user_id)
        if balance < price:
            bot.send_message(message.chat.id, f"Insufficient balance. The item costs ${price:.2f}. Please add funds.")
            return

        nickname = "Unknown"
        if zone_id != 0:
            api_url = f"https://api.isan.eu.org/nickname/ml?id={server_id}&zone={zone_id}"
            try:
                response = requests.get(api_url)
                response.raise_for_status()
                data = response.json()
                if data.get("success"):
                    nickname = data.get("name", "unfinded")
                else:
                    bot.reply_to(message, "Wrong ID")
                    return
            except requests.RequestException as e:
                bot.send_message(message.chat.id, "Error validating ID MLBB. Please try again later.")
                logging.error(f"API request failed: {e}")
                return

        update_user_balance(user_id, -price)

        bot.send_message(message.chat.id, f"New Order Successfully ❇️\nPlayer ID: {server_id}\nServer ID: {zone_id}\nNickname: {nickname}\nProduct: {item_id}\nStatus: Success ✅")

        group_ff_id = -1002840078804
        group_mlbb_id = -1002840078804
        group_operations_id = -1002721271109

        purchase_details = f"{server_id} {zone_id} {item_id}"
        if zone_id == 0:
            send_group_message(group_ff_id, purchase_details)
        else:
            send_group_message(group_mlbb_id, purchase_details)

        buyer_info = f"New Order Successfully ❇️\nGame: {'Free Fire' if zone_id == 0 else 'Mobile Legends'}\nPlayer ID: {server_id}\nServer ID: {zone_id}\nNickname: {nickname}\nProduct: {item_id}\nStatus: Success ✅"
        send_group_message(group_operations_id, buyer_info)

    except Exception as e:
        bot.send_message(message.chat.id, f"An error occurred: {e}")
        logging.error(f"Error in buy_item_handler: {e}")

def send_group_message(group_id, message):
    try:
        bot.send_message(group_id, message)
    except Exception as e:
        logging.error(f"Failed to send message to group {group_id}: {e}")

if __name__ == "__main__":
    init_db()
    logging.info("Bot is running...")
    bot.infinity_polling()