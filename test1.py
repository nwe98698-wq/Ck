import os
import logging
import hashlib
import time
import json
import requests
import random
import sqlite3
import asyncio
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext, CallbackQueryHandler

# Bot configuration
BOT_TOKEN = "8465631068:AAEogW6aPTamdmlsJ_0mvrHiHZ-NEQwAHxk"

# Channel configuration - Auto Signal ချမယ့် Channel
SIGNAL_CHANNEL_USERNAME = "@Sakuna_taitan_tool"  # Your signal channel

# Channel configuration - User ဝင်ရမယ့် Channel
CHANNEL_USERNAME = "@Vipsafesingalchannel298"
CHANNEL_LINK = "https://t.me/Vipsafesingalchannel298"

# Multiple API endpoints
API_ENDPOINTS = {
    "ck": "https://ckygjf6r.com/api/webapi/",
    "777": "https://api.bigwinqaz.com/api/webapi/",
    "6": "https://6lotteryapi.com/api/webapi/"
}

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database setup
DB_NAME = "auto_bot.db"

# Auto Signal Configuration
AUTO_SIGNAL_ENABLED = True
SIGNAL_INTERVAL = 60  # seconds between signals

# Bet Sequence for Loss (1,2,3,4,5,6,7,9,10,11,12)
BET_SEQUENCE = [10,30,70,160,320,760,1600,3200,7600,16000,32000,76000]  # Steps for loss progression

# Global storage for tracking current issues
current_issues = {
    'ck': {'issue': '', 'bet_type': '', 'amount': 0, 'step': 0},
    '777': {'issue': '', 'bet_type': '', 'amount': 0, 'step': 0},
    '6': {'issue': '', 'bet_type': '', 'amount': 0, 'step': 0}
}

def migrate_database():
    """Migrate database to add missing columns"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(user_settings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'language' not in columns:
            print("🔧 Migrating database: Adding language column...")
            cursor.execute('ALTER TABLE user_settings ADD COLUMN language TEXT DEFAULT "english"')
            conn.commit()
            print("✅ Database migration completed: language column added")
        
        conn.close()
    except Exception as e:
        print(f"❌ Database migration error: {e}")

def init_database():
    """Initialize SQLite database"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                phone TEXT,
                password TEXT,
                platform TEXT DEFAULT 'ck',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create user_settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                bet_amount INTEGER DEFAULT 100,
                auto_login BOOLEAN DEFAULT 1,
                platform TEXT DEFAULT 'ck',
                language TEXT DEFAULT 'english',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create signal_history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                issue TEXT,
                bet_type TEXT,
                amount INTEGER,
                result TEXT,
                profit_loss INTEGER,
                current_step INTEGER,
                signal_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create bet_sequence table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bet_sequence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                current_step INTEGER DEFAULT 0,
                last_result TEXT,
                total_profit INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

def save_signal_history(platform, issue, bet_type, amount, result, profit_loss, current_step, signal_text):
    """Save signal to history"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO signal_history (platform, issue, bet_type, amount, result, profit_loss, current_step, signal_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (platform, issue, bet_type, amount, result, profit_loss, current_step, signal_text))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving signal history: {e}")
        return False

def get_platform_sequence(platform):
    """Get current sequence for platform"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT current_step, last_result, total_profit FROM bet_sequence 
            WHERE platform = ? ORDER BY created_at DESC LIMIT 1
        ''', (platform,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'current_step': result[0],
                'last_result': result[1],
                'total_profit': result[2]
            }
        return {'current_step': 0, 'last_result': None, 'total_profit': 0}
    except Exception as e:
        logger.error(f"Error getting platform sequence: {e}")
        return {'current_step': 0, 'last_result': None, 'total_profit': 0}

def update_platform_sequence(platform, current_step, last_result, total_profit):
    """Update platform sequence"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bet_sequence (platform, current_step, last_result, total_profit)
            VALUES (?, ?, ?, ?)
        ''', (platform, current_step, last_result, total_profit))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error updating platform sequence: {e}")
        return False

def get_recent_signals(platform, limit=10):
    """Get recent signals for platform"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT platform, issue, bet_type, amount, result, profit_loss, current_step, signal_text, created_at 
            FROM signal_history 
            WHERE platform = ?
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (platform, limit))
        
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Error getting signal history: {e}")
        return []

class LotteryBot:
    def __init__(self, platform='ck'):
        self.platform = platform
        self.base_url = API_ENDPOINTS.get(platform, API_ENDPOINTS['ck'])
        
        # Set platform-specific headers
        if platform == 'ck':
            origin = "https://www.cklottery.cc"
            referer = "https://www.cklottery.cc/"
        elif platform == '777':
            origin = "https://www.bigwinqaz.com"
            referer = "https://www.bigwinqaz.com/"
        elif platform == '6':
            origin = "https://6lottery.com"
            referer = "https://6lottery.com/"
        else:
            origin = "https://www.cklottery.cc"
            referer = "https://www.cklottery.cc/"
            
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": origin,
            "Referer": referer,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    def sign_md5(self, data_dict):
        """Generate MD5 signature for API requests"""
        sign_data = data_dict.copy()
        if 'signature' in sign_data:
            del sign_data['signature']
        if 'timestamp' in sign_data:
            del sign_data['timestamp']
        
        sorted_data = dict(sorted(sign_data.items()))
        hash_string = json.dumps(sorted_data, separators=(',', ':')).replace(' ', '')
        
        md5_hash = hashlib.md5(hash_string.encode('utf-8')).hexdigest()
        return md5_hash
    
    def random_key(self):
        """Generate random key for API"""
        xxxx = "xxxxxxxxxxxx4xxxyxxxxxxxxxxxxxxx"
        result = ""
        
        for char in xxxx:
            if char == 'x':
                result += random.choice('0123456789abcdef')
            elif char == 'y':
                result += random.choice('89a')
            else:
                result += char
        return result
    
    async def get_current_issue(self):
        """Get current game issue"""
        try:
            body = {
                "typeId": 1,
                "language": 0,
                "random": "b05034ba4a2642009350ee863f29e2e9",
                "timestamp": int(time.time())
            }
            body["signature"] = self.sign_md5(body).upper()
            
            response = requests.post(
                f"{self.base_url}GetGameIssue",
                headers=self.headers,
                json=body,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('msgCode') == 0:
                    return result.get('data', {}).get('issueNumber', '')
            return ""
        except Exception as e:
            logger.error(f"Get issue error for {self.platform}: {e}")
            return ""
    
    async def get_recent_results(self, count=5):
        """Get recent game results"""
        try:
            body = {
                "pageNo": 1,
                "pageSize": count,
                "language": 0,
                "typeId": 1,
                "random": "6DEB0766860C42151A193692ED16D65A",
                "timestamp": int(time.time())
            }
            body["signature"] = self.sign_md5(body).upper()
            
            response = requests.post(
                f"{self.base_url}GetNoaverageEmerdList",
                headers=self.headers,
                json=body,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('msgCode') == 0:
                    data_str = response.text
                    start_idx = data_str.find('[')
                    end_idx = data_str.find(']') + 1
                    if start_idx != -1 and end_idx != -1:
                        results_json = data_str[start_idx:end_idx]
                        results = json.loads(results_json)
                        return results
            return []
        except Exception as e:
            logger.error(f"Get results error for {self.platform}: {e}")
            return []

def analyze_results(results):
    """Analyze recent results and determine next bet"""
    if not results or len(results) < 2:
        return {'bet_type': random.choice(['BIG', 'SMALL']), 'confidence': 'LOW'}
    
    last_result = results[0]
    second_last = results[1]
    
    number = str(last_result.get('number', ''))
    prev_number = str(second_last.get('number', ''))
    
    # Simple pattern analysis
    if number in ['0','1','2','3','4']:
        last_was_small = True
        last_was_big = False
    else:
        last_was_small = False
        last_was_big = True
    
    if prev_number in ['0','1','2','3','4']:
        prev_was_small = True
        prev_was_big = False
    else:
        prev_was_small = False
        prev_was_big = True
    
    # Strategy: Follow the trend if same result twice, otherwise switch
    if last_was_big and prev_was_big:
        return {'bet_type': 'BIG', 'confidence': 'HIGH'}
    elif last_was_small and prev_was_small:
        return {'bet_type': 'SMALL', 'confidence': 'HIGH'}
    elif last_was_big and prev_was_small:
        return {'bet_type': 'SMALL', 'confidence': 'MEDIUM'}
    else:  # last_was_small and prev_was_big
        return {'bet_type': 'BIG', 'confidence': 'MEDIUM'}

def calculate_profit_loss(bet_type, result_number, bet_amount):
    """Calculate profit/loss for a bet"""
    result_number = str(result_number)
    
    if bet_type == 'BIG':
        if result_number in ['5','6','7','8','9']:
            # Win - 96% payout
            profit = int(bet_amount * 0.96)
            return 'WIN', profit
        else:
            # Loss
            return 'LOSS', -bet_amount
    elif bet_type == 'SMALL':
        if result_number in ['0','1','2','3','4']:
            # Win - 96% payout
            profit = int(bet_amount * 0.96)
            return 'WIN', profit
        else:
            # Loss
            return 'LOSS', -bet_amount
    else:
        return 'UNKNOWN', 0

def get_next_bet_amount(current_step):
    """Get bet amount based on current step in sequence"""
    if current_step < len(BET_SEQUENCE):
        return BET_SEQUENCE[current_step] * 100  # Convert to actual amount (e.g., 1 = 100, 2 = 200, etc.)
    else:
        return BET_SEQUENCE[-1] * 100  # Use last amount if sequence exceeded

def generate_signal_text(platform, issue, bet_type, amount, current_step, total_profit, confidence):
    """Generate signal message for channel"""
    platform_names = {
        'ck': 'CK LOTTERY',
        '777': '777 BIG WIN', 
        '6': '6 LOTTERY'
    }
    
    platform_name = platform_names.get(platform, 'CK LOTTERY')
    step_display = current_step + 1
    
    signal_text = f"🎮 **{platform_name}**\n🎰 Issue: {issue}\n🎲 Bet: {bet_type}\n💰 Amount: {amount:,} K\n"
    
    return signal_text

def generate_result_text(platform, issue, bet_type, amount, result, profit_loss, current_step, total_profit, result_number):
    """Generate result message"""
    platform_names = {
        'ck': 'CK LOTTERY',
        '777': '777 BIG WIN', 
        '6': '6 LOTTERY'
    }
    
    platform_name = platform_names.get(platform, 'CK LOTTERY')
    step_display = current_step + 1
    
    if result == 'WIN':
        emoji = "🟢"
        result_text = "WIN"
        details = f"💰 Win Amount: {profit_loss:,} K"
        next_action = "🔄 **Next Bet:** Back to Step 1"
    else:
        emoji = "🔴"
        result_text = "LOSS"
        details = f"💸 Loss Amount: {amount:,} K"
        next_step = current_step + 1
        next_amount = get_next_bet_amount(next_step)
        next_action = f"📈 **Next Bet:** Step {next_step + 1} ({next_amount:,} K)"
    
    result_text = f"""

{emoji} **BET RESULT - {platform_name}**

Total Profit: {total_profit:,} K 🏆🏆🏆
    """
    
    return result_text

async def send_signal_for_platform(context: ContextTypes.DEFAULT_TYPE, platform: str):
    """Send signal and check result for one platform"""
    try:
        bot = LotteryBot(platform)
        
        # Get current issue and recent results
        current_issue = await bot.get_current_issue()
        recent_results = await bot.get_recent_results(3)
        
        if not current_issue:
            logger.error(f"No current issue for {platform}")
            return False
        
        if not recent_results:
            logger.error(f"No recent results for {platform}")
            return False
        
        # Get current sequence for platform
        sequence_data = get_platform_sequence(platform)
        current_step = sequence_data['current_step']
        total_profit = sequence_data['total_profit']
        
        # Analyze results to determine next bet
        analysis = analyze_results(recent_results)
        bet_type = analysis['bet_type']
        confidence = analysis['confidence']
        
        # Get bet amount based on current step
        bet_amount = get_next_bet_amount(current_step)
        
        # Store current issue data
        current_issues[platform] = {
            'issue': current_issue,
            'bet_type': bet_type,
            'amount': bet_amount,
            'step': current_step
        }
        
        # Generate and send signal
        signal_text = generate_signal_text(platform, current_issue, bet_type, bet_amount, current_step, total_profit, confidence)
        
        # Send signal to channel
        await context.bot.send_message(
            chat_id=SIGNAL_CHANNEL_USERNAME,
            text=signal_text,
            parse_mode='Markdown'
        )
        
        logger.info(f"Signal sent for {platform}: {bet_type} {bet_amount}K (Step {current_step + 1})")
        return True
        
    except Exception as e:
        logger.error(f"Error sending signal for {platform}: {e}")
        return False

async def check_result_for_platform(context: ContextTypes.DEFAULT_TYPE, platform: str):
    """Check result for previous signal of a platform"""
    try:
        bot = LotteryBot(platform)
        
        # Get stored issue data
        issue_data = current_issues[platform]
        if not issue_data['issue']:
            return False
        
        current_issue = issue_data['issue']
        bet_type = issue_data['bet_type']
        bet_amount = issue_data['amount']
        current_step = issue_data['step']
        
        # Get current sequence for platform
        sequence_data = get_platform_sequence(platform)
        total_profit = sequence_data['total_profit']
        
        # Wait a bit for result to be available
        await asyncio.sleep(10)
        
        # Get the result for the issue we bet on
        new_results = await bot.get_recent_results(2)
        if new_results and len(new_results) > 0:
            latest_result = new_results[0]
            result_issue = latest_result.get('issueNumber', '')
            result_number = str(latest_result.get('number', ''))
            
            # Check if this is the result for our bet issue
            if result_issue == current_issue:
                # Calculate result
                result, profit_loss = calculate_profit_loss(bet_type, result_number, bet_amount)
                
                # Update sequence and total profit
                if result == 'WIN':
                    new_step = 0  # Reset to step 1
                    new_total_profit = total_profit + profit_loss
                else:  # LOSS
                    new_step = current_step + 1
                    if new_step >= len(BET_SEQUENCE):
                        new_step = len(BET_SEQUENCE) - 1  # Stay at last step
                    new_total_profit = total_profit + profit_loss  # profit_loss is negative for loss
                
                # Update platform sequence
                update_platform_sequence(platform, new_step, result, new_total_profit)
                
                # Generate result message
                result_text = generate_result_text(
                    platform, current_issue, bet_type, bet_amount, result, 
                    profit_loss, current_step, new_total_profit, result_number
                )
                
                # Send result to channel
                await context.bot.send_message(
                    chat_id=SIGNAL_CHANNEL_USERNAME,
                    text=result_text,
                    parse_mode='Markdown'
                )
                
                # Save to history
                save_signal_history(
                    platform, current_issue, bet_type, bet_amount, result, 
                    profit_loss, current_step, result_text
                )
                
                logger.info(f"Result for {platform}: {result} (Profit: {profit_loss}, New Step: {new_step})")
                
                # Clear current issue after processing result
                current_issues[platform] = {'issue': '', 'bet_type': '', 'amount': 0, 'step': 0}
                return True
            else:
                logger.warning(f"Issue mismatch for {platform}: expected {current_issue}, got {result_issue}")
                return False
        else:
            logger.error(f"No results found for issue {current_issue} on {platform}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking result for {platform}: {e}")
        return False

async def process_platform_cycle(context: ContextTypes.DEFAULT_TYPE, platform: str):
    """Complete cycle for one platform: signal -> wait -> result -> next signal"""
    try:
        # Send signal for current issue
        signal_sent = await send_signal_for_platform(context, platform)
        if not signal_sent:
            return False
        
        # Wait for result (adjust timing based on game schedule)
        await asyncio.sleep(30)  # Wait 65 seconds for next result
        
        # Check result for the signal we just sent
        result_checked = await check_result_for_platform(context, platform)
        
        # Small delay before next signal
        await asyncio.sleep(5)
        
        return result_checked
        
    except Exception as e:
        logger.error(f"Error in platform cycle for {platform}: {e}")
        return False

async def start_auto_signal(context: ContextTypes.DEFAULT_TYPE):
    """Start auto signal service for all platforms"""
    try:
        logger.info("Auto signal service started")
        
        # Initial delay to let bot fully start
        await asyncio.sleep(10)
        
        while True:
            try:
                start_time = datetime.now()
                logger.info(f"Starting new signal cycle at {start_time.strftime('%H:%M:%S')}")
                
                # Process all platforms in parallel
                platforms = ['ck', '777', '6']
                
                # Send signals for all platforms first
                signal_tasks = []
                for platform in platforms:
                    task = asyncio.create_task(send_signal_for_platform(context, platform))
                    signal_tasks.append(task)
                    # Small delay between signal sends to avoid rate limiting
                    await asyncio.sleep(2)
                
                # Wait for all signals to be sent
                await asyncio.gather(*signal_tasks, return_exceptions=True)
                
                logger.info("All signals sent, waiting for results...")
                
                # Wait for results (adjust based on game timing)
                await asyncio.sleep(30)
                
                # Check results for all platforms
                result_tasks = []
                for platform in platforms:
                    task = asyncio.create_task(check_result_for_platform(context, platform))
                    result_tasks.append(task)
                    await asyncio.sleep(2)
                
                # Wait for all results to be processed
                await asyncio.gather(*result_tasks, return_exceptions=True)
                
                logger.info("All results processed")
                
                # Calculate time until next cycle
                cycle_duration = (datetime.now() - start_time).total_seconds()
                wait_time = max(0, SIGNAL_INTERVAL - cycle_duration)
                
                if wait_time > 0:
                    logger.info(f"Waiting {wait_time:.1f} seconds for next cycle")
                    await asyncio.sleep(wait_time)
                else:
                    logger.info("Starting next cycle immediately")
                    
            except Exception as e:
                logger.error(f"Error in signal cycle: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds before retrying
                
    except Exception as e:
        logger.error(f"Auto signal service stopped: {e}")

def get_join_channel_keyboard():
    """Get keyboard for joining channel"""
    keyboard = [
        [InlineKeyboardButton("📢 Join Our Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I've Joined", callback_data="check_join")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def check_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Check if user is a member of the channel"""
    try:
        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        
        if chat_member.status in ['member', 'administrator', 'creator']:
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        return True

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    if query.data == "check_join":
        has_joined = await check_channel_membership(update, context, query.from_user.id)
        
        if has_joined:
            await query.edit_message_text(
                "✅ Thank you for joining our channel! You can now use the bot.\n\n"
                "Press /start to begin.",
                reply_markup=None
            )
        else:
            await query.edit_message_text(
                "❌ You haven't joined our channel yet. Please join the channel first to use the bot.",
                reply_markup=get_join_channel_keyboard()
            )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    user_id = str(user.id)
    
    has_joined = await check_channel_membership(update, context, user.id)
    
    if not has_joined:
        welcome_text = f"""
🎰 **Welcome to Auto Signal Bot** 🎯

Dear {user.first_name},

To use this bot, you need to join our official channel first for VIP signals.

**Why join our channel?**
• 📊 Get real-time betting signals
• 💡 Professional analysis  
• 🔔 Instant result updates
• 🎯 High accuracy predictions

Please join our channel below and then click **✅ I've Joined** to verify.
        """
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_join_channel_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    welcome_text = f"""
🎰 **Auto Signal Bot** 🎯

Welcome {user.first_name}!

🤖 **Automatic Signal Features:**
• 📊 CK LOTTERY Signals
• 🎯 777 BIG WIN Signals  
• 🔥 6 LOTTERY Signals
• ⏰ 1-Minute Interval Updates
• 📈 Real Win/Loss Results
• 🔢 Smart Bet Sequence (1,2,3,4,5,6,7,9,10,11,12)
• 🎲 BIG/SMALL Only Strategy

📢 **Channel:** @Vipsafesingalchannel298

🚀 **Current Mode:** All 3 platforms signal every minute with instant results!
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    # Start auto signal service if not already running
    if 'auto_signal_started' not in context.bot_data:
        context.bot_data['auto_signal_started'] = True
        asyncio.create_task(start_auto_signal(context))
        logger.info("Auto signal service started")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check current status for all platforms"""
    try:
        status_text = "📊 **Current Bot Status**\n\n"
        
        platforms = ['ck', '777', '6']
        platform_names = {
            'ck': 'CK LOTTERY',
            '777': '777 BIG WIN', 
            '6': '6 LOTTERY'
        }
        
        for platform in platforms:
            sequence_data = get_platform_sequence(platform)
            current_step = sequence_data['current_step']
            total_profit = sequence_data['total_profit']
            last_result = sequence_data['last_result'] or 'N/A'
            
            current_issue = current_issues[platform]['issue']
            current_bet = current_issues[platform]['bet_type']
            
            status_text += f"**{platform_names[platform]}**\n"
            status_text += f"• Current Step: {current_step + 1}\n"
            status_text += f"• Last Result: {last_result}\n"
            status_text += f"• Total Profit: {total_profit:,} K\n"
            if current_issue:
                status_text += f"• Current Issue: {current_issue}\n"
                status_text += f"• Current Bet: {current_bet}\n"
            status_text += "\n"
        
        status_text += f"⏰ **Signal Interval:** {SIGNAL_INTERVAL} seconds\n"
        status_text += f"🔢 **Bet Sequence:** {', '.join(map(str, BET_SEQUENCE))}\n"
        status_text += f"🕒 **Last Update:** {datetime.now().strftime('%H:%M:%S')}"
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await update.message.reply_text("❌ Error getting status.")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset all platforms to step 1"""
    try:
        platforms = ['ck', '777', '6']
        
        for platform in platforms:
            update_platform_sequence(platform, 0, 'RESET', 0)
            current_issues[platform] = {'issue': '', 'bet_type': '', 'amount': 0, 'step': 0}
        
        await update.message.reply_text(
            "✅ **All platforms reset to Step 1!**\n\n"
            "All sequences have been reset and total profits cleared.",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in reset command: {e}")
        await update.message.reply_text("❌ Error resetting platforms.")

async def force_signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force send signals for all platforms immediately"""
    try:
        await update.message.reply_text("🔄 Forcing immediate signals for all platforms...")
        
        platforms = ['ck', '777', '6']
        for platform in platforms:
            await send_signal_for_platform(context, platform)
            await asyncio.sleep(2)
        
        await update.message.reply_text("✅ All signals sent successfully!")
        
    except Exception as e:
        logger.error(f"Error in force signal command: {e}")
        await update.message.reply_text("❌ Error sending signals.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    if text == "📊 Status":
        await status_command(update, context)
    elif text == "🔄 Reset":
        await reset_command(update, context)
    elif text == "🚀 Force Signal":
        await force_signal_command(update, context)
    else:
        await update.message.reply_text(
            "Please use /start to begin or check the status with 📊 Status",
            parse_mode='Markdown'
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    if update and update.message:
        await update.message.reply_text(
            "❌ An error occurred. Please try again later.",
            parse_mode='Markdown'
        )

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Please set your BOT_TOKEN in the code!")
        return
    
    init_database()
    migrate_database()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("force", force_signal_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    logger.info("Auto Signal Bot starting...")
    print("🤖 Auto Signal Bot is running...")
    print("📢 Auto Signal System: ENABLED")
    print(f"📊 Signal Channel: {SIGNAL_CHANNEL_USERNAME}")
    print(f"⏰ Signal Interval: {SIGNAL_INTERVAL} seconds")
    print("🎯 Bet Type: BIG/SMALL Only")
    print("🔢 Bet Sequence: 1,2,3,4,5,6,7,9,10,11,12")
    print("🔄 Win Strategy: Reset to Step 1")
    print("📈 Loss Strategy: Progress through sequence")
    print("📊 Platforms: CK LOTTERY, 777 BIG WIN, 6 LOTTERY")
    print("🚀 Mode: All 3 platforms signal every minute")
    print("💰 Real Profit/Loss Tracking")
    print("⏹️  Press Ctrl+C to stop.")
    
    application.run_polling()

if __name__ == "__main__":
    main()