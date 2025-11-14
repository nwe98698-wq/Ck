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
BOT_TOKEN = "8016620146:AAEEL6Y6XoWpaRb28BCOsKMLKnxEhmlrjbM"


# Channel configuration
CHANNEL_USERNAME = "@Vipsafesingalchannel298"
CHANNEL_LINK = "https://t.me/Vipsafesingalchannel298"

# Multiple API endpoints
API_ENDPOINTS = {
    "ck": "https://ckygjf6r.com/api/webapi/",
    "777": "https://api.bigwinqaz.com/api/webapi/",
    "6": "https://6lotteryapi.com/api/webapi/"
}

# Colour Bet Types
COLOUR_BET_TYPES = {
    "RED": 10,      # selectType: 10
    "GREEN": 11,    # selectType: 11  
    "VIOLET": 12    # selectType: 12
}

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database setup
DB_NAME = "auto_bot.db"

def migrate_database():
    """Migrate database to add missing columns"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # First, make sure user_settings table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                bet_amount INTEGER DEFAULT 100,
                auto_login BOOLEAN DEFAULT 1,
                bet_sequence TEXT DEFAULT '100,300,700,1600,3200,7600,16000,32000',
                current_bet_index INTEGER DEFAULT 0,
                platform TEXT DEFAULT 'ck',
                auto_betting BOOLEAN DEFAULT 0,
                random_betting TEXT DEFAULT 'bot',
                profit_target INTEGER DEFAULT 0,
                loss_target INTEGER DEFAULT 0,
                language TEXT DEFAULT 'english',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Check and add language column if missing
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
    """Initialize SQLite database with auto-update capability"""
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
        
        # Create user_settings table - language column added
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                bet_amount INTEGER DEFAULT 100,
                auto_login BOOLEAN DEFAULT 1,
                bet_sequence TEXT DEFAULT '100,300,700,1600,3200,7600,16000,32000',
                current_bet_index INTEGER DEFAULT 0,
                platform TEXT DEFAULT 'ck',
                auto_betting BOOLEAN DEFAULT 0,
                random_betting TEXT DEFAULT 'bot',
                profit_target INTEGER DEFAULT 0,
                loss_target INTEGER DEFAULT 0,
                language TEXT DEFAULT 'english',  -- NEW: Language setting
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Check if language column exists, if not add it
        try:
            cursor.execute("SELECT language FROM user_settings LIMIT 1")
        except sqlite3.OperationalError:
            print("🔧 Adding language column to user_settings table...")
            cursor.execute('ALTER TABLE user_settings ADD COLUMN language TEXT DEFAULT "english"')
        
        # Create bet_history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bet_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                platform TEXT,
                issue TEXT,
                bet_type TEXT,
                amount INTEGER,
                result TEXT,
                profit_loss INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create pending_bets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                platform TEXT,
                issue TEXT,
                bet_type TEXT,
                amount INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create bot_sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_sessions (
                user_id INTEGER PRIMARY KEY,
                is_running BOOLEAN DEFAULT 0,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_bets INTEGER DEFAULT 0,
                total_profit INTEGER DEFAULT 0,
                session_profit INTEGER DEFAULT 0,
                session_loss INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create bs_patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bs_patterns (
                user_id INTEGER PRIMARY KEY,
                pattern TEXT DEFAULT '',
                current_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create channel_verification table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channel_verification (
                user_id INTEGER PRIMARY KEY,
                has_joined BOOLEAN DEFAULT 0,
                verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create sl_patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sl_patterns (
                user_id INTEGER PRIMARY KEY,
                pattern TEXT DEFAULT '1,2,3,4,5',
                current_sl INTEGER DEFAULT 1,
                current_index INTEGER DEFAULT 0,
                wait_loss_count INTEGER DEFAULT 0,
                bet_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create sl_bet_sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sl_bet_sessions (
                user_id INTEGER PRIMARY KEY,
                is_wait_mode BOOLEAN DEFAULT 0,
                wait_bet_type TEXT DEFAULT '',
                wait_issue TEXT DEFAULT '',
                wait_amount INTEGER DEFAULT 0,
                wait_total_profit INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create formula_patterns table for separate BS and Colour patterns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS formula_patterns (
                user_id INTEGER PRIMARY KEY,
                bs_pattern TEXT DEFAULT '',
                colour_pattern TEXT DEFAULT '',
                bs_current_index INTEGER DEFAULT 0,
                colour_current_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

def save_channel_status(user_id, has_joined):
    """Save channel join status"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO channel_verification (user_id, has_joined, verified_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, has_joined))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving channel status: {e}")
        return False

def get_channel_status(user_id):
    """Get channel join status"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT has_joined FROM channel_verification WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return bool(result[0])
        return False
    except Exception as e:
        logger.error(f"Error getting channel status: {e}")
        return False

def save_user_credentials(user_id, phone, password, platform='ck'):
    """Save user credentials to database"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, phone, password, platform)
            VALUES (?, ?, ?, ?)
        ''', (user_id, phone, password, platform))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving user credentials: {e}")
        return False

def get_user_credentials(user_id):
    """Get user credentials from database"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT phone, password, platform FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {'phone': result[0], 'password': result[1], 'platform': result[2]}
        return None
    except Exception as e:
        logger.error(f"Error getting user credentials: {e}")
        return None

def save_user_setting(user_id, setting_key, setting_value):
    """Save user setting with error handling for missing columns"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Check if user exists in settings
        cursor.execute('SELECT user_id FROM user_settings WHERE user_id = ?', (user_id,))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO user_settings (user_id) VALUES (?)', (user_id,))
        
        # Update the setting with error handling
        try:
            cursor.execute(f'UPDATE user_settings SET {setting_key} = ? WHERE user_id = ?', 
                           (setting_value, user_id))
        except sqlite3.OperationalError as e:
            if "no such column" in str(e):
                print(f"🔧 Column {setting_key} not found, adding it...")
                # Add missing column
                cursor.execute(f'ALTER TABLE user_settings ADD COLUMN {setting_key} TEXT')
                cursor.execute(f'UPDATE user_settings SET {setting_key} = ? WHERE user_id = ?', 
                               (setting_value, user_id))
            else:
                raise e
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving user setting {setting_key}: {e}")
        return False

def get_user_setting(user_id, setting_key, default=None):
    """Get user setting with error handling for missing columns"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f'SELECT {setting_key} FROM user_settings WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
        except sqlite3.OperationalError as e:
            if "no such column" in str(e):
                print(f"🔧 Column {setting_key} not found, returning default...")
                return default
            else:
                raise e
        
        conn.close()
        
        if result and result[0] is not None:
            return result[0]
        return default
    except Exception as e:
        logger.error(f"Error getting user setting {setting_key}: {e}")
        return default

def save_bot_session(user_id, is_running=False, total_bets=0, total_profit=0, session_profit=0, session_loss=0):
    """Save bot session data"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO bot_sessions 
            (user_id, is_running, total_bets, total_profit, session_profit, session_loss, last_activity)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, is_running, total_bets, total_profit, session_profit, session_loss))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving bot session: {e}")
        return False

def get_bot_session(user_id):
    """Get bot session data"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT is_running, total_bets, total_profit, session_profit, session_loss FROM bot_sessions WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'is_running': bool(result[0]),
                'total_bets': result[1] or 0,
                'total_profit': result[2] or 0,
                'session_profit': result[3] or 0,
                'session_loss': result[4] or 0
            }
        return {'is_running': False, 'total_bets': 0, 'total_profit': 0, 'session_profit': 0, 'session_loss': 0}
    except Exception as e:
        logger.error(f"Error getting bot session: {e}")
        return {'is_running': False, 'total_bets': 0, 'total_profit': 0, 'session_profit': 0, 'session_loss': 0}

def update_bot_stats(user_id, profit=0):
    """Update bot statistics"""
    try:
        session = get_bot_session(user_id)
        new_total_bets = session['total_bets'] + 1
        new_total_profit = session['total_profit'] + profit
        
        # Update session profit/loss
        new_session_profit = session['session_profit']
        new_session_loss = session['session_loss']
        
        if profit > 0:
            new_session_profit += profit
        else:
            new_session_loss += abs(profit)
        
        save_bot_session(user_id, True, new_total_bets, new_total_profit, new_session_profit, new_session_loss)
        return True
    except Exception as e:
        logger.error(f"Error updating bot stats: {e}")
        return False

def reset_session_stats(user_id):
    """Reset session statistics"""
    try:
        save_bot_session(user_id, True, 0, 0, 0, 0)
        return True
    except Exception as e:
        logger.error(f"Error resetting session stats: {e}")
        return False

def save_bet_history(user_id, platform, issue, bet_type, amount, result, profit_loss):
    """Save bet history"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bet_history (user_id, platform, issue, bet_type, amount, result, profit_loss)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, platform, issue, bet_type, amount, result, profit_loss))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving bet history: {e}")
        return False

def get_bet_history(user_id, platform=None, limit=10):
    """Get user bet history"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        if platform:
            cursor.execute('''
                SELECT platform, issue, bet_type, amount, result, profit_loss, created_at 
                FROM bet_history 
                WHERE user_id = ? AND platform = ?
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (user_id, platform, limit))
        else:
            cursor.execute('''
                SELECT platform, issue, bet_type, amount, result, profit_loss, created_at 
                FROM bet_history 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (user_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Error getting bet history: {e}")
        return []

def get_current_bet_amount(user_id):
    """Get current bet amount based on sequence - FINAL FIXED"""
    try:
        bet_sequence = get_user_setting(user_id, 'bet_sequence', '100,300,700,1600,3200,7600,16000,32000')
        current_index = get_user_setting(user_id, 'current_bet_index', 0)
        
        amounts = [int(x.strip()) for x in bet_sequence.split(',')]
        
        print(f"🔧 DEBUG: get_current_bet_amount")
        print(f"🔧 DEBUG: Current Index: {current_index}")
        print(f"🔧 DEBUG: Sequence: {bet_sequence}")
        print(f"🔧 DEBUG: Amounts: {amounts}")
        
        # ✅ FIXED: Always check bounds
        if current_index < len(amounts):
            amount = amounts[current_index]
            current_step = current_index + 1
            print(f"🔧 DEBUG: Returning: {amount}K at index {current_index} (Step {current_step})")
            return amount
        else:
            # If index is out of bounds, reset to first amount
            amount = amounts[0] if amounts else 100
            save_user_setting(user_id, 'current_bet_index', 0)
            print(f"🔧 DEBUG: Index out of bounds, resetting to: {amount}K at index 0")
            return amount
    except Exception as e:
        logger.error(f"Error in get_current_bet_amount: {e}")
        return 100

def update_bet_sequence(user_id, result):
    """Update bet sequence based on result (WIN/LOSE) - FIXED VERSION"""
    try:
        current_index = get_user_setting(user_id, 'current_bet_index', 0)
        bet_sequence = get_user_setting(user_id, 'bet_sequence', '100,300,700,1600,3200,7600,16000,32000')
        amounts = [int(x.strip()) for x in bet_sequence.split(',')]
        
        print(f"🔧 DEBUG: update_bet_sequence START")
        print(f"🔧 DEBUG: Current Index: {current_index}, Result: {result}")
        print(f"🔧 DEBUG: Sequence: {bet_sequence}")
        print(f"🔧 DEBUG: Amounts: {amounts}")
        
        if result == "WIN":
            new_index = 0  # Win ရင် အစပြန်စ
            print(f"🔧 DEBUG: WIN - Reset index to 0")
        else:
            # Loss ရင် နောက်တစ်ဆင့်သို့
            new_index = current_index + 1
            print(f"🔧 DEBUG: LOSE - Current index: {current_index} -> New index: {new_index}")
            
            # Sequence ဆုံးရင် အစပြန်စ
            if new_index >= len(amounts):
                new_index = 0
                print(f"🔧 DEBUG: LOSE - Sequence ended, reset to 0")
        
        # ✅ FIXED: Save the new index
        save_user_setting(user_id, 'current_bet_index', new_index)
        
        print(f"🔧 DEBUG: update_bet_sequence END")
        print(f"🔧 DEBUG: Index updated: {current_index} -> {new_index}")
        
        return new_index
        
    except Exception as e:
        logger.error(f"Error in update_bet_sequence: {e}")
        return 0
        
def save_pending_bet(user_id, platform, issue, bet_type, amount):
    """Save pending bet waiting for result"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO pending_bets (user_id, platform, issue, bet_type, amount)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, platform, issue, bet_type, amount))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving pending bet: {e}")
        return False

def get_pending_bets(user_id, platform=None):
    """Get all pending bets for user"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        if platform:
            cursor.execute('''
                SELECT platform, issue, bet_type, amount FROM pending_bets 
                WHERE user_id = ? AND platform = ?
                ORDER BY created_at DESC
            ''', (user_id, platform))
        else:
            cursor.execute('''
                SELECT platform, issue, bet_type, amount FROM pending_bets 
                WHERE user_id = ? 
                ORDER BY created_at DESC
            ''', (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Error getting pending bets: {e}")
        return []

def remove_pending_bet(user_id, platform, issue):
    """Remove pending bet after result is known"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM pending_bets WHERE user_id = ? AND platform = ? AND issue = ?', 
                       (user_id, platform, issue))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error removing pending bet: {e}")
        return False

def has_user_bet_on_issue(user_id, platform, issue):
    """Check if user has already bet on this issue"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT issue FROM pending_bets WHERE user_id = ? AND platform = ? AND issue = ?', 
                       (user_id, platform, issue))
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    except Exception as e:
        logger.error(f"Error checking user bet on issue: {e}")
        return False

# Formula Pattern Functions (NEW: Separate BS and Colour patterns)
def save_formula_patterns(user_id, bs_pattern="", colour_pattern=""):
    """Save BS and Colour patterns separately"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT user_id FROM formula_patterns WHERE user_id = ?', (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing
            update_fields = []
            update_values = []
            
            if bs_pattern is not None:
                update_fields.append("bs_pattern = ?")
                update_values.append(bs_pattern)
                update_fields.append("bs_current_index = 0")
                
            if colour_pattern is not None:
                update_fields.append("colour_pattern = ?")
                update_values.append(colour_pattern)
                update_fields.append("colour_current_index = 0")
                
            if update_fields:
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                update_values.append(user_id)
                
                query = f'UPDATE formula_patterns SET {", ".join(update_fields)} WHERE user_id = ?'
                cursor.execute(query, update_values)
        else:
            # Insert new
            cursor.execute('''
                INSERT INTO formula_patterns (user_id, bs_pattern, colour_pattern)
                VALUES (?, ?, ?)
            ''', (user_id, bs_pattern or "", colour_pattern or ""))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving formula patterns: {e}")
        return False

def get_formula_patterns(user_id):
    """Get both BS and Colour patterns"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT bs_pattern, colour_pattern, bs_current_index, colour_current_index FROM formula_patterns WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'bs_pattern': result[0] or "",
                'colour_pattern': result[1] or "",
                'bs_current_index': result[2] or 0,
                'colour_current_index': result[3] or 0
            }
        return {'bs_pattern': "", 'colour_pattern': "", 'bs_current_index': 0, 'colour_current_index': 0}
    except Exception as e:
        logger.error(f"Error getting formula patterns: {e}")
        return {'bs_pattern': "", 'colour_pattern': "", 'bs_current_index': 0, 'colour_current_index': 0}

def update_formula_pattern_index(user_id, pattern_type, new_index):
    """Update current index for BS or Colour pattern"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        if pattern_type == 'bs':
            cursor.execute('''
                UPDATE formula_patterns SET bs_current_index = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (new_index, user_id))
        else:  # colour
            cursor.execute('''
                UPDATE formula_patterns SET colour_current_index = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (new_index, user_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error updating {pattern_type} pattern index: {e}")
        return False

def get_next_formula_bet(user_id, formula_type):
    """Get next bet type from BS or Colour pattern"""
    try:
        patterns_data = get_formula_patterns(user_id)
        
        if formula_type == 'bs':
            pattern = patterns_data['bs_pattern']
            current_index = patterns_data['bs_current_index']
        else:  # colour
            pattern = patterns_data['colour_pattern']
            current_index = patterns_data['colour_current_index']
        
        if not pattern:
            return None, current_index
        
        # Convert pattern to list
        pattern_list = [p.strip().upper() for p in pattern.split(',')]
        
        if current_index >= len(pattern_list):
            current_index = 0  # Reset to start if pattern completed
        
        next_bet = pattern_list[current_index]
        new_index = current_index + 1
        
        # Update the index
        update_formula_pattern_index(user_id, formula_type, new_index)
        
        return next_bet, current_index
    except Exception as e:
        logger.error(f"Error getting next {formula_type} bet: {e}")
        return None, 0

def clear_formula_patterns(user_id, pattern_type=None):
    """Clear BS and/or Colour patterns"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        if pattern_type == 'bs':
            cursor.execute('UPDATE formula_patterns SET bs_pattern = "", bs_current_index = 0 WHERE user_id = ?', (user_id,))
        elif pattern_type == 'colour':
            cursor.execute('UPDATE formula_patterns SET colour_pattern = "", colour_current_index = 0 WHERE user_id = ?', (user_id,))
        else:
            cursor.execute('UPDATE formula_patterns SET bs_pattern = "", colour_pattern = "", bs_current_index = 0, colour_current_index = 0 WHERE user_id = ?', (user_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error clearing formula patterns: {e}")
        return False

# BS Pattern Functions (Legacy - for backward compatibility)
def save_bs_pattern(user_id, pattern):
    """Save BS pattern for user (legacy)"""
    return save_formula_patterns(user_id, bs_pattern=pattern)

def get_bs_pattern(user_id):
    """Get BS pattern for user (legacy)"""
    patterns = get_formula_patterns(user_id)
    return {'pattern': patterns['bs_pattern'], 'current_index': patterns['bs_current_index']}

def update_bs_pattern_index(user_id, new_index):
    """Update current index in BS pattern (legacy)"""
    return update_formula_pattern_index(user_id, 'bs', new_index)

def clear_bs_pattern(user_id):
    """Clear BS pattern for user (legacy)"""
    return clear_formula_patterns(user_id, 'bs')

def get_next_bs_bet(user_id):
    """Get next bet type from BS pattern (legacy)"""
    return get_next_formula_bet(user_id, 'bs')

# SL Pattern Functions
def save_sl_pattern(user_id, pattern):
    """Save SL pattern for user"""
    try:
        print(f"🔧 DEBUG: Saving SL pattern for user {user_id}, pattern: {pattern}")
        
        # Validate pattern
        if not pattern or not isinstance(pattern, str):
            print("❌ DEBUG: Pattern is empty or not string")
            return False
            
        cleaned_pattern = pattern.strip()
        if not cleaned_pattern:
            print("❌ DEBUG: Pattern is empty after cleaning")
            return False
        
        # Validate pattern format
        try:
            numbers = [int(x.strip()) for x in cleaned_pattern.split(',')]
            if not all(1 <= num <= 5 for num in numbers):
                print("❌ DEBUG: Pattern numbers not in range 1-5")
                return False
            
            # For specific patterns: set custom starting points
            if cleaned_pattern == "2,1,3":
                current_sl = 2
                current_index = 0
                is_wait_mode = True
                
                print(f"✅ DEBUG: 2,1,3 pattern detected - Starting from SL 2 with WAIT BOT mode")
            elif cleaned_pattern == "2,1":
                current_sl = 2
                current_index = 0
                is_wait_mode = True
                
                print(f"✅ DEBUG: 2,1 pattern detected - Starting from SL 2 with WAIT BOT mode")
            else:
                # Normal start for other patterns
                current_sl = numbers[0]
                current_index = 0
                is_wait_mode = current_sl >= 2
            
            # Save session and pattern data
            save_sl_bet_session(user_id, is_wait_mode, '', '', 0, 0)
            update_sl_pattern(user_id, current_sl=current_sl, current_index=current_index, wait_loss_count=0, bet_count=0)
                
        except ValueError:
            print("❌ DEBUG: Pattern contains non-numeric values")
            return False
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        print("🔧 DEBUG: Database connected")
        
        # Check if user exists
        cursor.execute('SELECT user_id FROM sl_patterns WHERE user_id = ?', (user_id,))
        existing = cursor.fetchone()
        print(f"🔧 DEBUG: User exists check: {existing}")
        
        if existing:
            # Update existing
            try:
                cursor.execute('''
                    UPDATE sl_patterns 
                    SET pattern = ?, current_sl = ?, current_index = ?, wait_loss_count = 0, bet_count = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (cleaned_pattern, current_sl, current_index, user_id))
                print(f"🔧 DEBUG: Updated existing pattern, affected rows: {cursor.rowcount}")
            except Exception as e:
                print(f"❌ DEBUG: Update error: {e}")
                conn.close()
                return False
        else:
            # Insert new
            try:
                cursor.execute('''
                    INSERT INTO sl_patterns 
                    (user_id, pattern, current_sl, current_index, wait_loss_count, bet_count)
                    VALUES (?, ?, ?, ?, 0, 0)
                ''', (user_id, cleaned_pattern, current_sl, current_index))
                print(f"🔧 DEBUG: Inserted new pattern, affected rows: {cursor.rowcount}")
            except Exception as e:
                print(f"❌ DEBUG: Insert error: {e}")
                conn.close()
                return False
        
        conn.commit()
        conn.close()
        
        print(f"✅ DEBUG: SL pattern successfully saved: {cleaned_pattern}, starting from SL {current_sl}")
        return True
        
    except Exception as e:
        print(f"❌ DEBUG: Overall error in save_sl_pattern: {e}")
        return False

def get_sl_pattern(user_id):
    """Get SL pattern for user - RETURN EMPTY IF NOT SET"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT pattern, current_sl, current_index, wait_loss_count, bet_count FROM sl_patterns WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            pattern = result[0] or ''
            # If pattern is default, treat as empty
            if pattern == '1,2,3,4,5':
                pattern = ''
                
            return {
                'pattern': pattern,
                'current_sl': result[1] or 1,
                'current_index': result[2] or 0,
                'wait_loss_count': result[3] or 0,
                'bet_count': result[4] or 0
            }
        
        # Return empty pattern if not set
        return {'pattern': '', 'current_sl': 1, 'current_index': 0, 'wait_loss_count': 0, 'bet_count': 0}
        
    except Exception as e:
        print(f"❌ DEBUG: Error in get_sl_pattern: {e}")
        return {'pattern': '', 'current_sl': 1, 'current_index': 0, 'wait_loss_count': 0, 'bet_count': 0}
        
def update_sl_pattern(user_id, current_sl=None, current_index=None, wait_loss_count=None, bet_count=None):
    """Update SL pattern data"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Build update query
        update_fields = []
        update_values = []
        
        if current_sl is not None:
            update_fields.append("current_sl = ?")
            update_values.append(current_sl)
        
        if current_index is not None:
            update_fields.append("current_index = ?")
            update_values.append(current_index)
            
        if wait_loss_count is not None:
            update_fields.append("wait_loss_count = ?")
            update_values.append(wait_loss_count)
            
        if bet_count is not None:
            update_fields.append("bet_count = ?")
            update_values.append(bet_count)
        
        if update_fields:
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            update_values.append(user_id)
            
            query = f'UPDATE sl_patterns SET {", ".join(update_fields)} WHERE user_id = ?'
            cursor.execute(query, update_values)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ DEBUG: Error updating SL pattern: {e}")
        return False

def reset_sl_pattern(user_id):
    """Reset SL pattern to initial state - PROPER BET COUNT INITIALIZATION"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Get current pattern to preserve it
        cursor.execute('SELECT pattern FROM sl_patterns WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        current_pattern = result[0] if result else '1,2,3,4,5'
        
        print(f"🔧 DEBUG: Resetting pattern: {current_pattern} for user {user_id}")
        
        # For specific patterns, set custom starting points
        if current_pattern == "2,1,3":
            current_sl = 2
            current_index = 0
            is_wait_mode = True
            bet_count = 0  # ✅ FIXED: Start with bet count 0
            print("✅ DEBUG: 2,1,3 pattern - setting WAIT MODE")
        elif current_pattern == "2,1":
            current_sl = 2
            current_index = 0
            is_wait_mode = True
            bet_count = 0  # ✅ FIXED: Start with bet count 0
            print("✅ DEBUG: 2,1 pattern - setting WAIT MODE")
        else:
            # For normal patterns, start from first SL
            numbers = [int(x.strip()) for x in current_pattern.split(',')]
            current_sl = numbers[0]
            current_index = 0
            is_wait_mode = current_sl >= 2
            bet_count = 0  # ✅ FIXED: Start with bet count 0
            print(f"✅ DEBUG: Normal pattern {current_pattern} - WAIT MODE: {is_wait_mode}")
        
        # Update or insert with explicit values
        cursor.execute('''
            INSERT OR REPLACE INTO sl_patterns 
            (user_id, pattern, current_sl, current_index, wait_loss_count, bet_count)
            VALUES (?, ?, ?, ?, 0, ?)
        ''', (user_id, current_pattern, current_sl, current_index, bet_count))
        
        # Force set the session with explicit wait mode
        cursor.execute('''
            INSERT OR REPLACE INTO sl_bet_sessions 
            (user_id, is_wait_mode, wait_bet_type, wait_issue, wait_amount, wait_total_profit)
            VALUES (?, ?, '', '', 0, 0)
        ''', (user_id, 1 if is_wait_mode else 0))
        
        # ✅ FIXED: Clear pending bets
        cursor.execute('DELETE FROM pending_bets WHERE user_id = ?', (user_id,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ DEBUG: SL pattern reset complete - SL: {current_sl}, Wait Mode: {is_wait_mode}, Bet Count: {bet_count}")
        return True
        
    except Exception as e:
        print(f"❌ DEBUG: Error in reset_sl_pattern: {e}")
        return False
# SL Bet Session Functions
def save_sl_bet_session(user_id, is_wait_mode=False, wait_bet_type='', wait_issue='', wait_amount=0, wait_total_profit=0):
    """Save SL bet session data"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO sl_bet_sessions (user_id, is_wait_mode, wait_bet_type, wait_issue, wait_amount, wait_total_profit, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, is_wait_mode, wait_bet_type, wait_issue, wait_amount, wait_total_profit))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving SL bet session: {e}")
        return False

def get_sl_bet_session(user_id):
    """Get SL bet session data"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT is_wait_mode, wait_bet_type, wait_issue, wait_amount, wait_total_profit FROM sl_bet_sessions WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'is_wait_mode': bool(result[0]),
                'wait_bet_type': result[1],
                'wait_issue': result[2],
                'wait_amount': result[3],
                'wait_total_profit': result[4]
            }
        return {'is_wait_mode': False, 'wait_bet_type': '', 'wait_issue': '', 'wait_amount': 0, 'wait_total_profit': 0}
    except Exception as e:
        logger.error(f"Error getting SL bet session: {e}")
        return {'is_wait_mode': False, 'wait_bet_type': '', 'wait_issue': '', 'wait_amount': 0, 'wait_total_profit': 0}

# Language Functions
def get_user_language(user_id):
    """Get user's preferred language"""
    return get_user_setting(user_id, 'language', 'english')

def get_localized_message(message_key, language='english'):
    """Get localized message based on language"""
    messages = {
        'english': {
            'welcome': "🎰 **Auto Lottery Bot** 🎯\n\nWelcome!",
            'login_success': "✅ **Login Successful!**",
            'bet_placed': "✅ **Bet Placed Successfully!**",
            'balance': "💰 Balance",
            'language_set': "✅ **Language set to English** 🇺🇸\n\nAll bot messages will now be displayed in English.",
            'choose_language': "🌐 **Choose Your Language**\n\nPlease select your preferred language:",
            'bot_settings': "⚙️ Bot Setting",
            'random_big': "🎲 Random BIG",
            'random_small': "🎯 Random SMALL",
            'random_bot': "🔄 Random Bot",
            'follow_bot': "📈 Follow Bot",
            'bs_formula': "📋 BS Formula",
            'colour_formula': "🔮 Colour Formula",
            'bot_stats': "📊 Bot Stats",
            'set_bet_sequence': "🔢 Set Bet Sequence",
            'profit_target': "🎯 Profit Target",
            'loss_target': "🎯 Loss Target",
            'reset_stats': "🔄 Reset Stats",
            'back_main_menu': "↩️ Main Menu",
            'ck_login': "🔐 CK Login",
            'bigwin_login': "🔐 777 Login",
            'six_login': "🔐 6 Login",
            'results': "📊 Results",
            'bet_big': "🎲 Bet BIG",
            'bet_small': "🎯 Bet SMALL",
            'bet_red': "🔴 Bet RED",
            'bet_green': "🟢 Bet GREEN",
            'bet_violet': "🟣 Bet VIOLET",
            'my_bets': "📈 My Bets",
            'sl_layer': "📋 SL Layer",
            'language': "🌐 Language",
            'run_bot': "🤖 Run Bot",
            'stop_bot': "🛑 Stop Bot",
            # Add more English messages as needed
        },
        'burmese': {
            'welcome': "🎰 **အလိုအလျောက် ထီဘော့** 🎯\n\nကြိုဆိုပါတယ်!",
            'login_success': "✅ **လော့ဂ်အင် အောင်မြင်ပါတယ်**",
            'bet_placed': "✅ **ထီထိုးပြီးပါပြီ**",
            'balance': "💰 ပိုက်ဆံ",
            'language_set': "✅ **ဘာသာစကား ပြောင်းလဲပြီးပါပြီ** 🇲🇲\n\nဘော့သတင်းစကားအားလုံးကို မြန်မာဘာသာဖြင့် ပြသပေးပါမည်။",
            'choose_language': "🌐 **ဘာသာစကား ရွေးချယ်ပါ**\n\nကျေးဇူးပြု၍ သင့်နှစ်သက်ရာ ဘာသာစကားကို ရွေးချယ်ပါ:",
            'bot_settings': "⚙️ ဘော့ ဆက်တင်များ",
            'random_big': "🎲 ကြီးတစ်ခုတည်း",
            'random_small': "🎯 သေးတစ်ခုတည်း",
            'random_bot': "🔄 ကြီး/သေး ကျပန်း",
            'follow_bot': "📈 နောက်ဆုံးရလဒ်အတိုင်း",
            'bs_formula': "📋 BS ပုံသေနည်း",
            'colour_formula': "🔮 အရောင် ပုံသေနည်း",
            'bot_stats': "📊 ဘော့ စာရင်းဇယား",
            'set_bet_sequence': "🔢 ထိုးကြေးအစဉ် သတ်မှတ်ရန်",
            'profit_target': "🎯 အမြတ်ပန်းတိုင်",
            'loss_target': "🎯 အရှုံးပန်းတိုင်",
            'reset_stats': "🔄 စာရင်းများ ပြန်လည်သတ်မှတ်ရန်",
            'back_main_menu': "↩️ ပင်မမီနူး",
            'ck_login': "🔐 CK လော့ဂ်အင်",
            'bigwin_login': "🔐 777 လော့ဂ်အင်",
            'six_login': "🔐 6 လော့ဂ်အင်",
            'results': "📊 ရလဒ်များ",
            'bet_big': "🎲 ကြီးထိုးရန်",
            'bet_small': "🎯 သေးထိုးရန်",
            'bet_red': "🔴 အနီထိုးရန်",
            'bet_green': "🟢 အစိမ်းထိုးရန်",
            'bet_violet': "🟣 ခရမ်းထိုးရန်",
            'my_bets': "📈 ကျွန်ုပ်၏ထိုးငွေများ",
            'sl_layer': "📋 SL Layer",
            'language': "🌐 ဘာသာစကား",
            'run_bot': "🤖 ဘော့စတင်ရန်",
            'stop_bot': "🛑 ဘော့ရပ်ရန်"
        },
        'chinese': {
            'welcome': "🎰 **自动彩票机器人** 🎯\n\n欢迎！",
            'login_success': "✅ **登录成功！**",
            'bet_placed': "✅ **投注成功！**",
            'balance': "💰 账户信息",
            'language_set': "✅ **语言已设置为中文** 🇨🇳\n\n所有机器人消息现在将以中文显示。",
            'choose_language': "🌐 **选择您的语言**\n\n请选择您偏好的语言:",
            'bot_settings': "⚙️ 机器人设置",
            'random_big': "🎲 只投注大",
            'random_small': "🎯 只投注小",
            'random_bot': "🔄 随机大小",
            'follow_bot': "📈 跟随最后结果",
            'bs_formula': "📋 BS 公式",
            'colour_formula': "🔮 颜色公式",
            'bot_stats': "📊 机器人统计",
            'set_bet_sequence': "🔢 设置投注序列",
            'profit_target': "🎯 盈利目标",
            'loss_target': "🎯 亏损目标",
            'reset_stats': "🔄 重置统计",
            'back_main_menu': "↩️ 主菜单",
            'ck_login': "🔐 CK 登录",
            'bigwin_login': "🔐 777 登录",
            'six_login': "🔐 6 登录",
            'results': "📊 结果",
            'bet_big': "🎲 投注大",
            'bet_small': "🎯 投注小",
            'bet_red': "🔴 投注红",
            'bet_green': "🟢 投注绿",
            'bet_violet': "🟣 投注紫",
            'my_bets': "📈 我的投注",
            'sl_layer': "📋 SL 层",
            'language': "🌐 语言",
            'run_bot': "🤖 运行机器人",
            'stop_bot': "🛑 停止机器人"
        },
        'thai': {
            'welcome': "🎰 **บอตลอตเตอรี่อัตโนมัติ** 🎯\n\nยินดีต้อนรับ!",
            'login_success': "✅ **เข้าสู่ระบบสำเร็จ!**",
            'bet_placed': "✅ **วางเดิมพันสำเร็จ!**",
            'balance': "💰 ข้อมูลบัญชี",
            'language_set': "✅ **ตั้งค่าภาษาเป็นไทยแล้ว** 🇹🇭\n\nข้อความบอททั้งหมดจะแสดงเป็นภาษาไทย",
            'choose_language': "🌐 **เลือกภาษาของคุณ**\n\nกรุณาเลือกภาษาที่คุณต้องการ:",
            'bot_settings': "⚙️ การตั้งค่าบอท",
            'random_big': "🎲 สุ่มใหญ่เท่านั้น",
            'random_small': "🎯 สุ่มเล็กเท่านั้น",
            'random_bot': "🔄 สุ่มใหญ่/เล็ก",
            'follow_bot': "📈 ตามผลล่าสุด",
            'bs_formula': "📋 สูตร BS",
            'colour_formula': "🔮 สูตรสี",
            'bot_stats': "📊 สถิติบอท",
            'set_bet_sequence': "🔢 ตั้งลำดับการเดิมพัน",
            'profit_target': "🎯 เป้าหมายกำไร",
            'loss_target': "🎯 เป้าหมายขาดทุน",
            'reset_stats': "🔄 รีเซ็ตสถิติ",
            'back_main_menu': "↩️ เมนูหลัก",
            'ck_login': "🔐 CK เข้าสู่ระบบ",
            'bigwin_login': "🔐 777 เข้าสู่ระบบ",
            'six_login': "🔐 6 เข้าสู่ระบบ",
            'results': "📊 ผลลัพธ์",
            'bet_big': "🎲 เดิมพันใหญ่",
            'bet_small': "🎯 เดิมพันเล็ก",
            'bet_red': "🔴 เดิมพันสีแดง",
            'bet_green': "🟢 เดิมพันสีเขียว",
            'bet_violet': "🟣 เดิมพันสีม่วง",
            'my_bets': "📈 การเดิมพันของฉัน",
            'sl_layer': "📋 SL Layer",
            'language': "🌐 ภาษา",
            'run_bot': "🤖 เริ่มบอท",
            'stop_bot': "🛑 หยุดบอท"
        },
        'urdu': {
            'welcome': "🎰 **آٹو لاٹری بوٹ** 🎯\n\nخوش آمدید!",
            'login_success': "✅ **لاگ ان کامیاب!**",
            'bet_placed': "✅ شرط لگائی گئی!",
            'balance': "💰 **اکاؤنٹ کی معلومات**",
            'language_set': "✅ **زبان اردو میں تبدیل کر دی گئی** 🇵🇰\n\nتمام بوٹ کے پیغامات اب اردو میں دکھائے جائیں گے۔",
            'choose_language': "🌐 **اپنی زبان منتخب کریں**\n\nبراہ کرم اپنی ترجیحی زبان منتخب کریں:",
            'bot_settings': "⚙️ بوٹ کی ترتیبات",
            'random_big': "🎲 صرف بڑا",
            'random_small': "🎯 صرف چھوٹا",
            'random_bot': "🔄 بڑا/چھوٹا بے ترتیب",
            'follow_bot': "📈 آخری نتیجہ کی پیروی کریں",
            'bs_formula': "📋 BS فارمولا",
            'colour_formula': "🔮 رنگ فارمولا",
            'bot_stats': "📊 بوٹ کے اعداد و شمار",
            'set_bet_sequence': "🔢 شرط کی ترتیب سیٹ کریں",
            'profit_target': "🎯 منافع کا ہدف",
            'loss_target': "🎯 نقصان کا ہدف",
            'reset_stats': "🔄 اعداد و شمار دوبارہ ترتیب دیں",
            'back_main_menu': "↩️ مین مینو",
            'ck_login': "🔐 CK لاگ ان",
            'bigwin_login': "🔐 777 لاگ ان",
            'six_login': "🔐 6 لاگ ان",
            'results': "📊 نتائج",
            'bet_big': "🎲 بڑا شرط لگائیں",
            'bet_small': "🎯 چھوٹا شرط لگائیں",
            'bet_red': "🔴 سرخ شرط لگائیں",
            'bet_green': "🟢 سبز شرط لگائیں",
            'bet_violet': "🟣 بنفشی شرط لگائیں",
            'my_bets': "📈 میری شرطیں",
            'sl_layer': "📋 SL Layer",
            'language': "🌐 زبان",
            'run_bot': "🤖 بوٹ چلائیں",
            'stop_bot': "🛑 بوٹ روکیں"
        }
    }
    
    return messages.get(language, messages['english']).get(message_key, message_key)

def get_main_keyboard(user_id=None):
    """Get main keyboard with localized text"""
    if user_id:
        language = get_user_language(user_id)
    else:
        language = 'english'
    
    # Get localized button texts
    button_texts = {
        'ck_login': get_localized_message('ck_login', language),
        'bigwin_login': get_localized_message('bigwin_login', language),
        'six_login': get_localized_message('six_login', language),
        'balance': get_localized_message('balance', language),
        'results': get_localized_message('results', language),
        'bet_big': get_localized_message('bet_big', language),
        'bet_small': get_localized_message('bet_small', language),
        'bet_red': get_localized_message('bet_red', language),
        'bet_green': get_localized_message('bet_green', language),
        'bet_violet': get_localized_message('bet_violet', language),
        'bot_settings': get_localized_message('bot_settings', language),
        'my_bets': get_localized_message('my_bets', language),
        'sl_layer': get_localized_message('sl_layer', language),
        'language': get_localized_message('language', language),
        'run_bot': get_localized_message('run_bot', language),
        'stop_bot': get_localized_message('stop_bot', language)
    }
    
    keyboard = [
        [KeyboardButton(button_texts['ck_login']), KeyboardButton(button_texts['bigwin_login']), KeyboardButton(button_texts['six_login'])],
        [KeyboardButton(button_texts['balance']), KeyboardButton(button_texts['results'])],
        [KeyboardButton(button_texts['bet_big']), KeyboardButton(button_texts['bet_small'])],
        [KeyboardButton(button_texts['bet_red']), KeyboardButton(button_texts['bet_green']), KeyboardButton(button_texts['bet_violet'])],
        [KeyboardButton(button_texts['bot_settings']), KeyboardButton(button_texts['my_bets'])],
        [KeyboardButton(button_texts['sl_layer']), KeyboardButton(button_texts['language'])],
        [KeyboardButton(button_texts['run_bot']), KeyboardButton(button_texts['stop_bot'])]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_bot_settings_keyboard(user_id=None):
    """Get bot settings keyboard with localized text"""
    if user_id:
        language = get_user_language(user_id)
    else:
        language = 'english'
    
    keyboard = [
        [KeyboardButton(get_localized_message('random_big', language)), 
         KeyboardButton(get_localized_message('random_small', language))],
        [KeyboardButton(get_localized_message('random_bot', language)), 
         KeyboardButton(get_localized_message('follow_bot', language))],
        [KeyboardButton(get_localized_message('bs_formula', language)), 
         KeyboardButton(get_localized_message('colour_formula', language))],
        [KeyboardButton(get_localized_message('bot_stats', language)), 
         KeyboardButton(get_localized_message('set_bet_sequence', language))],
        [KeyboardButton(get_localized_message('profit_target', language)), 
         KeyboardButton(get_localized_message('loss_target', language))],
        [KeyboardButton(get_localized_message('reset_stats', language)), 
         KeyboardButton(get_localized_message('back_main_menu', language))]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_language_keyboard():
    """Keyboard for language selection"""
    keyboard = [
        [KeyboardButton("🇺🇸 English"), KeyboardButton("🇲🇲 Burmese")],
        [KeyboardButton("🇨🇳 Chinese"), KeyboardButton("🇹🇭 Thailand")],
        [KeyboardButton("🇵🇰 Pakistan"), KeyboardButton("↩️ Main Menu")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_sl_layer_keyboard():
    """Keyboard for SL Layer menu - SIMPLIFIED"""
    keyboard = [
        [KeyboardButton("🔢 Set SL Pattern"), KeyboardButton("👀 View SL Pattern")],
        [KeyboardButton("🔄 Reset SL Pattern"), KeyboardButton("📊 SL Stats")],
        [KeyboardButton("↩️ Main Menu")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_login_keyboard():
    keyboard = [
        [KeyboardButton("📝 Enter Phone"), KeyboardButton("🔑 Enter Password")],
        [KeyboardButton("🚪 Login Now"), KeyboardButton("↩️ Back")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_bs_pattern_keyboard():
    keyboard = [
        [KeyboardButton("🔢 Set BS Pattern"), KeyboardButton("👀 View BS Pattern")],
        [KeyboardButton("🗑️ Clear BS Pattern"), KeyboardButton("↩️ Bot Settings")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_colour_pattern_keyboard():
    keyboard = [
        [KeyboardButton("🔢 Set Colour Pattern"), KeyboardButton("👀 View Colour Pattern")],
        [KeyboardButton("🗑️ Clear Colour Pattern"), KeyboardButton("↩️ Bot Settings")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Global storage
user_sessions = {}
issue_checkers = {}
auto_betting_tasks = {}
waiting_for_results = {}
processed_issues = {}

def reset_processed_issues(user_id: str):
    """Reset processed issues for user"""
    global processed_issues
    if user_id in processed_issues:
        processed_issues[user_id].clear()
        print(f"🔧 DEBUG: Processed issues reset for user {user_id}")
    else:
        processed_issues[user_id] = set()
        print(f"🔧 DEBUG: Processed issues initialized for user {user_id}")

async def check_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Check if user is a member of the channel"""
    try:
        # Check if user is member of channel
        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        
        if chat_member.status in ['member', 'administrator', 'creator']:
            save_channel_status(user_id, True)
            return True
        else:
            save_channel_status(user_id, False)
            return False
            
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        save_channel_status(user_id, True)
        return True

def get_join_channel_keyboard():
    """Get keyboard for joining channel"""
    keyboard = [
        [InlineKeyboardButton("📢 Join Our Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I've Joined", callback_data="check_join")]
    ]
    return InlineKeyboardMarkup(keyboard)

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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.token = ""
        
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
    
    async def login(self, phone, password):
    """Login to Lottery API - FIXED VERSION"""
    try:
        # Use Myanmar phone number format (remove leading 95 if exists)
        clean_phone = phone.replace('95', '') if phone.startswith('95') else phone
        
        body = {
            "phonetype": -1,
            "language": 0,
            "logintype": "mobile",
            "random": self.random_key(),  # Use dynamic random key
            "username": clean_phone,  # Use clean phone number
            "pwd": password,
            "timestamp": int(time.time() * 1000)  # Use milliseconds
        }
        
        body["signature"] = self.sign_md5(body).upper()
        
        print(f"🔧 DEBUG: {self.platform.upper()} Login Request:")
        print(f"🔧 DEBUG: URL: {self.base_url}Login")
        print(f"🔧 DEBUG: Headers: {self.headers}")
        print(f"🔧 DEBUG: Body: {body}")
        
        response = requests.post(
            f"{self.base_url}Login",
            headers=self.headers,
            json=body,
            timeout=30,
            verify=False  # Add SSL verification bypass for testing
        )
        
        print(f"🔧 DEBUG: {self.platform.upper()} Login Response:")
        print(f"🔧 DEBUG: Status Code: {response.status_code}")
        print(f"🔧 DEBUG: Response Text: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('msgCode') == 0:
                token_data = result.get('data', {})
                self.token = f"{token_data.get('tokenHeader', '')}{token_data.get('token', '')}"
                self.headers["Authorization"] = self.token
                return True, "Login successful", self.token
            else:
                error_msg = result.get('msg', 'Login failed')
                # Provide more specific error messages
                if "password" in error_msg.lower():
                    error_msg = "Invalid password. Please check your password."
                elif "user" in error_msg.lower():
                    error_msg = "User not found. Please check your phone number."
                elif "locked" in error_msg.lower():
                    error_msg = "Account temporarily locked. Please try again later."
                return False, error_msg, ""
        else:
            return False, f"API connection failed: {response.status_code}", ""
            
    except requests.exceptions.Timeout:
        return False, "Login timeout. Please check your internet connection and try again.", ""
    except requests.exceptions.ConnectionError:
        return False, "Connection error. Please check your internet connection.", ""
    except Exception as e:
        logger.error(f"Login error for {self.platform}: {e}")
        return False, f"Login error: {str(e)}", ""

def random_key(self):
    """Generate random key for API - IMPROVED VERSION"""
    import string
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(32))

def sign_md5(self, data_dict):
    """Generate MD5 signature for API requests - IMPROVED VERSION"""
    try:
        sign_data = data_dict.copy()
        if 'signature' in sign_data:
            del sign_data['signature']
        
        # Sort and create hash string
        sorted_data = dict(sorted(sign_data.items()))
        hash_string = json.dumps(sorted_data, separators=(',', ':'), ensure_ascii=False)
        
        # Remove spaces and ensure proper encoding
        hash_string = hash_string.replace(' ', '').encode('utf-8')
        
        md5_hash = hashlib.md5(hash_string).hexdigest().upper()
        
        print(f"🔧 DEBUG: MD5 Signature Generation:")
        print(f"🔧 DEBUG: Original Data: {sorted_data}")
        print(f"🔧 DEBUG: Hash String: {hash_string}")
        print(f"🔧 DEBUG: MD5 Hash: {md5_hash}")
        
        return md5_hash
    except Exception as e:
        print(f"❌ DEBUG: MD5 Signature Error: {e}")
        return ""
    
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
    
    async def get_balance(self):
        """Get user balance"""
        try:
            body = {
                "language": 0,
                "random": "9078efc98754430e92e51da59eb2563c",
                "timestamp": int(time.time())
            }
            body["signature"] = self.sign_md5(body).upper()
            
            response = requests.post(
                f"{self.base_url}GetBalance",
                headers=self.headers,
                json=body,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('msgCode') == 0:
                    return result.get('data', {}).get('amount', 0)
            return 0
        except Exception as e:
            logger.error(f"Get balance error for {self.platform}: {e}")
            return 0
    
    async def get_user_info(self):
        """Get user information"""
        try:
            body = {
                "language": 0,
                "random": "9078efc98754430e92e51da59eb2563c",
                "timestamp": int(time.time())
            }
            body["signature"] = self.sign_md5(body).upper()
            
            response = requests.post(
                f"{self.base_url}GetUserInfo",
                headers=self.headers,
                json=body,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('msgCode') == 0:
                    return result.get('data', {})
            return {}
        except Exception as e:
            logger.error(f"Get user info error for {self.platform}: {e}")
            return {}
    
    async def place_bet(self, amount, bet_type):
        """Place a bet (13=BIG, 14=SMALL, 10=RED, 11=GREEN, 12=VIOLET)"""
        try:
            issue_id = await self.get_current_issue()
            if not issue_id:
                return False, "Failed to get current issue", "", 0
            
            # Determine if it's colour bet or normal bet
            is_colour_bet = bet_type in [10, 11, 12]
            
            # 6 Lottery requires different bet amount calculation
            if self.platform == '6':
                base_amount = amount
                bet_count = 1
            else:
                if is_colour_bet:
                    base_amount = 10 if amount < 10000 else 10 ** (len(str(int(amount))) - 2)
                    bet_count = int(amount / base_amount)
                else:
                    base_amount = 10 if amount < 10000 else 10 ** (len(str(int(amount))) - 2)
                    bet_count = int(amount / base_amount)
            
            body = {
                "typeId": 1,
                "issuenumber": issue_id,
                "language": 0,
                "gameType": 2 if not is_colour_bet else 0,
                "amount": base_amount,
                "betCount": bet_count,
                "selectType": int(bet_type),
                "random": self.random_key(),
                "timestamp": int(time.time())
            }
            body["signature"] = self.sign_md5(body).upper()
            
            logger.info(f"{self.platform.upper()} {('Colour' if is_colour_bet else 'Normal')} Bet Request: {body}")
            
            response = requests.post(
                f"{self.base_url}GameBetting",
                headers=self.headers,
                json=body,
                timeout=10
            )
            
            logger.info(f"{self.platform.upper()} Bet API Response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0 or result.get('msgCode') == 0:
                    if is_colour_bet:
                        potential_profit = int(amount * 2.5)
                    else:
                        potential_profit = int(amount * 0.96)
                    return True, "Bet placed successfully", issue_id, potential_profit
                else:
                    error_msg = result.get('msg', 'Bet failed')
                    if "amount" in error_msg.lower() or "betting" in error_msg.lower():
                        if self.platform == '6':
                            return await self.place_bet_fallback(amount, bet_type, issue_id, is_colour_bet)
                        else:
                            error_msg = f"Betting amount error: {error_msg}"
                    return False, error_msg, issue_id, 0
            return False, f"API connection failed: {response.status_code}", issue_id, 0
            
        except Exception as e:
            logger.error(f"Place bet error for {self.platform}: {e}")
            return False, f"Bet error: {str(e)}", "", 0
    
    async def place_bet_fallback(self, amount, bet_type, issue_id, is_colour_bet=False):
        """Fallback betting method for 6 Lottery with colour bet support"""
        try:
            if amount >= 100:
                base_amount = 100
                bet_count = amount // 100
            elif amount >= 50:
                base_amount = 50
                bet_count = amount // 50
            elif amount >= 10:
                base_amount = 10
                bet_count = amount // 10
            else:
                base_amount = amount
                bet_count = 1
            
            body = {
                "typeId": 1,
                "issuenumber": issue_id,
                "language": 0,
                "gameType": 2 if not is_colour_bet else 0,
                "amount": base_amount,
                "betCount": bet_count,
                "selectType": int(bet_type),
                "random": self.random_key(),
                "timestamp": int(time.time())
            }
            body["signature"] = self.sign_md5(body).upper()
            
            logger.info(f"{self.platform.upper()} Fallback {('Colour' if is_colour_bet else 'Normal')} Bet Request: {body}")
            
            response = requests.post(
                f"{self.base_url}GameBetting",
                headers=self.headers,
                json=body,
                timeout=10
            )
            
            logger.info(f"{self.platform.upper()} Fallback Bet API Response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0 or result.get('msgCode') == 0:
                    if is_colour_bet:
                        potential_profit = int(amount * 2.5)
                    else:
                        potential_profit = int(amount * 0.96)
                    return True, "Bet placed successfully (fallback method)", issue_id, potential_profit
                else:
                    error_msg = result.get('msg', 'Fallback bet failed')
                    return False, error_msg, issue_id, 0
            return False, f"Fallback API connection failed: {response.status_code}", issue_id, 0
            
        except Exception as e:
            logger.error(f"Fallback bet error for {self.platform}: {e}")
            return False, f"Fallback bet error: {str(e)}", issue_id, 0
    
    async def get_recent_results(self, count=10):
        """Get recent game results with NEW colour rules"""
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
                        
                        for result_item in results:
                            number = str(result_item.get('number', ''))
                            
                            if number in ['0', '5']:
                                result_item['colour'] = 'VIOLET'
                            elif number in ['5','1', '3', '7', '9']:
                                result_item['colour'] = 'GREEN'
                            elif number in ['0','2', '4', '6', '8']:
                                result_item['colour'] = 'RED'
                            else:
                                result_item['colour'] = 'UNKNOWN'
                        
                        return results
            return []
        except Exception as e:
            logger.error(f"Get results error for {self.platform}: {e}")
            return []

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
    user = update.effective_user
    user_id = str(user.id)
    
    has_joined = await check_channel_membership(update, context, user.id)
    
    if not has_joined:
        welcome_text = f"""
🎰 **Welcome to Auto Lottery Bot** 🎯

Dear {user.first_name},

To use this bot, you need to join our official channel first for updates and signals.

**Why join our channel?**
• 📊 Get daily betting signals
• 💡 Learn betting strategies  
• 🔔 Receive important updates
• 🎯 Access exclusive content

Please join our channel below and then click **✅ I've Joined** to verify.
        """
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_join_channel_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    user_sessions[user_id] = {
        'step': 'main',
        'phone': '',
        'password': '',
        'platform': 'ck',
        'logged_in': False,
        'api_instance': None
    }
    
    saved_creds = get_user_credentials(user_id)
    auto_login = get_user_setting(user_id, 'auto_login', 1)
    
    if saved_creds and auto_login:
        user_sessions[user_id]['phone'] = saved_creds['phone']
        user_sessions[user_id]['password'] = saved_creds['password']
        user_sessions[user_id]['platform'] = saved_creds['platform']
        user_sessions[user_id]['api_instance'] = LotteryBot(saved_creds['platform'])
        await auto_login_user(update, context, user_id)
        return
    
    welcome_text = f"""
🎰 **Auto Lottery Bot** 🎯

Welcome {user.first_name}!

**🤖 Auto Bot Features:**
• 🎲 Random BIG Betting
• 🎯 Random SMALL Betting  
• 🔄 Random BIG/SMALL Betting
• 📈 Follow Bot (Follow Last Result)
• 📋 BS Formula Pattern Betting (B,S only)
• 🔮 Colour Formula Pattern Betting (G,R,V only)
• 📋 SL Layer Pattern Betting
• 📊 Bot Statistics Tracking
• ⚡ Auto Result Checking
• 🎯 Profit/Loss Targets
• 🔴🟢🟣 Colour Betting (RED, GREEN, VIOLET)

**Platform Support:**
• 🔐 CK Lottery
• 🔐 777 Big Win  
• 🔐 6 Lottery

**Manual Features:**
• 💰 Real-time Balance
• 📊 Game Results & History

Press **🤖 Run Bot** to start auto betting!
    """
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(user_id), parse_mode='Markdown')

async def auto_login_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str):
    """Auto login with saved credentials"""
    user_session = user_sessions.get(user_id)
    if not user_session:
        return
    
    loading_msg = await update.message.reply_text("🔄 Auto logging in...")
    
    try:
        success, message, token = await user_session['api_instance'].login(
            user_session['phone'], 
            user_session['password']
        )
        
        if success:
            user_session['logged_in'] = True
            user_session['step'] = 'main'
            
            balance = await user_session['api_instance'].get_balance()
            user_info = await user_session['api_instance'].get_user_info()
            user_id_display = user_info.get('userId', 'N/A')
            
            current_amount = get_current_bet_amount(user_id)
            bet_sequence = get_user_setting(user_id, 'bet_sequence', '100,300,700,1600,3200,7600,16000,32000')
            current_index = get_user_setting(user_id, 'current_bet_index', 0)
            
            bot_session = get_bot_session(user_id)
            
            platform_name = get_platform_name(user_session['platform'])
            
            success_text = f"""
✅ **Auto Login Successful!**

**Platform:** {platform_name}
**User ID:** {user_id_display}
**Account:** {user_session['phone']}
**Balance:** {balance:,.0f} K

**Bot Status:** {'🟢 RUNNING' if bot_session['is_running'] else '🔴 STOPPED'}
**Total Profit:** {bot_session['total_profit']:,} K

**Bet Sequence:** {bet_sequence}
**Current Bet:** {current_amount} K (Step {current_index + 1})
            """
            await loading_msg.edit_text(success_text, parse_mode='Markdown')
            await update.message.reply_text("Choose an option:", reply_markup=get_main_keyboard(user_id))
            
        else:
            await loading_msg.edit_text(f"❌ Auto login failed: {message}")
            await update.message.reply_text("Please login manually:", reply_markup=get_login_keyboard())
            
    except Exception as e:
        await loading_msg.edit_text(f"❌ Auto login error: {str(e)}")
        await update.message.reply_text("Please login manually:", reply_markup=get_login_keyboard())

def get_platform_name(platform_code):
    """Get platform display name"""
    platform_names = {
        'ck': 'CK Lottery',
        '777': '777 Big Win',
        '6': '6 Lottery'
    }
    return platform_names.get(platform_code, 'CK Lottery')

async def ck_login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start CK login process - IMPROVED VERSION"""
    user_id = str(update.effective_user.id)
    
    # Initialize user session if not exists
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'step': 'login',
            'phone': '',
            'password': '',
            'platform': 'ck',
            'logged_in': False,
            'api_instance': None
        }
    else:
        user_sessions[user_id]['step'] = 'login'
        user_sessions[user_id]['platform'] = 'ck'
    
    user_sessions[user_id]['api_instance'] = LotteryBot('ck')
    
    login_guide = """
🔐 **CK Lottery Login - Improved Version**

📝 **Login Instructions:**

1. Click '📝 Enter Phone' and send your phone number
   - Example: 91234567 (without 95 prefix)
   - Example: 987654321

2. Click '🔑 Enter Password' and send your password

3. Click '🚪 Login Now' to authenticate

✅ **Your credentials will be saved for auto login!**

🆘 **Troubleshooting:**
• Ensure phone number is correct
• Check your password
• Stable internet connection required
• If login fails, try again after 1 minute
    """
    await update.message.reply_text(login_guide, reply_markup=get_login_keyboard(), parse_mode='Markdown')
    
async def bigwin_login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start 777 BigWin login process"""
    user_id = str(update.effective_user.id)
    user_sessions[user_id]['step'] = 'login'
    user_sessions[user_id]['platform'] = '777'
    user_sessions[user_id]['api_instance'] = LotteryBot('777')
    
    login_guide = """
🔐 **777 Big Win Login**

Please follow these steps:

1. Click '📝 Enter Phone' and send your phone number
2. Click '🔑 Enter Password' and send your password  
3. Click '🚪 Login Now' to authenticate

**Your credentials will be saved for future use!**
    """
    await update.message.reply_text(login_guide, reply_markup=get_login_keyboard(), parse_mode='Markdown')

async def six_login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start 6 Lottery login process"""
    user_id = str(update.effective_user.id)
    user_sessions[user_id]['step'] = 'login'
    user_sessions[user_id]['platform'] = '6'
    user_sessions[user_id]['api_instance'] = LotteryBot('6')
    
    login_guide = """
🔐 **6 Lottery Login**

Please follow these steps:

1. Click '📝 Enter Phone' and send your phone number
2. Click '🔑 Enter Password' and send your password  
3. Click '🚪 Login Now' to authenticate

**Your credentials will be saved for future use!**
    """
    await update.message.reply_text(login_guide, reply_markup=get_login_keyboard(), parse_mode='Markdown')

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_session = user_sessions.get(user_id, {})
    
    if not user_session.get('logged_in'):
        await update.message.reply_text("❌ Please login first!")
        return
    
    try:
        balance = await user_session['api_instance'].get_balance()
        user_info = await user_session['api_instance'].get_user_info()
        user_id_display = user_info.get('userId', 'N/A')
        
        current_amount = get_current_bet_amount(user_id)
        bet_sequence = get_user_setting(user_id, 'bet_sequence', '100,300,700,1600,3200,7600,16000,32000')
        current_index = get_user_setting(user_id, 'current_bet_index', 0)
        
        platform_name = get_platform_name(user_session['platform'])
        
        balance_text = f"""
💰 **Account Information**

**Platform:** {platform_name}
**User ID:** {user_id_display}
**Balance:** {balance:,.0f} K
**Status:** 🟢 LOGGED IN

Last update: {datetime.now().strftime("%H:%M:%S")}
        """
        await update.message.reply_text(balance_text, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting balance: {str(e)}")

async def results_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_session = user_sessions.get(user_id, {})
    
    platform_name = get_platform_name(user_session.get('platform', 'ck'))
    
    try:
        if user_session.get('api_instance'):
            results = await user_session['api_instance'].get_recent_results(10)
        else:
            api = LotteryBot('ck')
            results = await api.get_recent_results(10)
        
        if not results:
            await update.message.reply_text("📊 No recent results available.")
            return
        
        results_text = f"📊 **Recent Game Results - {platform_name}**\n\n"
        for i, result in enumerate(results):
            issue_no = result.get('issueNumber', 'N/A')
            number = result.get('number', 'N/A')
            
            if number in ['0','1','2','3','4']:
                result_type = "SMALL"
            else:
                result_type = "BIG"
            
            number_str = str(number)
            if number_str in ['0', '5']:
                colour_emoji = "🟣"
            elif number_str in ['5','1', '3', '7', '9']:
                colour_emoji = "🟢"
            elif number_str in ['0','2', '4', '6', '8']:
                colour_emoji = "🔴"
            else:
                colour_emoji = "⚪"
            
            results_text += f"{i+1}. **{issue_no}** - {number} - {result_type} {colour_emoji}\n"
        

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        results_text += f"\n🕐 Last updated: {current_time}"
        
        await update.message.reply_text(results_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error getting results: {str(e)}")
        await update.message.reply_text(f"❌ Error getting results: {str(e)}")

async def my_bets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_session = user_sessions.get(user_id, {})
    
    if not user_session.get('logged_in'):
        await update.message.reply_text("❌ Please login first!")
        return
    
    try:
        platform = user_session.get('platform', 'ck')
        my_bets = get_bet_history(user_id, platform, 10)
        
        if not my_bets:
            await update.message.reply_text("📈 No bet history found.")
            return
        
        platform_name = get_platform_name(platform)
        
        bets_text = f"📈 **Your Recent Bets - {platform_name}**\n\n"
        for i, bet in enumerate(my_bets):
            platform_bet, issue, bet_type, amount, result, profit_loss, created_at = bet
            
            if result == "WIN":
                result_emoji = "🟢"
                total_win_amount = amount + profit_loss
                result_text = f"WIN (+{total_win_amount:,}K)"
            elif result == "LOSE":
                result_emoji = "🔴"
                result_text = f"LOSE (-{amount:,}K)"
            else:
                result_emoji = "🟡"
                result_text = "PENDING"
            
            time_str = created_at.split(' ')[1][:5] if ' ' in str(created_at) else str(created_at)[11:16]
            
            bets_text += f"{i+1}. **{issue}** - {bet_type} - {amount:,}K - {result_emoji} {result_text} \n"
        
        await update.message.reply_text(bets_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in my_bets_command: {e}")
        await update.message.reply_text("❌ Error getting bet history. Please try again.")

async def bet_red_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Place RED colour bet"""
    await place_colour_bet_handler(update, context, "RED")

async def bet_green_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Place GREEN colour bet"""
    await place_colour_bet_handler(update, context, "GREEN")

async def bet_violet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Place VIOLET colour bet"""
    await place_colour_bet_handler(update, context, "VIOLET")

async def place_colour_bet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, colour: str):
    """Handle colour bet placement with sequence management"""
    user_id = str(update.effective_user.id)
    user_session = user_sessions.get(user_id, {})
    
    if not user_session.get('logged_in'):
        await update.message.reply_text("❌ Please login first!")
        return
    
    current_issue = await user_session['api_instance'].get_current_issue()
    if not current_issue:
        await update.message.reply_text("❌ Cannot get current game issue. Please try again.")
        return
    
    if has_user_bet_on_issue(user_id, user_session['platform'], current_issue):
        await update.message.reply_text(
            f"⏳ **Wait for next period**\n\n"
            f"You have already placed a bet on issue **{current_issue}**.\n"
            f"Please wait for the next game period to place another bet.",
            parse_mode='Markdown'
        )
        return
    
    amount = get_current_bet_amount(user_id)
    bet_type = COLOUR_BET_TYPES[colour]
    colour_emoji = {"RED": "🔴", "GREEN": "🟢", "VIOLET": "🟣"}[colour]
    
    bet_sequence = get_user_setting(user_id, 'bet_sequence', '100,300,700,1600,3200,7600,16000,32000')
    current_index = get_user_setting(user_id, 'current_bet_index', 0)
    amounts = [int(x.strip()) for x in bet_sequence.split(',')]
    
    balance = await user_session['api_instance'].get_balance()
    if balance < amount:
        await update.message.reply_text(f"❌ Insufficient balance! You have {balance:,} K but need {amount:,} K")
        return
    
    platform_name = get_platform_name(user_session['platform'])
    
    loading_msg = await update.message.reply_text(
        f"🔄 Placing {colour_emoji} {colour} bet...\n"
        f"Platform: {platform_name}\n"
        f"Issue: {current_issue}\n"
        f"Amount: {amount:,} K (Step {current_index + 1}/{len(amounts)})\n"
        f"Sequence: {bet_sequence}"
    )
    
    try:
        success, message, issue_id, potential_profit = await user_session['api_instance'].place_bet(amount, bet_type)
        
        if success:
            bet_type_str = f"{colour_emoji} {colour}"
            save_pending_bet(user_id, user_session['platform'], issue_id, bet_type_str, amount)
            
            if user_id not in issue_checkers:
                asyncio.create_task(start_issue_checker(user_id, context))
            
            bet_text = f"""
✅ **Colour Bet Placed Successfully!**

**Platform:** {platform_name}
Issue: {issue_id}
Type: {colour_emoji} {colour}
Amount: {amount:,} K (Step {current_index + 1})
Sequence: {bet_sequence}

Time: {datetime.now().strftime("%H:%M:%S")}
            """
            await loading_msg.edit_text(bet_text, parse_mode='Markdown')
            
        else:
            await loading_msg.edit_text(f"❌ {colour} bet failed: {message}")
            
    except Exception as e:
        await loading_msg.edit_text(f"❌ {colour} bet error: {str(e)}")

async def bs_formula_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show BS Formula menu and set mode"""
    user_id = str(update.effective_user.id)
    patterns_data = get_formula_patterns(user_id)
    
    bs_pattern_text = patterns_data['bs_pattern'] if patterns_data['bs_pattern'] else "Not set"
    bs_current_index = patterns_data['bs_current_index']
    
    if patterns_data['bs_pattern']:
        bs_info = f"""
✅ **BS Formula Mode Activated**

• 📋 BS Formula - Follow BS Pattern (B,S only)

**Current BS Pattern:** {bs_pattern_text}
**Current Position:** {bs_current_index}

**Bot will now follow your BS Pattern:**
{bs_pattern_text}

**Note:** BS Formula uses only B (BIG) and S (SMALL) patterns.

Choose an option to manage your BS pattern:
        """
    else:
        bs_info = f"""
📋 **BS Formula Pattern Mode**

• 📋 BS Formula - Follow BS Pattern (B,S only)

**Current Status:** BS Pattern not set

**To use BS Formula Mode:**
1. Set your BS Pattern first (B,S only)
2. Bot will follow the pattern automatically
3. Pattern will loop until cleared

**How to create BS pattern:**
• Use B for BIG, S for SMALL ONLY
• Separate with commas: B,S,B,B
• **Only B and S allowed** - no colours

**Example BS Patterns:**
• B,S,B,B → BIG → SMALL → BIG → BIG
• S,S,B → SMALL → SMALL → BIG
• B,B,B,S → BIG → BIG → BIG → SMALL

Choose an option to get started:
        """
    
    await update.message.reply_text(bs_info, reply_markup=get_bs_pattern_keyboard(), parse_mode='Markdown')

async def set_bs_pattern_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set BS Pattern and activate BS Formula mode"""
    user_id = str(update.effective_user.id)
    user_sessions[user_id]['step'] = 'set_bs_pattern'
    
    await update.message.reply_text(
        "🔢 **Set BS Pattern for BS Formula Mode**\n\n"
        "• 📋 BS Formula - Follow BS Pattern (B,S only)\n\n"
        "Enter your BS pattern using ONLY B for BIG and S for SMALL:\n\n"
        "**Allowed characters:** B, S only\n"
        "**Examples:**\n"
        "• B,S,B,B\n"
        "• S,S,B\n"
        "• B,B,B,S\n\n"
        "The bot will follow this BS pattern sequentially in BS Formula mode.\n"
        "**Note:** Colour codes (R,G,V) are NOT allowed in BS Formula.\n\n"
        "Enter your BS pattern:"
    )

async def view_bs_pattern_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View current BS Pattern"""
    user_id = str(update.effective_user.id)
    patterns_data = get_formula_patterns(user_id)
    
    if patterns_data['bs_pattern']:
        pattern_list = [p.strip().upper() for p in patterns_data['bs_pattern'].split(',')]
        current_index = patterns_data['bs_current_index']
        
        pattern_display = ""
        for i, bet_type in enumerate(pattern_list):
            if i == current_index:
                pattern_display += f"**→ {bet_type}** "
            else:
                pattern_display += f"{bet_type} "
        
        await update.message.reply_text(
            f"👀 **Current BS Pattern**\n\n"
            f"• 📋 BS Formula - Follow BS Pattern (B,S only)\n\n"
            f"**BS Pattern:** {patterns_data['bs_pattern']}\n"
            f"**Current Position:** {current_index}\n"
            f"**Progress:** {pattern_display}\n\n"
            f"**Next bet:** {pattern_list[current_index] if current_index < len(pattern_list) else 'Pattern completed - will restart from beginning'}\n\n"
            f"Bot is following this BS pattern in BS Formula mode."
        )
    else:
        await update.message.reply_text(
            "❌ **No BS Pattern Set**\n\n"
            "• 📋 BS Formula - Follow BS Pattern (B,S only)\n\n"
            "BS Formula mode is active but no BS pattern is set.\n"
            "Please set a BS Pattern first to use this mode."
        )

async def clear_bs_pattern_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear BS Pattern"""
    user_id = str(update.effective_user.id)
    
    if clear_formula_patterns(user_id, 'bs'):
        await update.message.reply_text(
            "🗑️ **BS Pattern Cleared**\n\n"
            "• 📋 BS Formula - Follow BS Pattern (B,S only)\n\n"
            "BS Pattern has been cleared successfully!\n\n"
            "BS Formula mode is still active but no BS pattern is set.\n"
            "Set a new BS pattern to continue using BS Formula mode."
        )
    else:
        await update.message.reply_text("❌ Error clearing BS pattern.")

async def colour_formula_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Colour Formula menu and set mode"""
    user_id = str(update.effective_user.id)
    patterns_data = get_formula_patterns(user_id)
    
    colour_pattern_text = patterns_data['colour_pattern'] if patterns_data['colour_pattern'] else "Not set"
    colour_current_index = patterns_data['colour_current_index']
    
    if patterns_data['colour_pattern']:
        colour_info = f"""
🔮 **Colour Formula Mode Activated**

• 🔮 Colour Formula - Follow Colour Pattern (G,R,V only)

**Current Colour Pattern:** {colour_pattern_text}
**Current Position:** {colour_current_index}

**Bot will now follow your Colour Pattern:**
{colour_pattern_text}

**Note:** Colour Formula uses only G (GREEN), R (RED), and V (VIOLET) patterns.

Choose an option to manage your Colour pattern:
        """
    else:
        colour_info = f"""
🔮 **Colour Formula Pattern Mode**

• 🔮 Colour Formula - Follow Colour Pattern (G,R,V only)

**Current Status:** Colour Pattern not set

**To use Colour Formula Mode:**
1. Set your Colour Pattern first (G,R,V only)
2. Bot will follow the pattern automatically
3. Pattern will loop until cleared

**How to create Colour pattern:**
• Use G for GREEN, R for RED, V for VIOLET ONLY
• Separate with commas: G,R,V,R
• **Only G, R, and V allowed** - no BIG/SMALL

**Example Colour Patterns:**
• R,G,V → RED → GREEN → VIOLET
• R,R,G → RED → RED → GREEN
• G,V,R → GREEN → VIOLET → RED

Choose an option to get started:
        """
    
    await update.message.reply_text(colour_info, reply_markup=get_colour_pattern_keyboard(), parse_mode='Markdown')

async def set_colour_pattern_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set Colour Pattern and activate Colour Formula mode"""
    user_id = str(update.effective_user.id)
    user_sessions[user_id]['step'] = 'set_colour_pattern'
    
    await update.message.reply_text(
        "🔢 **Set Colour Pattern for Colour Formula Mode**\n\n"
        "• 🔮 Colour Formula - Follow Colour Pattern (G,R,V only)\n\n"
        "Enter your Colour pattern using ONLY:\n"
        "• G for 🟢 GREEN\n"  
        "• R for 🔴 RED\n"
        "• V for 🟣 VIOLET\n\n"
        "**Allowed characters:** G, R, V only\n"
        "**Examples:**\n"
        "• R,G,V,R\n"
        "• G,V,R\n"
        "• R,R,G\n\n"
        "The bot will follow this Colour pattern in Colour Formula mode.\n"
        "**Note:** BIG/SMALL codes (B,S) are NOT allowed in Colour Formula.\n\n"
        "Enter your Colour pattern:"
    )

async def view_colour_pattern_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View current Colour Pattern"""
    user_id = str(update.effective_user.id)
    patterns_data = get_formula_patterns(user_id)
    
    if patterns_data['colour_pattern']:
        pattern_list = [p.strip().upper() for p in patterns_data['colour_pattern'].split(',')]
        current_index = patterns_data['colour_current_index']
        
        pattern_display = ""
        colour_guide = ""
        
        for i, bet_type in enumerate(pattern_list):
            emoji = ""
            if bet_type == 'R':
                emoji = "🔴"
                bet_name = "RED"
            elif bet_type == 'G':
                emoji = "🟢" 
                bet_name = "GREEN"
            elif bet_type == 'V':
                emoji = "🟣"
                bet_name = "VIOLET"
            else:
                emoji = "❓"
                bet_name = "UNKNOWN"
                
            if i == current_index:
                pattern_display += f"**→ {emoji} {bet_type}** "
            else:
                pattern_display += f"{emoji} {bet_type} "
                
            colour_guide += f"• {bet_type} = {emoji} {bet_name}\n"
        
        next_bet = pattern_list[current_index] if current_index < len(pattern_list) else pattern_list[0]
        next_emoji = ""
        if next_bet == 'R':
            next_emoji = "🔴"
            next_name = "RED"
        elif next_bet == 'G':
            next_emoji = "🟢"
            next_name = "GREEN"
        elif next_bet == 'V':
            next_emoji = "🟣" 
            next_name = "VIOLET"
        else:
            next_emoji = "❓"
            next_name = "UNKNOWN"
        
        await update.message.reply_text(
            f"👀 **Current Colour Pattern**\n\n"
            f"• 🔮 Colour Formula - Follow Colour Pattern (G,R,V only)\n\n"
            f"**Colour Pattern:** {patterns_data['colour_pattern']}\n"
            f"**Current Position:** {current_index}\n"
            f"**Progress:** {pattern_display}\n\n"
            f"**Next bet:** {next_emoji} {next_name}\n\n"
            f"Colour Guide:\n{colour_guide}\n"
            f"Bot is following this Colour pattern in Colour Formula mode."
        )
    else:
        await update.message.reply_text(
            "❌ **No Colour Pattern Set**\n\n"
            "• 🔮 Colour Formula - Follow Colour Pattern (G,R,V only)\n\n"
            "Colour Formula mode is active but no Colour pattern is set.\n"
            "Please set a Colour Pattern first to use this mode."
        )

async def clear_colour_pattern_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear Colour Pattern"""
    user_id = str(update.effective_user.id)
    
    if clear_formula_patterns(user_id, 'colour'):
        await update.message.reply_text(
            "🗑️ **Colour Pattern Cleared**\n\n"
            "• 🔮 Colour Formula - Follow Colour Pattern (G,R,V only)\n\n"
            "Colour Pattern has been cleared successfully!\n\n"
            "Colour Formula mode is still active but no Colour pattern is set.\n"
            "Set a new Colour pattern to continue using Colour Formula mode."
        )
    else:
        await update.message.reply_text("❌ Error clearing Colour pattern.")

async def process_login(update: Update, context: ContextTypes.DEFAULT_TYPE, save_credentials=False):
    user_id = str(update.effective_user.id)
    user_session = user_sessions.get(user_id)
    
    if not user_session or not user_session.get('phone') or not user_session.get('password'):
        await update.message.reply_text(
            "❌ Please enter bot phone number and password first!",
            reply_markup=get_login_keyboard()
        )
        return
    
    loading_msg = await update.message.reply_text("🔄 Logging in... Please wait.")
    
    try:
        success, message, token = await user_session['api_instance'].login(user_session['phone'], user_session['password'])
        
        if success:
            user_session['logged_in'] = True
            user_session['step'] = 'main'
            
            if save_credentials:
                save_user_credentials(user_id, user_session['phone'], user_session['password'], user_session['platform'])
                save_user_setting(user_id, 'auto_login', 1)
                save_user_setting(user_id, 'platform', user_session['platform'])
            
            balance = await user_session['api_instance'].get_balance()
            user_info = await user_session['api_instance'].get_user_info()
            user_id_display = user_info.get('userId', 'N/A')
            
            current_amount = get_current_bet_amount(user_id)
            bet_sequence = get_user_setting(user_id, 'bet_sequence', '100,300,700,1600,3200,7600,16000,32000')
            current_index = get_user_setting(user_id, 'current_bet_index', 0)
            
            platform_name = get_platform_name(user_session['platform'])
            
            success_text = f"""
✅ **Login Successful!**

**Platform:** {platform_name}
**User ID:** {user_id_display}
**Account:** {user_session['phone']}
**Balance:** {balance:,.0f} K

**Bet Sequence:** {bet_sequence}
**Current Bet:** {current_amount} K (Step {current_index + 1})

{'✅ Credentials saved for auto login!' if save_credentials else ''}
            """
            await loading_msg.edit_text(success_text, parse_mode='Markdown')
            await update.message.reply_text("Choose an option:", reply_markup=get_main_keyboard(user_id))
            
        else:
            await loading_msg.edit_text(f"❌ Login failed: {message}")
            
    except Exception as e:
        await loading_msg.edit_text(f"❌ Login error: {str(e)}")

async def place_bet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, bet_type: int):
    """Handle bet placement"""
    user_id = str(update.effective_user.id)
    user_session = user_sessions.get(user_id, {})
    
    if not user_session.get('logged_in'):
        await update.message.reply_text("❌ Please login first!")
        return
    
    current_issue = await user_session['api_instance'].get_current_issue()
    if not current_issue:
        await update.message.reply_text("❌ Cannot get current game issue. Please try again.")
        return
    
    if has_user_bet_on_issue(user_id, user_session['platform'], current_issue):
        await update.message.reply_text(
            f"⏳ **Wait for next period**\n\n"
            f"You have already placed a bet on issue **{current_issue}**.\n"
            f"Please wait for the next game period to place another bet.",
            parse_mode='Markdown'
        )
        return
    
    amount = get_current_bet_amount(user_id)
    bet_type_str = "BIG 🎲" if bet_type == 13 else "SMALL 🎯"
    
    bet_sequence = get_user_setting(user_id, 'bet_sequence', '100,300,700,1600,3200,7600,16000,32000')
    current_index = get_user_setting(user_id, 'current_bet_index', 0)
    amounts = [int(x.strip()) for x in bet_sequence.split(',')]
    
    balance = await user_session['api_instance'].get_balance()
    if balance < amount:
        await update.message.reply_text(f"❌ Insufficient balance! You have {balance:,} K but need {amount:,} K")
        return
    
    platform_name = get_platform_name(user_session['platform'])
    
    loading_msg = await update.message.reply_text(
        f"🔄 Placing {bet_type_str} bet...\n"
        f"Platform: {platform_name}\n"
        f"Issue: {current_issue}\n"
        f"Amount: {amount:,} K (Step {current_index + 1}/{len(amounts)})\n"
        f"Sequence: {bet_sequence}"
    )
    
    try:
        success, message, issue_id, potential_profit = await user_session['api_instance'].place_bet(amount, bet_type)
        
        if success:
            save_pending_bet(user_id, user_session['platform'], issue_id, bet_type_str, amount)
            
            if user_id not in issue_checkers:
                asyncio.create_task(start_issue_checker(user_id, context))
            
            bet_text = f"""
✅ **Bet Placed Successfully!**

**Platform:** {platform_name}
**Bet Details:**
Issue: {issue_id}
Type: {bet_type_str}
Amount: {amount:,} K (Step {current_index + 1})
            """
            await loading_msg.edit_text(bet_text, parse_mode='Markdown')
            
        else:
            await loading_msg.edit_text(f"❌ Bet failed: {message}")
            
    except Exception as e:
        await loading_msg.edit_text(f"❌ Bet error: {str(e)}")

async def run_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start auto betting bot - COMPLETELY DISABLE SL LAYER FOR NORMAL BOT"""
    user_id = str(update.effective_user.id)
    user_session = user_sessions.get(user_id, {})
    
    if not user_session.get('logged_in'):
        await update.message.reply_text("❌ Please login first!")
        return
    
    if user_id in auto_betting_tasks:
        await update.message.reply_text("🤖 Bot is already running!")
        return
    
    try:
        balance = await user_session['api_instance'].get_balance()
        
        sl_pattern_data = get_sl_pattern(user_id)
        patterns_data = get_formula_patterns(user_id)
        
        # ✅ FIXED: COMPLETELY DISABLE SL LAYER FOR NORMAL BOT
        use_sl_layer = False
        
        # Only use SL Layer if user EXPLICITLY set a custom SL pattern
        if (sl_pattern_data['pattern'] and 
            sl_pattern_data['pattern'] != '1,2,3,4,5' and 
            (patterns_data['bs_pattern'] or patterns_data['colour_pattern']) and
            balance >= 30000):
            use_sl_layer = True
            print(f"🔧 DEBUG: SL LAYER ACTIVATED - User {user_id} has custom SL pattern")
        else:
            use_sl_layer = False
            print(f"🔧 DEBUG: NORMAL BOT MODE - User {user_id} has no custom SL pattern")
            
            # If user has default SL pattern, completely disable SL Layer
            if sl_pattern_data['pattern'] == '1,2,3,4,5':
                print(f"🔧 DEBUG: Default SL pattern detected - SL Layer COMPLETELY DISABLED")
        
        if use_sl_layer:
            # Run SL Bot
            await run_sl_bot_integrated(update, context, user_id)
            return
        else:
            # Run Normal Bot (COMPLETELY without SL Layer)
            if balance < 10000:
                await update.message.reply_text(
                    f"❌ **Insufficient Balance!**\n\n"
                    f"Minimum balance required: 10,000 K\n"
                    f"Your current balance: {balance:,} K\n\n"
                    f"Please top up your account to run the bot.",
                    parse_mode='Markdown'
                )
                return
    except Exception as e:
        logger.error(f"Error checking balance for bot start: {e}")
        await update.message.reply_text("❌ Error checking balance. Please try again.")
        return
    
    # ✅ Start NORMAL bot (COMPLETELY without SL Layer)
    auto_betting_tasks[user_id] = True
    waiting_for_results[user_id] = False
    
    # Reset processed issues when starting bot
    reset_processed_issues(user_id)
    
    reset_session_stats(user_id)
    save_bot_session(user_id, True)
    
    random_mode = get_user_setting(user_id, 'random_betting', 'bot')
    patterns_data = get_formula_patterns(user_id)
    
    # Determine mode text
    if patterns_data['bs_pattern']:
        mode_text = f"📋 BS Formula - {patterns_data['bs_pattern']}"
        mode_details = f"Following BS Pattern: {patterns_data['bs_pattern']}"
    elif patterns_data['colour_pattern']:
        mode_text = f"🔮 Colour Formula - {patterns_data['colour_pattern']}"
        mode_details = f"Following Colour Pattern: {patterns_data['colour_pattern']}"
    else:
        mode_text = {
            'big': "🎲 Random BIG Only",
            'small': "🎯 Random SMALL Only", 
            'bot': "🔄 Random BIG/SMALL",
            'follow': "📈 Follow Bot"
        }.get(random_mode, "🔄 Random BIG/SMALL")
        mode_details = mode_text
    
    # ✅ FIXED: Show clear SL Layer status
    sl_status = "🔴 COMPLETELY DISABLED"
    
    await update.message.reply_text(
        f"🤖 **Auto Bot Started!**\n\n"
        f"**Mode:** {mode_text}\n"
        f"**SL Layer:** {sl_status}\n"
        f"**Status:** 🟢 RUNNING\n\n"
        f"Bot will start placing bets automatically.\n"
        f"{mode_details}",
        parse_mode='Markdown'
    )
    
    asyncio.create_task(auto_betting_loop(user_id, context))
        
async def run_sl_bot_integrated(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str):
    """Run SL Bot when Run Bot button is pressed - FINAL FIXED"""
    user_session = user_sessions.get(user_id, {})
    
    # ✅ FIXED: Reset SL pattern but NOT bet sequence
    # save_user_setting(user_id, 'current_bet_index', 0)  # ❌ REMOVED: ဒီ line ကို ဖျက်လိုက်ပါ
    reset_sl_pattern(user_id)
    
    # Get current settings for display
    current_bet_index = get_user_setting(user_id, 'current_bet_index', 0)
    bet_sequence = get_user_setting(user_id, 'bet_sequence', '100,300,700,1600,3200,7600,16000,32000')
    amounts = [int(x.strip()) for x in bet_sequence.split(',')]
    current_amount = amounts[current_bet_index] if current_bet_index < len(amounts) else amounts[0]
    
    print(f"🔧 DEBUG: SL Bot Start - SL RESET ONLY")
    print(f"🔧 DEBUG: Bet index preserved at: {current_bet_index}")
    print(f"🔧 DEBUG: Starting bet: {current_amount}K")
    print(f"🔧 DEBUG: Sequence: {bet_sequence}")
    
    # ... rest of the function remains the same ...
    
    sl_pattern_data = get_sl_pattern(user_id)
    sl_session = get_sl_bet_session(user_id)
    
    print(f"🔧 DEBUG: SL Bot Start - SL: {sl_pattern_data['current_sl']}, Wait Mode: {sl_session['is_wait_mode']}")
    
    current_sl = sl_pattern_data['current_sl']
    should_be_wait_mode = current_sl >= 2
    
    if should_be_wait_mode and not sl_session['is_wait_mode']:
        print(f"🔧 DEBUG: Forcing WAIT mode for SL {current_sl}")
        save_sl_bet_session(user_id, True, '', '', 0, 0)
        sl_session = get_sl_bet_session(user_id)
    elif not should_be_wait_mode and sl_session['is_wait_mode']:
        print(f"🔧 DEBUG: Forcing BETTING mode for SL {current_sl}")
        save_sl_bet_session(user_id, False, '', '', 0, 0)
        sl_session = get_sl_bet_session(user_id)
    
    auto_betting_tasks[user_id] = True
    waiting_for_results[user_id] = False
    
    if user_id not in processed_issues:
        processed_issues[user_id] = set()
    
    mode_text = "🟢 WAIT BOT" if sl_session['is_wait_mode'] else "🔵 BETTING"
    
    pattern_list = [int(x.strip()) for x in sl_pattern_data['pattern'].split(',')]
    current_wait_loss_limit = pattern_list[sl_pattern_data['current_index']] if sl_pattern_data['current_index'] < len(pattern_list) else pattern_list[-1]
    
    if sl_session['is_wait_mode']:
        status_details = f"Waiting for {current_wait_loss_limit} losses before betting"
    else:
        status_details = f"Betting 3 times with BS/Colour Pattern"
    
    # ✅ FIXED: Bet sequence information ထည့်ပေးမယ်
    bet_sequence = get_user_setting(user_id, 'bet_sequence', '100,300,700,1600,3200,7600,16000,32000')
    current_amount = get_current_bet_amount(user_id)
    
    await update.message.reply_text(
        f"🤖 **SL Layer Bot Started!**\n\n"
        f"**BS/Colour Pattern Mode:** 🟢 Active\n"
        f"**SL Pattern:** {sl_pattern_data['pattern']}\n"
        f"**Starting at:** SL {sl_pattern_data['current_sl']}\n"
        f"**Mode:** {mode_text}\n"
        f"**Status:** {status_details}\n"
        f"**Bet Sequence:** {bet_sequence}\n"
        f"**Starting Bet:** {current_amount} K\n\n"
        f"**Bot Status:** 🟢 RUNNING\n\n"
        f"Bot will now start with {mode_text} mode for SL {sl_pattern_data['current_sl']}.",
        parse_mode='Markdown'
    )
    
    asyncio.create_task(sl_betting_loop(user_id, context))

async def stop_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop auto betting bot immediately"""
    user_id = str(update.effective_user.id)
    
    if user_id in auto_betting_tasks:
        del auto_betting_tasks[user_id]
    if user_id in waiting_for_results:
        del waiting_for_results[user_id]
    if user_id in issue_checkers:
        del issue_checkers[user_id]
    
    # Reset processed issues when bot stops
    reset_processed_issues(user_id)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM pending_bets WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    save_bot_session(user_id, False)
    
    sl_pattern_data = get_sl_pattern(user_id)
    patterns_data = get_formula_patterns(user_id)
    
    if sl_pattern_data['pattern'] and sl_pattern_data['pattern'] != '1,2,3,4,5' and (patterns_data['bs_pattern'] or patterns_data['colour_pattern']):
        bot_type = "SL Layer Bot"
        current_mode = f"SL {sl_pattern_data['current_sl']}"
    else:
        bot_type = "Auto Bot"
        current_mode = "Normal Mode"
    
    bot_session = get_bot_session(user_id)
    
    await update.message.reply_text(
        f"🛑 **{bot_type} Stopped!**\n\n"

        f"",
        parse_mode='Markdown'
    )

async def auto_betting_loop(user_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Main auto betting loop"""
    user_session = user_sessions.get(user_id, {})
    
    if not user_session.get('api_instance'):
        return
    
    last_issue = ""
    consecutive_failures = 0
    max_failures = 3
    
    while user_id in auto_betting_tasks:
        try:
            if waiting_for_results.get(user_id):
                await asyncio.sleep(5)
                continue
            
            current_issue = await user_session['api_instance'].get_current_issue()
            
            if current_issue and current_issue != last_issue:
                logger.info(f"New issue detected: {current_issue} for user {user_id}")
                
                await asyncio.sleep(3)
                
                if not has_user_bet_on_issue(user_id, user_session['platform'], current_issue):
                    await place_auto_bet(user_id, context, current_issue)
                    last_issue = current_issue
                    consecutive_failures = 0
                else:
                    logger.info(f"User {user_id} already bet on issue {current_issue}")
            
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Auto betting error for user {user_id}: {e}")
            consecutive_failures += 1
            if consecutive_failures >= max_failures:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text="❌ **Auto Bot Stopped - Too many errors!**",
                    parse_mode='Markdown'
                )
                if user_id in auto_betting_tasks:
                    del auto_betting_tasks[user_id]
                if user_id in waiting_for_results:
                    del waiting_for_results[user_id]
                save_bot_session(user_id, False)
            await asyncio.sleep(10)

async def check_targets(user_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Check if profit/loss targets are reached"""
    bot_session = get_bot_session(user_id)
    profit_target = get_user_setting(user_id, 'profit_target', 0)
    loss_target = get_user_setting(user_id, 'loss_target', 0)
    
    session_profit = bot_session['session_profit']
    session_loss = bot_session['session_loss']
    net_profit = session_profit - session_loss
    
    if profit_target > 0 and net_profit >= profit_target:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"🎯 **PROFIT TARGET REACHED!** 🎯\n\n"
                 f"Target: {profit_target:,} K\n"
                 f"Achieved: {net_profit:,} K\n\n"
                 f"Bot has been stopped automatically.",
            parse_mode='Markdown'
        )
        if user_id in auto_betting_tasks:
            del auto_betting_tasks[user_id]
        if user_id in waiting_for_results:
            del waiting_for_results[user_id]
        save_bot_session(user_id, False)
        return True
    
    if loss_target > 0 and session_loss >= loss_target:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"🎯 **LOSS TARGET REACHED!** 🎯\n\n"
                 f"Target: {loss_target:,} K\n"
                 f"Achieved: {session_loss:,} K\n\n"
                 f"Bot has been stopped automatically.",
            parse_mode='Markdown'
        )
        if user_id in auto_betting_tasks:
            del auto_betting_tasks[user_id]
        if user_id in waiting_for_results:
            del waiting_for_results[user_id]
        save_bot_session(user_id, False)
        return True
    
    return False

async def get_bet_type_based_on_mode(random_mode, api_instance):
    """Get bet type based on random mode (helper function)"""
    if random_mode == 'big':
        return 13, "BIG 🎲"
    elif random_mode == 'small':
        return 14, "SMALL 🎯"
    elif random_mode == 'follow':
        return await get_follow_bet_type(api_instance)
    else:
        bet_type = random.choice([13, 14])
        return bet_type, "BIG 🎲" if bet_type == 13 else "SMALL 🎯"

async def place_auto_bet(user_id: str, context: ContextTypes.DEFAULT_TYPE, issue: str):
    """Place automatic bet - COMPLETELY DISABLE SL LAYER"""
    user_session = user_sessions.get(user_id, {})
    
    if not user_session.get('logged_in'):
        return
    
    if await check_targets(user_id, context):
        return
    
    waiting_for_results[user_id] = True
    
    random_mode = get_user_setting(user_id, 'random_betting', 'bot')
    
    patterns_data = get_formula_patterns(user_id)
    sl_pattern_data = get_sl_pattern(user_id)
    
    # ✅ FIXED: COMPLETELY DISABLE SL LAYER FOR NORMAL BOT
    use_sl_layer = False
    
    # Only use SL Layer if user EXPLICITLY set custom SL pattern
    if (sl_pattern_data['pattern'] and 
        sl_pattern_data['pattern'] != '1,2,3,4,5' and 
        (patterns_data['bs_pattern'] or patterns_data['colour_pattern'])):
        use_sl_layer = True
    else:
        use_sl_layer = False
    
    # ❌ NEVER use SL Layer in normal bot mode
    if use_sl_layer:
        print(f"❌ DEBUG: SL Layer detected but not used in normal bot mode")
        use_sl_layer = False
    
    bet_type = None
    bet_type_str = ""
    current_pattern_index = 0
    formula_type = ""
    
    # Check which formula pattern is active
    if patterns_data['bs_pattern']:
        next_bet, current_pattern_index = get_next_formula_bet(user_id, 'bs')
        formula_type = "BS Formula"
        if next_bet:
            if next_bet == 'B':
                bet_type = 13
                bet_type_str = f"BIG 🎲 ({formula_type})"
            elif next_bet == 'S':
                bet_type = 14  
                bet_type_str = f"SMALL 🎯 ({formula_type})"
            else:
                bet_type, bet_type_str = await get_bet_type_based_on_mode(random_mode, user_session['api_instance'])
        else:
            bet_type, bet_type_str = await get_bet_type_based_on_mode(random_mode, user_session['api_instance'])
    elif patterns_data['colour_pattern']:
        next_bet, current_pattern_index = get_next_formula_bet(user_id, 'colour')
        formula_type = "Colour Formula"
        if next_bet:
            if next_bet == 'R':
                bet_type = 10
                bet_type_str = f"🔴 RED ({formula_type})"
            elif next_bet == 'G':
                bet_type = 11
                bet_type_str = f"🟢 GREEN ({formula_type})"
            elif next_bet == 'V':
                bet_type = 12
                bet_type_str = f"🟣 VIOLET ({formula_type})"
            else:
                bet_type, bet_type_str = await get_bet_type_based_on_mode(random_mode, user_session['api_instance'])
        else:
            bet_type, bet_type_str = await get_bet_type_based_on_mode(random_mode, user_session['api_instance'])
    else:
        bet_type, bet_type_str = await get_bet_type_based_on_mode(random_mode, user_session['api_instance'])
    
    amount = get_current_bet_amount(user_id)
    
    balance = await user_session['api_instance'].get_balance()
    
    if amount > 0 and balance < amount:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"❌ **Auto Bot Stopped - Insufficient Balance!**\n\nNeed: {amount:,} K\nAvailable: {balance:,} K",
            parse_mode='Markdown'
        )
        if user_id in auto_betting_tasks:
            del auto_betting_tasks[user_id]
        if user_id in waiting_for_results:
            del waiting_for_results[user_id]
        return
    
    try:
        success, message, issue_id, potential_profit = await user_session['api_instance'].place_bet(amount, bet_type)
        
        if success:
            # ✅ FIXED: Never add SL information to bet type string in normal mode
            clean_bet_type_str = bet_type_str.replace('(SL', '(').replace('SL Layer', 'Normal')
            
            save_pending_bet(user_id, user_session['platform'], issue_id, clean_bet_type_str, amount)
            update_bot_stats(user_id)
            
            if user_id not in issue_checkers:
                asyncio.create_task(start_issue_checker(user_id, context))
            
            pattern_info = ""
            if patterns_data['bs_pattern']:
                pattern_list = [p.strip().upper() for p in patterns_data['bs_pattern'].split(',')]
                pattern_info = f"\n**📋 BS Formula:** {patterns_data['bs_pattern']}\n**Position:** {current_pattern_index + 1}/{len(pattern_list)}"
            elif patterns_data['colour_pattern']:
                pattern_list = [p.strip().upper() for p in patterns_data['colour_pattern'].split(',')]
                pattern_info = f"\n**🔮 Colour Formula:** {patterns_data['colour_pattern']}\n**Position:** {current_pattern_index + 1}/{len(pattern_list)}"
            
            bet_sequence = get_user_setting(user_id, 'bet_sequence', '100,300,700,1600,3200,7600,16000,32000')
            current_index = get_user_setting(user_id, 'current_bet_index', 0)
            
            bet_text = f"""
🤖 **Auto Bet Placed!**

🎲🎲🎲🎲🎲🎲🎲🎲🎲🎲🎲🎲🎲
**Issue:** {issue_id}
**Type:** {clean_bet_type_str}
**Amount:** {amount:,} K (Step {current_index + 1})
{pattern_info}
            """
            await context.bot.send_message(chat_id=int(user_id), text=bet_text, parse_mode='Markdown')
            
        else:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=f"❌ **Auto Bet Failed**\n\nError: {message}",
                parse_mode='Markdown'
            )
            waiting_for_results[user_id] = False
            
    except Exception as e:
        logger.error(f"Auto bet placement error: {e}")
        waiting_for_results[user_id] = False

async def get_follow_bet_type(api_instance):
    """Get bet type for FOLLOW BOT mode based on last result"""
    try:
        results = await api_instance.get_recent_results(1)
        if not results:
            bet_type = random.choice([13, 14])
            return bet_type, "BIG 🎲" if bet_type == 13 else "SMALL 🎯"
        
        last_result = results[0]
        number = last_result.get('number', '')
        
        if number in ['0','1','2','3','4']:
            return 14, "SMALL 🎯 (Follow)"
        else:
            return 13, "BIG 🎲 (Follow)"
            
    except Exception as e:
        logger.error(f"Error getting follow bet type: {e}")
        bet_type = random.choice([13, 14])
        return bet_type, "BIG 🎲" if bet_type == 13 else "SMALL 🎯"

async def bot_settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot settings with localized keyboard"""
    try:
        user_id = str(update.effective_user.id)
        language = get_user_language(user_id)
        
        random_mode = get_user_setting(user_id, 'random_betting', 'bot')
        bet_sequence = get_user_setting(user_id, 'bet_sequence', '100,300,700,1600,3200,7600,16000,32000')
        current_index = get_user_setting(user_id, 'current_bet_index', 0)
        current_amount = get_current_bet_amount(user_id)
        
        bot_session = get_bot_session(user_id)
        
        patterns_data = get_formula_patterns(user_id)
        
        bs_pattern_status = f" {patterns_data['bs_pattern']} (pos: {patterns_data['bs_current_index']})" if patterns_data['bs_pattern'] else "❌ Not set"
        colour_pattern_status = f" {patterns_data['colour_pattern']} (pos: {patterns_data['colour_current_index']})" if patterns_data['colour_pattern'] else "❌ Not set"
        
        sl_pattern_data = get_sl_pattern(user_id)
        sl_pattern_active = bool(sl_pattern_data['pattern'] and sl_pattern_data['pattern'] != '1,2,3,4,5')
        
        # ✅ AUTO DETECTION STATUS
        sl_activation_conditions = []
        if sl_pattern_active:
            sl_activation_conditions.append("✅ SL Pattern Set")
        else:
            sl_activation_conditions.append("❌ SL Pattern Not Set")
            
        if patterns_data['bs_pattern'] or patterns_data['colour_pattern']:
            sl_activation_conditions.append("✅ BS/Colour Pattern Set")
        else:
            sl_activation_conditions.append("❌ BS/Colour Pattern Not Set")
            
        balance = 0
        try:
            user_session = user_sessions.get(user_id, {})
            if user_session.get('api_instance'):
                balance = await user_session['api_instance'].get_balance()
                if balance >= 30000:
                    sl_activation_conditions.append("✅ Sufficient Balance")
                else:
                    sl_activation_conditions.append(f"❌ Low Balance ({balance:,}K/30,000K)")
        except:
            sl_activation_conditions.append("⚪ Balance Unknown")
        
        sl_layer_status = "🟢 READY (Will activate on bot start)" if (
            sl_pattern_active and 
            (patterns_data['bs_pattern'] or patterns_data['colour_pattern']) and
            balance >= 30000
        ) else "🔴 NOT READY"
        
        sl_pattern_status = f"✅ {sl_pattern_data['pattern']} (SL {sl_pattern_data['current_sl']})" if sl_pattern_active else "❌ Not set"
        
        # Determine current mode
        if patterns_data['bs_pattern']:
            mode_text = "📋 BS Formula"
        elif patterns_data['colour_pattern']:
            mode_text = "🔮 Colour Formula"
        else:
            mode_text = {
                'big': "🎲 Random BIG Only",
                'small': "🎯 Random SMALL Only", 
                'bot': "🔄 Random Bot",
                'follow': "📈 Follow Bot"
            }.get(random_mode, "🔄 Random BIG/SMALL")
        
        profit_target = get_user_setting(user_id, 'profit_target', 0)
        loss_target = get_user_setting(user_id, 'loss_target', 0)
        
        target_info = ""
        if profit_target > 0:
            target_info += f"• Profit Target: {profit_target:,} K\n"
        else:
            target_info += "• Profit Target: Not set\n"
            
        if loss_target > 0:
            target_info += f"• Loss Target: {loss_target:,} K\n"
        else:
            target_info += "• Loss Target: Not set\n"
        
        settings_text = f"""
 **{get_localized_message('bot_settings', language)}**

**Current Settings:**
• Betting Mode: {mode_text}
• Bet Sequence: {bet_sequence}
• Current Bet: {current_amount} K (Step {current_index + 1})
• BS Pattern: {bs_pattern_status}
• Colour Pattern: {colour_pattern_status}
• SL Pattern: {sl_pattern_status}
• SL Layer: {sl_layer_status}
• Bot Status: {'🟢 RUNNING' if bot_session['is_running'] else '🔴 STOPPED'}

**SL Layer Activation Conditions:**
{chr(10).join(sl_activation_conditions)}

**Target Settings:**
{target_info}

**Bot Statistics:**
• Session Profit: {bot_session['session_profit']:,} K
• Session Loss: {bot_session['session_loss']:,} K
• Net Profit: {bot_session['session_profit'] - bot_session['session_loss']:,} K

**Auto Detection System:**
• SL Layer activates automatically when all conditions are met
• Otherwise, Normal Bot runs automatically
• No manual switching needed!

Choose your betting mode:
    """
        await update.message.reply_text(settings_text, reply_markup=get_bot_settings_keyboard(user_id), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in bot_settings_command: {e}")
        await update.message.reply_text("❌ Error loading bot settings. Please try again.")

async def set_random_big(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set random mode to BIG only - DISABLE SL LAYER"""
    user_id = str(update.effective_user.id)
    save_user_setting(user_id, 'random_betting', 'big')
    clear_formula_patterns(user_id)  # Clear both patterns
    save_sl_pattern(user_id, '1,2,3,4,5')
    
    await update.message.reply_text(
        "✅ **Random Mode Set**\n\n"
        "• 🎲 Random BIG - Always bet BIG\n\n"
        "Bot will now always bet BIG in auto mode.\n"
        "❌ SL Layer has been disabled (BS/Colour Pattern mode required)."
    )

async def set_random_small(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set random mode to SMALL only - DISABLE SL LAYER"""
    user_id = str(update.effective_user.id)
    save_user_setting(user_id, 'random_betting', 'small')
    clear_formula_patterns(user_id)  # Clear both patterns
    save_sl_pattern(user_id, '1,2,3,4,5')
    
    await update.message.reply_text(
        "✅ **Random Mode Set**\n\n"
        "• 🎯 Random SMALL - Always bet SMALL\n\n"
        "Bot will now always bet SMALL in auto mode.\n"
        "❌ SL Layer has been disabled (BS/Colour Pattern mode required)."
    )

async def set_random_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set random mode to bot BIG and SMALL - DISABLE SL LAYER"""
    user_id = str(update.effective_user.id)
    save_user_setting(user_id, 'random_betting', 'bot')
    clear_formula_patterns(user_id)  # Clear both patterns
    save_sl_pattern(user_id, '1,2,3,4,5')
    
    await update.message.reply_text(
        "✅ **Random Mode Set**\n\n"
        "• 🔄 Random Bot - Random BIG/SMALL\n\n"
        "Bot will now randomly choose between BIG and SMALL in auto mode.\n"
        "❌ SL Layer has been disabled (BS/Colour Pattern mode required)."
    )

async def set_follow_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set random mode to FOLLOW BOT - DISABLE SL LAYER"""
    user_id = str(update.effective_user.id)
    save_user_setting(user_id, 'random_betting', 'follow')
    clear_formula_patterns(user_id)  # Clear both patterns
    save_sl_pattern(user_id, '1,2,3,4,5')
    
    await update.message.reply_text(
        "✅ **Random Mode Set**\n\n"
        "• 📈 Follow Bot - Follow Last Result\n\n"
        "Bot will now follow the last game result in auto mode.\n"
        "❌ SL Layer has been disabled (BS/Colour Pattern mode required)."
    )

async def show_bot_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics"""
    user_id = str(update.effective_user.id)
    bot_session = get_bot_session(user_id)
    
    stats_text = f"""
📊 **Bot Statistics**

**Session Data:**
• Session Profit: {bot_session['session_profit']:,} K
• Session Loss: {bot_session['session_loss']:,} K
• Net Profit: {bot_session['session_profit'] - bot_session['session_loss']:,} K
• Status: {'🟢 RUNNING' if bot_session['is_running'] else '🔴 STOPPED'}

*Session statistics reset when bot starts*
    """
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def reset_bot_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset bot statistics"""
    user_id = str(update.effective_user.id)
    reset_session_stats(user_id)
    await update.message.reply_text("✅ Bot session statistics reset to zero!")

async def set_profit_target_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set profit target"""
    user_id = str(update.effective_user.id)
    user_sessions[user_id]['step'] = 'set_profit_target'
    
    current_target = get_user_setting(user_id, 'profit_target', 0)
    
    await update.message.reply_text(
        f"🎯 **Set Profit Target**\n\n"
        f"Current target: {current_target:,} K\n\n"
        "Please enter the profit target amount (in K):\n"
        "Example: 1000 (for 1000 K profit target)\n"
        "Enter 0 to disable profit target"
    )

async def set_loss_target_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set loss target"""
    user_id = str(update.effective_user.id)
    user_sessions[user_id]['step'] = 'set_loss_target'
    
    current_target = get_user_setting(user_id, 'loss_target', 0)
    
    await update.message.reply_text(
        f"🎯 **Set Loss Target**\n\n"
        f"Current target: {current_target:,} K\n\n"
        "Please enter the loss target amount (in K):\n"
        "Example: 500 (for 500 K loss target)\n"
        "Enter 0 to disable loss target"
    )

async def reset_targets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset all targets"""
    user_id = str(update.effective_user.id)
    
    save_user_setting(user_id, 'profit_target', 0)
    save_user_setting(user_id, 'loss_target', 0)
    
    await update.message.reply_text(
        "✅ All targets have been reset!\n\n"
        "Profit Target: 0 K (disabled)\n"
        "Loss Target: 0 K (disabled)\n\n"
        "Bot will now run continuously until manually stopped."
    )

async def sl_layer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show SL Layer menu with AUTO ACTIVATION info"""
    user_id = str(update.effective_user.id)
    
    sl_pattern_data = get_sl_pattern(user_id)
    sl_session = get_sl_bet_session(user_id)
    patterns_data = get_formula_patterns(user_id)
    
    pattern_text = sl_pattern_data['pattern']
    current_sl = sl_pattern_data['current_sl']
    
    bs_pattern_active = bool(patterns_data['bs_pattern'])
    colour_pattern_active = bool(patterns_data['colour_pattern'])
    
    # ✅ AUTO ACTIVATION STATUS
    activation_status = []
    ready_for_sl = True
    
    if not sl_pattern_data['pattern'] or sl_pattern_data['pattern'] == '1,2,3,4,5':
        activation_status.append("❌ SL Pattern not set")
        ready_for_sl = False
    else:
        activation_status.append("✅ SL Pattern ready")
        
    if not bs_pattern_active and not colour_pattern_active:
        activation_status.append("❌ BS/Colour Pattern not set")
        ready_for_sl = False
    else:
        activation_status.append("✅ BS/Colour Pattern ready")
    
    balance = 0
    try:
        user_session = user_sessions.get(user_id, {})
        if user_session.get('api_instance'):
            balance = await user_session['api_instance'].get_balance()
            if balance >= 30000:
                activation_status.append("✅ Sufficient balance")
            else:
                activation_status.append(f"❌ Low balance ({balance:,}K/30,000K)")
                ready_for_sl = False
    except:
        activation_status.append("⚪ Balance unknown")
        ready_for_sl = False
    
    if not bs_pattern_active and not colour_pattern_active:
        sl_info = f"""
📋 **SL Layer Bot System**

🎯 **Auto Activation System**

**How it works:**
1. Set your SL Pattern here
2. Set BS Pattern or Colour Pattern in Bot Settings  
3. Ensure balance ≥ 30,000K
4. Press **🤖 Run Bot**
5. System automatically chooses SL Layer or Normal Bot

**Current Status:**
{chr(10).join(activation_status)}

**SL Layer will activate automatically when all conditions are met!**
        """
    else:
        active_pattern_type = "BS Formula" if bs_pattern_active else "Colour Formula"
        active_pattern = patterns_data['bs_pattern'] if bs_pattern_active else patterns_data['colour_pattern']
        
        overall_status = "🟢 READY FOR SL LAYER" if ready_for_sl else "🔴 NOT READY"
        
        sl_info = f"""
📋 **SL Layer Bot System** - {overall_status}

**{active_pattern_type} Mode:** 🟢 Active - {active_pattern}
**SL Layer:** {'🟢 Will Auto-Activate' if ready_for_sl else '🔴 Cannot Activate'}

**Activation Status:**
{chr(10).join(activation_status)}

**Current SL Pattern:** {pattern_text}
**Current SL Level:** {current_sl}

**Auto Detection:**
• When you press **🤖 Run Bot**:
• System checks all conditions automatically
• If ready → SL Layer activates
• If not ready → Normal Bot runs
• No manual switching needed!

Manage your SL Pattern:
    """
    
    await update.message.reply_text(sl_info, reply_markup=get_sl_layer_keyboard(), parse_mode='Markdown')
    
def get_next_sl_action(user_id):
    """Get description of next action in SL system"""
    sl_pattern_data = get_sl_pattern(user_id)
    sl_session = get_sl_bet_session(user_id)
    
    pattern_list = [int(x.strip()) for x in sl_pattern_data['pattern'].split(',')]
    current_sl = sl_pattern_data['current_sl']
    
    if sl_session['is_wait_mode']:
        current_wait_loss = sl_pattern_data['wait_loss_count']
        wait_limit = pattern_list[sl_pattern_data['current_index']] if sl_pattern_data['current_index'] < len(pattern_list) else pattern_list[-1]
        
        return f"**WAIT BOT MODE - SL {current_sl}**\nWaiting for {current_wait_loss}/{wait_limit} losses → Then bet 3 times"
    
    current_sl = sl_pattern_data['current_sl']
    bet_count = sl_pattern_data['bet_count']
    
    if bet_count < 3:
        return f"**BETTING MODE - SL {current_sl}**\nBetting {bet_count}/3 times → Complete 3 bets to move to next SL"
    else:
        next_sl_index = (sl_pattern_data['current_index'] + 1) % len(pattern_list)
        next_sl = pattern_list[next_sl_index]
        next_mode = "WAIT BOT" if next_sl >= 2 else "BETTING"
        return f"**BETTING MODE - SL {current_sl}**\nCompleted 3 bets → Moving to SL {next_sl} ({next_mode} mode)"

async def set_sl_pattern_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set SL Pattern - WITH AUTO DETECTION EXPLANATION"""
    user_id = str(update.effective_user.id)
    patterns_data = get_formula_patterns(user_id)
    
    if not patterns_data['bs_pattern'] and not patterns_data['colour_pattern']:
        await update.message.reply_text(
            "❌ **Cannot Set SL Pattern**\n\n"
            "SL Layer requires BS Formula or Colour Formula mode to be active.\n\n"
            "Please first:\n"
            "1. Go to **Bot Settings**\n" 
            "2. Click **📋 BS Formula** or **🔮 Colour Formula**\n"
            "3. Set a **BS Pattern** or **Colour Pattern**\n"
            "4. Then come back to set SL Pattern\n\n"
            "✅ **Auto Detection System:**\n"
            "• SL Layer will activate automatically when you run bot\n"
            "• All conditions must be met: SL Pattern + BS/Colour Pattern + 30,000K balance\n"
            "• Otherwise, Normal Bot mode will run automatically"
        )
        return
    
    user_sessions[user_id]['step'] = 'set_sl_pattern'
    
    current_pattern = get_sl_pattern(user_id)['pattern']
    
    await update.message.reply_text(
        f"🔢 **Set SL Pattern**\n\n"
        f"Current pattern: {current_pattern}\n\n"
        "Enter your SL pattern (comma separated numbers 1-5):\n"
        "Example: 2,1,3 (Starts from SL 2 with WAIT BOT)\n"
        "Example: 2,1 (Starts from SL 2 with WAIT BOT)\n"
        "Example: 1,2,3 (Starts from SL 1 with BETTING)\n\n"
      
    )

async def view_sl_pattern_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View current SL Pattern"""
    user_id = str(update.effective_user.id)
    sl_pattern_data = get_sl_pattern(user_id)
    sl_session = get_sl_bet_session(user_id)
    patterns_data = get_formula_patterns(user_id)
    
    pattern_text = sl_pattern_data['pattern']
    current_sl = sl_pattern_data['current_sl']
    current_index = sl_pattern_data['current_index']
    wait_loss_count = sl_pattern_data['wait_loss_count']
    bet_count = sl_pattern_data['bet_count']
    
    pattern_list = [int(x.strip()) for x in pattern_text.split(',')]
    
    pattern_display = ""
    for i, wait_limit in enumerate(pattern_list):
        if i == current_index:
            pattern_display += f"**→ SL{i+1}({wait_limit}L)** "
        else:
            pattern_display += f"SL{i+1}({wait_limit}L) "
    
    mode_status = "🟢 WAIT MODE" if sl_session['is_wait_mode'] else f"🔵 SL {current_sl} MODE"
    
    bs_status = "🟢 Active" if patterns_data['bs_pattern'] else "🔴 Inactive"
    colour_status = "🟢 Active" if patterns_data['colour_pattern'] else "🔴 Inactive"
    
    await update.message.reply_text(
        f"👀 **Current SL Pattern**\n\n"
        f"**BS Pattern Mode:** {bs_status}\n"
        f"**Colour Pattern Mode:** {colour_status}\n"
        f"**SL Pattern:** {pattern_text}\n"
        f"**Current Mode:** {mode_status}\n"
        f"**Progress:**{pattern_display}\n\n"
        f"**Current Stats:**\n"
        f"• Wait Loss Count: {wait_loss_count}/{pattern_list[current_index] if current_index < len(pattern_list) else pattern_list[-1]}\n"
        f"• Bet Count: {bet_count}/3\n\n"
        f"**Next Action:**\n"
        f"{get_next_sl_action(user_id)}",
        parse_mode='Markdown'
    )

async def reset_sl_pattern_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset SL Pattern to initial state"""
    user_id = str(update.effective_user.id)
    
    if reset_sl_pattern(user_id):
        save_sl_bet_session(user_id, False, '', '', 0, 0)
        await update.message.reply_text(
            "🔄 **SL Pattern Reset!**\n\n"
            "SL Pattern has been reset to initial state.\n"
            "Starting from SL 1 with current pattern."
        )
    else:
        await update.message.reply_text("❌ Error resetting SL pattern.")

async def sl_bot_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show SL Bot statistics"""
    await view_sl_pattern_command(update, context)

async def sl_betting_loop(user_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Main SL betting loop"""
    user_session = user_sessions.get(user_id, {})
    
    if not user_session.get('api_instance'):
        return
    
    last_issue = ""
    consecutive_failures = 0
    max_failures = 3
    
    while user_id in auto_betting_tasks:
        try:
            if await check_targets(user_id, context):
                break
                
            if waiting_for_results.get(user_id):
                # ✅ NEW: Increase wait time when waiting for results
                await asyncio.sleep(5)
                continue
            
            current_issue = await user_session['api_instance'].get_current_issue()
            
            if current_issue and current_issue != last_issue:
                logger.info(f"New issue detected: {current_issue} for user {user_id} in SL Bot")
                
                # ✅ NEW: Add delay to ensure result messages are processed
                await asyncio.sleep(5)
                
                if not has_user_bet_on_issue(user_id, user_session['platform'], current_issue):
                    await place_sl_bet_new_logic(user_id, context, current_issue)
                    last_issue = current_issue
                    consecutive_failures = 0
                else:
                    logger.info(f"User {user_id} already bet on issue {current_issue} in SL Bot")
            
            # ✅ NEW: Increase polling interval to allow message display
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"SL betting error for user {user_id}: {e}")
            consecutive_failures += 1
            if consecutive_failures >= max_failures:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text="❌ **SL Bot Stopped - Too many errors!**",
                    parse_mode='Markdown'
                )
                if user_id in auto_betting_tasks:
                    del auto_betting_tasks[user_id]
                if user_id in waiting_for_results:
                    del waiting_for_results[user_id]
            await asyncio.sleep(10)


            
    
async def check_sl_bet_result(user_id: str, context: ContextTypes.DEFAULT_TYPE, issue: str, bet_type_str: str, amount: int, platform: str, result: str, profit_loss: int):
    """Check and process SL bet results with PROPER BET COUNT UPDATE"""
    try:
        print(f"🔧 DEBUG: SL Bet Result Check Started")
        print(f"🔧 DEBUG: Issue: {issue}, User: {user_id}, Result: {result}")
        
        # Mark as processed immediately to prevent duplicates
        if user_id not in processed_issues:
            processed_issues[user_id] = set()
        processed_issues[user_id].add(issue)
        
        sl_pattern_data = get_sl_pattern(user_id)
        sl_session = get_sl_bet_session(user_id)
        
        current_sl = sl_pattern_data['current_sl']
        current_bet_count = sl_pattern_data['bet_count']  # Current bet count before update
        
        print(f"🔧 DEBUG: SL: {current_sl}, Current Bet Count: {current_bet_count}, Wait Mode: {sl_session['is_wait_mode']}")
        
        bot_session = get_bot_session(user_id)
        total_profit = bot_session['total_profit']
        
        # ✅ FIXED: Get current bet sequence information
        current_main_index = get_user_setting(user_id, 'current_bet_index', 0)
        bet_sequence = get_user_setting(user_id, 'bet_sequence', '100,300,700,1600,3200,7600,16000,32000')
        amounts = [int(x.strip()) for x in bet_sequence.split(',')]
        
        print(f"🔧 DEBUG: BEFORE Sequence Update")
        print(f"🔧 DEBUG: Current Index: {current_main_index}")
        print(f"🔧 DEBUG: Current Amount: {amounts[current_main_index] if current_main_index < len(amounts) else amounts[0]}K")
        
        # ✅ FIXED: Sequence Management - ONLY update for betting mode based on result
        sequence_info = ""
        if not sl_session['is_wait_mode']:
            if result == "WIN":
                new_main_index = update_bet_sequence(user_id, "WIN")
                next_amount = amounts[0]  # Win ရင် အစပြန်စ
                sequence_info = f"**Sequence Reset:** Back to Step 1"
                print(f"🔧 DEBUG: WIN - Sequence reset to Step 1 (10K)")
            else:
                new_main_index = update_bet_sequence(user_id, "LOSE")
                next_amount = amounts[new_main_index] if new_main_index < len(amounts) else amounts[0]
                next_step_display = new_main_index + 1
                sequence_info = f"**Next Bet:** Step {next_step_display} ({next_amount:,} K)"
                print(f"🔧 DEBUG: LOSE - Next bet will be: Step {next_step_display} ({next_amount}K)")
        else:
            # Wait Bot Mode မှာ sequence မပြောင်းရပါ
            sequence_info = "**Status:** Wait Bot Mode - Sequence Frozen"
            print(f"🔧 DEBUG: ⚠️ WAIT BOT MODE - Sequence frozen")
        
        # ✅ FIXED: PROPER BET COUNT UPDATE LOGIC
        new_bet_count = current_bet_count
        
        if not sl_session['is_wait_mode']:  # Only update bet count in BETTING mode
            if result == "WIN":
                # Win ရင် Bet Count ကို 0 ပြန်စမယ် (ဘာလို့လဲဆိုတော့ Win ရင် SL Change ဖြစ်မယ်)
                new_bet_count = 0
                print(f"🔧 DEBUG: WIN - Bet Count reset to 0 (SL Change will happen)")
            else:
                # Loss ရင် Bet Count တိုးမယ်
                new_bet_count = current_bet_count + 1
                print(f"🔧 DEBUG: LOSE - Bet Count updated: {current_bet_count} -> {new_bet_count}")
        
        # ✅ FIXED: Update SL pattern with new bet count
        update_sl_pattern(user_id, bet_count=new_bet_count)
        
        # Process the result message based on mode
        if sl_session['is_wait_mode']:
            # Wait Bot Mode logic...
            wait_loss_count = sl_pattern_data['wait_loss_count']
            pattern_list = [int(x.strip()) for x in sl_pattern_data['pattern'].split(',')]
            current_index = sl_pattern_data['current_index']
            current_wait_loss_limit = pattern_list[current_index] if current_index < len(pattern_list) else pattern_list[-1]
            
            if result == "WIN":
                update_sl_pattern(user_id, wait_loss_count=0)
                
                total_win_amount = amount + profit_loss
                
                # WIN Message for Wait Bot Mode
                win_message = f"""
🟢 **WAIT BOT WIN**

                """
                
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=win_message,
                    parse_mode='Markdown'
                )
                
            else:
                new_wait_loss_count = wait_loss_count + 1
                update_sl_pattern(user_id, wait_loss_count=new_wait_loss_count)
                
                # LOSS Message for Wait Bot Mode
                loss_message = f"""
🔴 **WAIT BOT LOSS**
                """
                
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=loss_message,
                    parse_mode='Markdown'
                )
                
                if new_wait_loss_count >= current_wait_loss_limit:
                    # ✅ FIXED: Wait limit reached, switch to BETTING mode
                    save_sl_bet_session(user_id, False, '', '', 0, 0)
                    update_sl_pattern(user_id, bet_count=0, wait_loss_count=0)
                    
                    transition_message = f"""
🔵 **Wait Loss Limit Reached!**

                    """
                    
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text=transition_message,
                        parse_mode='Markdown'
                    )
        
        else:
            # Betting Mode logic...
            if result == "WIN":
                pattern_list = [int(x.strip()) for x in sl_pattern_data['pattern'].split(',')]
                first_sl = pattern_list[0]
                is_wait_mode = first_sl >= 2
                
                # ✅ FIXED: Win ရင် SL Change ဖြစ်မယ်
                save_sl_bet_session(user_id, is_wait_mode, '', '', 0, 0)
                update_sl_pattern(user_id, current_sl=first_sl, current_index=0, wait_loss_count=0, bet_count=0)
                
                patterns_data = get_formula_patterns(user_id)
                if patterns_data['bs_pattern']:
                    update_formula_pattern_index(user_id, 'bs', 0)
                if patterns_data['colour_pattern']:
                    update_formula_pattern_index(user_id, 'colour', 0)
                
                total_win_amount = amount + profit_loss
                
                mode_text = "WAIT BOT" if is_wait_mode else "BETTING"
                
                # ✅ FIXED: WIN Message for Betting Mode
                win_message = f"""
🟢 **BET RESULT UPDATE**

**Total Profit:** {total_profit:,} K 🏆🏆🏆

                """
                
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=win_message,
                    parse_mode='Markdown'
                )
                
            else:
                # ✅ FIXED: LOSS Message for Betting Mode with CORRECT bet count
                loss_message = f"""
🔴 **BET RESULT UPDATE**

**Total Profit:** {total_profit:,} K 🏆🏆🏆
                """
                
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=loss_message,
                    parse_mode='Markdown'
                )
                
                # ✅ FIXED: SL Level Change - Check if completed 3 bets
                if new_bet_count >= 3:
                    pattern_list = [int(x.strip()) for x in sl_pattern_data['pattern'].split(',')]
                    current_index = sl_pattern_data['current_index']
                    new_index = (current_index + 1) % len(pattern_list)
                    new_sl = pattern_list[new_index]
                    
                    is_wait_mode = new_sl >= 2
                    save_sl_bet_session(user_id, is_wait_mode, '', '', 0, 0)
                    update_sl_pattern(user_id, current_sl=new_sl, current_index=new_index, wait_loss_count=0, bet_count=0)
                    
                    mode_text = "WAIT BOT" if is_wait_mode else "BETTING"
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text=f"\n\n"

                             f"",
                        parse_mode='Markdown'
                    )
        
        await check_targets(user_id, context)
        
        if user_id in waiting_for_results:
            waiting_for_results[user_id] = False
            
        print(f"🔧 DEBUG: SL Bet Result Processing Completed - New Bet Count: {new_bet_count}")
            
    except Exception as e:
        logger.error(f"Error processing SL bet result: {e}")
        print(f"❌ DEBUG: SL Bet Result Error: {e}")
        if user_id in waiting_for_results:
            waiting_for_results[user_id] = False


async def start_issue_checker(user_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Start checking for new issues to get bet results"""
    if user_id in issue_checkers:
        return
    
    issue_checkers[user_id] = True
    logger.info(f"Started issue checker for user {user_id}")
    
    try:
        user_session = user_sessions.get(user_id, {})
        if not user_session.get('api_instance'):
            return
            
        last_checked_issue = await user_session['api_instance'].get_current_issue()
        
        while user_id in issue_checkers:
            await asyncio.sleep(5)
            
            current_issue = await user_session['api_instance'].get_current_issue()
            
            if current_issue and current_issue != last_checked_issue:
                logger.info(f"Issue changed from {last_checked_issue} to {current_issue}, checking results for user {user_id}")
                
                await check_pending_bets(user_id, context, last_checked_issue)
                
                sl_session = get_sl_bet_session(user_id)
                if sl_session['is_wait_mode']:
                    await check_wait_bot_result(user_id, context, last_checked_issue)
                
                last_checked_issue = current_issue
                
    except Exception as e:
        logger.error(f"Issue checker error for user {user_id}: {e}")
    finally:
        if user_id in issue_checkers:
            del issue_checkers[user_id]

async def check_pending_bets(user_id: str, context: ContextTypes.DEFAULT_TYPE, previous_issue: str):
    """Check results for pending bets when issue changes"""
    try:
        user_session = user_sessions.get(user_id, {})
        platform = user_session.get('platform', 'ck')
        
        pending_bets = get_pending_bets(user_id, platform)
        
        for bet_platform, issue, bet_type_str, amount in pending_bets:
            if issue == previous_issue and bet_platform == platform:
                await check_single_bet_result(user_id, context, issue, bet_type_str, amount, platform)
                
    except Exception as e:
        logger.error(f"Error checking pending bets for user {user_id}: {e}")

async def check_single_bet_result(user_id: str, context: ContextTypes.DEFAULT_TYPE, issue: str, bet_type_str: str, amount: int, platform: str):
    """Check result for a single bet with PROPER SL BET IDENTIFICATION"""
    try:
        print(f"🔧 DEBUG: Single Bet Result Check - Issue: {issue}, User: {user_id}, Bet Type: {bet_type_str}")
        
        # Check if already processed
        if user_id in processed_issues and issue in processed_issues[user_id]:
            print(f"🔧 DEBUG: Issue {issue} already processed for user {user_id}, skipping...")
            return
            
        user_session = user_sessions.get(user_id, {})
        
        if not user_session.get('api_instance'):
            print(f"❌ DEBUG: No API instance for user {user_id}")
            return
            
        results = await user_session['api_instance'].get_recent_results(5)
        bet_result = "UNKNOWN"
        profit_loss = 0
        total_win_amount = 0
        number = ""
        actual_result = ""
        
        for result in results:
            if result.get('issueNumber') == issue:
                number = result.get('number', 'N/A')
                colour = result.get('colour', '').upper()
                
                print(f"🔧 DEBUG: Found result for issue {issue} - Number: {number}, Colour: {colour}")
                
                if "BIG" in bet_type_str:
                    user_bet_type = "BIG"
                    if number in ['5','6','7','8','9']:
                        actual_result = "BIG"
                        bet_result = "WIN"
                    else:
                        actual_result = "SMALL"
                        bet_result = "LOSE"
                elif "SMALL" in bet_type_str:
                    user_bet_type = "SMALL"
                    if number in ['0','1','2','3','4']:
                        actual_result = "SMALL"
                        bet_result = "WIN"
                    else:
                        actual_result = "BIG"
                        bet_result = "LOSE"
                elif "RED" in bet_type_str:
                    user_bet_type = "RED"
                    if number in ['0','2', '4', '6', '8']:
                        actual_result = "RED"
                        bet_result = "WIN"
                    else:
                        actual_result = "OTHER"
                        bet_result = "LOSE"
                elif "GREEN" in bet_type_str:
                    user_bet_type = "GREEN"
                    if number in ['5','1', '3', '7', '9']:
                        actual_result = "GREEN"
                        bet_result = "WIN"
                    else:
                        actual_result = "OTHER"
                        bet_result = "LOSE"
                elif "VIOLET" in bet_type_str:
                    user_bet_type = "VIOLET"
                    if number in ['0', '5']:
                        actual_result = "VIOLET"
                        bet_result = "WIN"
                    else:
                        actual_result = "OTHER"
                        bet_result = "LOSE"
                else:
                    user_bet_type = "UNKNOWN"
                    actual_result = "UNKNOWN"
                    bet_result = "UNKNOWN"
                
                if bet_result == "WIN":
                    if "RED" in bet_type_str or "GREEN" in bet_type_str or "VIOLET" in bet_type_str:
                        profit_amount = int(amount * 1.5)
                        profit_loss = profit_amount
                        total_win_amount = amount + profit_amount
                    else:
                        profit_amount = int(amount * 0.96)
                        profit_loss = profit_amount
                        total_win_amount = amount + profit_amount
                    update_bot_stats(user_id, profit_amount)
                else:
                    profit_loss = -amount
                    update_bot_stats(user_id, -amount)
                
                print(f"🔧 DEBUG: Bet Result Determined - Result: {bet_result}, Profit/Loss: {profit_loss}")
                break
        
        if bet_result == "UNKNOWN":
            print(f"🔧 DEBUG: No result found for issue {issue}")
            return
            
        # ✅ FIXED: Save bet history and remove pending bet
        save_bet_history(user_id, platform, issue, bet_type_str, amount, bet_result, profit_loss)
        remove_pending_bet(user_id, platform, issue)
        
        # ✅ FIXED: IMPROVED SL BET IDENTIFICATION
        is_sl_bet = False

        # Check multiple ways to identify SL bets
        if any(keyword in bet_type_str for keyword in ["(SL", "SL ", "SL Layer", "SL Bot"]):
            is_sl_bet = True
            print(f"🔧 DEBUG: ✅ SL BET IDENTIFIED - '{bet_type_str}' contains SL keyword")
        elif user_id in auto_betting_tasks:
            # Additional check: if user is in SL bot mode
            sl_pattern_data = get_sl_pattern(user_id)
            if sl_pattern_data['pattern'] and sl_pattern_data['pattern'] != '1,2,3,4,5':
                is_sl_bet = True
                print(f"🔧 DEBUG: ✅ SL BET IDENTIFIED - User has active SL pattern")
        else:
            print(f"🔧 DEBUG: ⚠️ NORMAL BET IDENTIFIED - '{bet_type_str}'")
        
        if is_sl_bet:
            print(f"🔧 DEBUG: This is an SL bet, calling SL bet result handler")
            # Call SL bet result handler for processing
            await check_sl_bet_result(user_id, context, issue, bet_type_str, amount, platform, bet_result, profit_loss)
        else:
            # Normal bet processing
            sl_session = get_sl_bet_session(user_id)
            
            # ✅ FIXED: Wait Bot Mode မှာ bet sequence မပြောင်းရပါ
            if not sl_session['is_wait_mode']:
                # Betting Mode မှာသာ bet sequence update လုပ်ပါ
                current_index = get_user_setting(user_id, 'current_bet_index', 0)
                new_index = update_bet_sequence(user_id, bet_result)
                print(f"🔧 DEBUG: Normal Bet - Updated index from {current_index} to {new_index}")
            else:
                # Wait Bot Mode မှာ bet sequence မပြောင်းရပါ
                current_index = get_user_setting(user_id, 'current_bet_index', 0)
                print(f"🔧 DEBUG: ⚠️ WAIT BOT MODE - Bet sequence FROZEN at index {current_index}")
            
            platform_name = get_platform_name(platform)
            
            # Normal bet result message
            if bet_result == "WIN":
                result_emoji = "🟢"
                result_text = "WIN"
                profit_text = f"+{profit_loss:,} K"
                sequence_info = f"**Sequence Reset:** Back to Step 1"
                win_details = f"**Total Win:** {total_win_amount:,} K"
            else:
                result_emoji = "🔴"
                result_text = "LOSE" 
                profit_text = f"-{amount:,} K"
                
                # Wait Bot Mode မှာ sequence info မပြရပါ
                if sl_session['is_wait_mode']:
                    sequence_info = "**Status:** Wait Bot Mode - Sequence Frozen"
                else:
                    current_index = get_user_setting(user_id, 'current_bet_index', 0)
                    bet_sequence = get_user_setting(user_id, 'bet_sequence', '100,300,700,1600,3200,7600,16000,32000')
                    amounts = [int(x.strip()) for x in bet_sequence.split(',')]
                    next_amount = amounts[current_index] if current_index < len(amounts) else amounts[0]
                    sequence_info = f"**Next Bet:** Step {current_index + 1} ({next_amount:,} K)"
                win_details = ""
            
            bot_session = get_bot_session(user_id)
            
            result_message = f"""
{result_emoji} **BET RESULT UPDATE**

**Total Profit:** {bot_session['total_profit']:,} K🏆🏆🏆
            """
            
            await context.bot.send_message(chat_id=int(user_id), text=result_message, parse_mode='Markdown')
            
            # ✅ NEW: Wait for user to read the message
            await asyncio.sleep(3)
            
            # Mark as processed AFTER sending message
            if user_id not in processed_issues:
                processed_issues[user_id] = set()
            processed_issues[user_id].add(issue)
        
        if user_id in waiting_for_results:
            waiting_for_results[user_id] = False
        
        print(f"🔧 DEBUG: Single Bet Result Processing Completed - Issue: {issue}")
        
    except Exception as e:
        logger.error(f"Error checking single bet result: {e}")
        print(f"❌ DEBUG: Single Bet Result Error: {e}")
        if user_id in waiting_for_results:
            waiting_for_results[user_id] = False




async def place_sl_bet_new_logic(user_id: str, context: ContextTypes.DEFAULT_TYPE, issue: str):
    """Place bet according to NEW SL logic with PROPER BET TYPE STRING"""
    user_session = user_sessions.get(user_id, {})
    
    if not user_session.get('logged_in'):
        return
    
    if user_id not in auto_betting_tasks:
        return
    
    if await check_targets(user_id, context):
        return
    
    waiting_for_results[user_id] = True
    
    sl_pattern_data = get_sl_pattern(user_id)
    sl_session = get_sl_bet_session(user_id)
    patterns_data = get_formula_patterns(user_id)
    
    current_sl = sl_pattern_data['current_sl']
    current_bet_count = sl_pattern_data['bet_count']  # Current bet count
    wait_loss_count = sl_pattern_data['wait_loss_count']
    
    pattern_list = [int(x.strip()) for x in sl_pattern_data['pattern'].split(',')]
    current_wait_loss_limit = pattern_list[sl_pattern_data['current_index']] if sl_pattern_data['current_index'] < len(pattern_list) else pattern_list[-1]
    
    # ✅ FIXED: Get current step from user settings
    current_main_index = get_user_setting(user_id, 'current_bet_index', 0)
    bet_sequence = get_user_setting(user_id, 'bet_sequence', '100,300,700,1600,3200,7600,16000,32000')
    amounts = [int(x.strip()) for x in bet_sequence.split(',')]
    
    # ✅ FIXED: Ensure index is within bounds
    if current_main_index < len(amounts):
        current_amount = amounts[current_main_index]
        current_step_display = current_main_index + 1
    else:
        # If index is out of bounds, reset to first amount
        current_amount = amounts[0] if amounts else 100
        save_user_setting(user_id, 'current_bet_index', 0)
        current_main_index = 0
        current_step_display = 1
    
    print(f"🔧 DEBUG: 🎯 SL BOT BET PLACEMENT")
    print(f"🔧 DEBUG: Wait Mode: {sl_session['is_wait_mode']}")
    print(f"🔧 DEBUG: Current Bet Count: {current_bet_count}")
    print(f"🔧 DEBUG: Current Amount: {current_amount} K")
    print(f"🔧 DEBUG: SL: {current_sl}")
    
    # ✅ FIXED: Wait Bot Mode မှာ Bet sequence ကို မပြောင်းလဲပါ
    if sl_session['is_wait_mode']:
        print(f"🔧 DEBUG: ⚠️ WAIT BOT MODE - No actual betting")
        
        # Wait Bot Mode မှာ bet sequence ကို မပြောင်းလဲပါ
        sequence_info = "**Status:** Wait Bot Mode - Sequence Frozen"
        print(f"🔧 DEBUG: ⚠️ WAIT BOT MODE - Sequence frozen")
        
        # Determine which pattern to use
        if patterns_data['bs_pattern']:
            next_bet, current_pattern_index = get_next_formula_bet(user_id, 'bs')
            formula_type = "BS Formula"
        elif patterns_data['colour_pattern']:
            next_bet, current_pattern_index = get_next_formula_bet(user_id, 'colour')
            formula_type = "Colour Formula"
        else:
            next_bet = None
            formula_type = "Auto"
        
        if next_bet:
            if next_bet == 'B':
                # ✅ FIXED: Add SL information to bet type string for identification
                bet_type_str = f"BIG 🎲 ({formula_type} - SL {current_sl})"
            elif next_bet == 'S':
                bet_type_str = f"SMALL 🎯 ({formula_type} - SL {current_sl})"
            elif next_bet == 'R':
                bet_type_str = f"🔴 RED ({formula_type} - SL {current_sl})"
            elif next_bet == 'G':
                bet_type_str = f"🟢 GREEN ({formula_type} - SL {current_sl})"
            elif next_bet == 'V':
                bet_type_str = f"🟣 VIOLET ({formula_type} - SL {current_sl})"
            else:
                bet_type_str = f"UNKNOWN ({formula_type} - SL {current_sl})"
        else:
            bet_type, fallback_str = await get_bet_type_based_on_mode('bot', user_session['api_instance'])
            # ✅ FIXED: Add SL information to bet type string for identification
            bet_type_str = f"{fallback_str} (SL {current_sl})"
        
        # Save pending bet for result checking (amount = 0 for wait mode)
        save_pending_bet(user_id, user_session['platform'], issue, bet_type_str, 0)
        
        if user_id not in issue_checkers:
            asyncio.create_task(start_issue_checker(user_id, context))
        
        mode_text = "🟢 WAIT BOT"
        
        pattern_info = ""
        if patterns_data['bs_pattern']:
            pattern_list_bs = [p.strip().upper() for p in patterns_data['bs_pattern'].split(',')]
            pattern_info = f"\n**📋 BS Formula:** {patterns_data['bs_pattern']}\n**Position:** {current_pattern_index + 1}/{len(pattern_list_bs)}"
        elif patterns_data['colour_pattern']:
            pattern_list_colour = [p.strip().upper() for p in patterns_data['colour_pattern'].split(',')]
            pattern_info = f"\n**🔮 Colour Formula:** {patterns_data['colour_pattern']}\n**Position:** {current_pattern_index + 1}/{len(pattern_list_colour)}"
        
        # Wait Bot Mode Message
        bet_text = f"""
🤖 **SL Bot - Wait Mode**

💤💤💤💤💤💤💤💤💤💤💤💤
**Issue:** {issue}
**Type:** {bet_type_str.split('(')[0].strip()} 🎯
**Wait Loss Count:** {wait_loss_count}/{current_wait_loss_limit}
**Mode:** {mode_text} (SL {current_sl})
{pattern_info}
        """
        
        await context.bot.send_message(chat_id=int(user_id), text=bet_text, parse_mode='Markdown')
        
        # ✅ FIXED: Wait Bot Mode မှာ waiting_for_results ကို False ပြန်လုပ်ပါ
        waiting_for_results[user_id] = False
    
    else:
        # Betting Mode - Actual betting
        bet_type = None
        bet_type_str = ""
        current_pattern_index = 0
        formula_type = ""
        
        # Determine which pattern to use
        if patterns_data['bs_pattern']:
            next_bet, current_pattern_index = get_next_formula_bet(user_id, 'bs')
            formula_type = "BS Formula"
        elif patterns_data['colour_pattern']:
            next_bet, current_pattern_index = get_next_formula_bet(user_id, 'colour')
            formula_type = "Colour Formula"
        else:
            next_bet = None
            formula_type = "Auto"
        
        if next_bet:
            if next_bet == 'B':
                bet_type = 13
                # ✅ FIXED: Add SL information to bet type string for identification
                bet_type_str = f"BIG 🎲 ({formula_type} - SL {current_sl})"
            elif next_bet == 'S':
                bet_type = 14
                bet_type_str = f"SMALL 🎯 ({formula_type} - SL {current_sl})"
            elif next_bet == 'R':
                bet_type = 10
                bet_type_str = f"🔴 RED ({formula_type} - SL {current_sl})"
            elif next_bet == 'G':
                bet_type = 11
                bet_type_str = f"🟢 GREEN ({formula_type} - SL {current_sl})"
            elif next_bet == 'V':
                bet_type = 12
                bet_type_str = f"🟣 VIOLET ({formula_type} - SL {current_sl})"
            else:
                bet_type, fallback_str = await get_bet_type_based_on_mode('bot', user_session['api_instance'])
                bet_type_str = f"{fallback_str} (SL {current_sl})"
        else:
            bet_type, fallback_str = await get_bet_type_based_on_mode('bot', user_session['api_instance'])
            bet_type_str = f"{fallback_str} (SL {current_sl})"
        
        # ✅ FIXED: Use current_amount from sequence (NO reset)
        amount = current_amount
        
        balance = await user_session['api_instance'].get_balance()
        
        if amount > 0 and balance < amount:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=f"❌ **SL Bot Stopped - Insufficient Balance!**\n\nNeed: {amount:,} K\nAvailable: {balance:,} K",
                parse_mode='Markdown'
            )
            if user_id in auto_betting_tasks:
                del auto_betting_tasks[user_id]
            if user_id in waiting_for_results:
                del waiting_for_results[user_id]
            return
        
        try:
            success, message, issue_id, potential_profit = await user_session['api_instance'].place_bet(amount, bet_type)
            
            if success:
                # ✅ FIXED: Save with proper SL identification in bet type string
                save_pending_bet(user_id, user_session['platform'], issue_id, bet_type_str, amount)
                update_bot_stats(user_id)
                
                if user_id not in issue_checkers:
                    asyncio.create_task(start_issue_checker(user_id, context))
                
                mode_text = f"🔵 SL {current_sl}"
                
                pattern_info = ""
                if patterns_data['bs_pattern']:
                    pattern_list_bs = [p.strip().upper() for p in patterns_data['bs_pattern'].split(',')]
                    pattern_info = f"\n**📋 BS Formula:** {patterns_data['bs_pattern']}\n**Position:** {current_pattern_index + 1}/{len(pattern_list_bs)}"
                elif patterns_data['colour_pattern']:
                    pattern_list_colour = [p.strip().upper() for p in patterns_data['colour_pattern'].split(',')]
                    pattern_info = f"\n**🔮 Colour Formula:** {patterns_data['colour_pattern']}\n**Position:** {current_pattern_index + 1}/{len(pattern_list_colour)}"
                
                # ✅ FIXED: Update the bet message to show CORRECT bet count
                # Next bet count will be current_bet_count + 1 (after this bet)
                next_bet_count = current_bet_count + 1
                
                # Betting Mode Message
                bet_text = f"""
🤖 **SL Bot - Active Bet**

🎲🎲🎲🎲🎲🎲🎲🎲🎲🎲🎲🎲🎲
**Issue:** {issue_id}
**Amount:** {amount:,} K
**Type:** {bet_type_str}
**Mode:** {mode_text}
**Bet Count:** {next_bet_count}/3
{pattern_info}
                """
                
                await context.bot.send_message(chat_id=int(user_id), text=bet_text, parse_mode='Markdown')
                
            else:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=f"❌ **SL Bot Bet Failed**\n\nError: {message}",
                    parse_mode='Markdown'
                )
                waiting_for_results[user_id] = False
                
        except Exception as e:
            logger.error(f"SL bet placement error: {e}")
            waiting_for_results[user_id] = False

async def force_wait_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force switch to Wait Bot mode - FIXED VERSION"""
    user_id = str(update.effective_user.id)
    
    patterns_data = get_formula_patterns(user_id)
    if not patterns_data['bs_pattern'] and not patterns_data['colour_pattern']:
        await update.message.reply_text(
            "❌ **Cannot Force Wait Bot**\n\n"
            "BS Formula or Colour Formula mode is required for SL Layer.\n\n"
            "Please first:\n"
            "1. Go to **Bot Settings**\n"
            "2. Click **📋 BS Formula** or **🔮 Colour Formula**\n"
            "3. Set a **BS Pattern** or **Colour Pattern**\n"
            "4. Then try again"
        )
        return
    
    if user_id in auto_betting_tasks:
        del auto_betting_tasks[user_id]
    if user_id in waiting_for_results:
        del waiting_for_results[user_id]
    
    save_sl_pattern(user_id, "2,1,3")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO sl_patterns 
        (user_id, pattern, current_sl, current_index, wait_loss_count, bet_count)
        VALUES (?, ?, ?, ?, 0, 0)
    ''', (user_id, "2,1,3", 2, 0))
    
    cursor.execute('''
        INSERT OR REPLACE INTO sl_bet_sessions 
        (user_id, is_wait_mode, wait_bet_type, wait_issue, wait_amount, wait_total_profit)
        VALUES (?, 1, '', '', 0, 0)
    ''', (user_id,))
    
    conn.commit()
    conn.close()
    
    # ✅ FIXED: Reset bet sequence to start from 10K
    save_user_setting(user_id, 'current_bet_index', 0)
    
    bet_sequence = get_user_setting(user_id, 'bet_sequence', '100,300,700,1600,3200,7600,16000,32000')
    
    await update.message.reply_text(
        "🔄 **Force Reset to Wait Bot Mode**\n\n"
        "✅ SL Pattern: 2,1,3\n"
        "✅ Starting from: SL 2\n" 
        "✅ Mode: 🟢 WAIT BOT\n"
        "✅ Wait Loss Count: 0/2\n"
        f"✅ **Starting Bet:** 10 K\n"
        f"✅ **Bet Sequence:** {bet_sequence}\n\n"
        "**Bot will now:**\n"
        "1. Wait for 2 consecutive losses\n"
        "2. Then bet 3 times with BS/Colour Pattern\n"
        "3. **Start betting from 10K**\n\n"
        "Now press **🤖 Run Bot** to start in Wait Bot mode.",
        parse_mode='Markdown'
    )

# Language Functions
async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show language selection menu"""
    user_id = str(update.effective_user.id)
    
    # Get current language setting
    current_language = get_user_language(user_id)
    
    language_info = f"""
🌐 **Choose Your Language**

**Current Language:** {current_language.title()}

Please select your preferred language:

• 🇺🇸 English - English language
• 🇲🇲 Burmese - မြန်မာစာ  
• 🇨🇳 Chinese - 中文
• 🇹🇭 Thailand - ภาษาไทย
• 🇵🇰 Pakistan - اردو

Select your language below:
    """
    
    await update.message.reply_text(language_info, reply_markup=get_language_keyboard(), parse_mode='Markdown')

async def set_english_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set language to English"""
    user_id = str(update.effective_user.id)
    save_user_setting(user_id, 'language', 'english')
    
    await update.message.reply_text(
        "✅ **Language set to English** 🇺🇸\n\n"
        "All bot messages will now be displayed in English.",
        reply_markup=get_main_keyboard(user_id)
    )

async def set_burmese_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set language to Burmese"""
    user_id = str(update.effective_user.id)
    save_user_setting(user_id, 'language', 'burmese')
    
    await update.message.reply_text(
        "✅ **ဘာသာစကား ပြောင်းလဲပြီးပါပြီ** 🇲🇲\n\n"
        "ဘော့သတင်းစကားအားလုံးကို မြန်မာဘာသာဖြင့် ပြသပေးပါမည်။",
        reply_markup=get_main_keyboard(user_id)
    )

async def set_chinese_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set language to Chinese"""
    user_id = str(update.effective_user.id)
    save_user_setting(user_id, 'language', 'chinese')
    
    await update.message.reply_text(
        "✅ **语言已设置为中文** 🇨🇳\n\n"
        "所有机器人消息现在将以中文显示。",
        reply_markup=get_main_keyboard(user_id)
    )

async def set_thai_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set language to Thai"""
    user_id = str(update.effective_user.id)
    save_user_setting(user_id, 'language', 'thai')
    
    await update.message.reply_text(
        "✅ **ตั้งค่าภาษาเป็นไทยแล้ว** 🇹🇭\n\n"
        "ข้อความบอททั้งหมดจะแสดงเป็นภาษาไทย",
        reply_markup=get_main_keyboard(user_id)
    )

async def set_pakistan_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set language to Pakistan/Urdu"""
    user_id = str(update.effective_user.id)
    save_user_setting(user_id, 'language', 'urdu')
    
    await update.message.reply_text(
        "✅ **زبان اردو میں تبدیل کر دی گئی** 🇵🇰\n\n"
        "تمام بوٹ کے پیغامات اب اردو میں دکھائے جائیں گے۔",
        reply_markup=get_main_keyboard(user_id)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    language = get_user_language(user_id)
    
    if not get_channel_status(user_id):
        has_joined = await check_channel_membership(update, context, update.effective_user.id)
        if not has_joined:
            await update.message.reply_text(
                "❌ Please join our channel first to use the bot.",
                reply_markup=get_join_channel_keyboard()
            )
            return
    
    text = update.message.text
    user_session = user_sessions.get(user_id, {'step': 'main'})
    
    # Get ALL localized button texts for comparison
    localized_texts = {
        # Bot Settings buttons
        'random_big': get_localized_message('random_big', language),
        'random_small': get_localized_message('random_small', language),
        'random_bot': get_localized_message('random_bot', language),
        'follow_bot': get_localized_message('follow_bot', language),
        'bs_formula': get_localized_message('bs_formula', language),
        'colour_formula': get_localized_message('colour_formula', language),
        'bot_stats': get_localized_message('bot_stats', language),
        'set_bet_sequence': get_localized_message('set_bet_sequence', language),
        'profit_target': get_localized_message('profit_target', language),
        'loss_target': get_localized_message('loss_target', language),
        'reset_stats': get_localized_message('reset_stats', language),
        'back_main_menu': get_localized_message('back_main_menu', language),
        
        # Main Menu buttons
        'ck_login': get_localized_message('ck_login', language),
        'bigwin_login': get_localized_message('bigwin_login', language),
        'six_login': get_localized_message('six_login', language),
        'balance': get_localized_message('balance', language),
        'results': get_localized_message('results', language),
        'bet_big': get_localized_message('bet_big', language),
        'bet_small': get_localized_message('bet_small', language),
        'bet_red': get_localized_message('bet_red', language),
        'bet_green': get_localized_message('bet_green', language),
        'bet_violet': get_localized_message('bet_violet', language),
        'bot_settings': get_localized_message('bot_settings', language),
        'my_bets': get_localized_message('my_bets', language),
        'sl_layer': get_localized_message('sl_layer', language),
        'language': get_localized_message('language', language),
        'run_bot': get_localized_message('run_bot', language),
        'stop_bot': get_localized_message('stop_bot', language),
    }
    
    # Debug: Print received text and localized texts for troubleshooting
    print(f"🔧 DEBUG: User {user_id} pressed: '{text}'")
    print(f"🔧 DEBUG: Language: {language}")
    print(f"🔧 DEBUG: Localized 'random_big': '{localized_texts['random_big']}'")
    
    if text == "🔄 Force Wait Bot":
        await force_wait_bot_command(update, context)
        return
        
    if user_session['step'] == 'login_phone':
        user_session['phone'] = text
        user_session['step'] = 'login'
        platform_name = get_platform_name(user_session.get('platform', 'ck'))
        await update.message.reply_text(
            f"✅ Phone number saved: {text}\nPlatform: {platform_name}\nNow please enter your password:",
            reply_markup=get_login_keyboard()
        )
        
    elif user_session['step'] == 'login_password':
        user_session['password'] = text
        user_session['step'] = 'login'
        platform_name = get_platform_name(user_session.get('platform', 'ck'))
        await update.message.reply_text(
            f"✅ Password saved!\nPlatform: {platform_name}\nClick '🚪 Login Now' to authenticate and save credentials.",
            reply_markup=get_login_keyboard()
        )
        
    elif user_session['step'] == 'set_bet_sequence':
        try:
            amounts = [int(x.strip()) for x in text.split(',')]
            if len(amounts) == 0:
                await update.message.reply_text("❌ Please enter valid amounts separated by commas")
                return
            
            if any(amount < 10 for amount in amounts):
                await update.message.reply_text("❌ Minimum bet amount is 10 K")
                return
                
            bet_sequence = ','.join(str(x) for x in amounts)
            save_user_setting(user_id, 'bet_sequence', bet_sequence)
            save_user_setting(user_id, 'current_bet_index', 0)
            
            user_session['step'] = 'main'
            await update.message.reply_text(
                f"✅ Bet sequence set to: {bet_sequence}\nStarting from first amount: {amounts[0]} K",
                reply_markup=get_main_keyboard(user_id)
            )
        except ValueError:
            await update.message.reply_text("❌ Please enter valid numbers separated by commas (e.g., 100,300,700,1600,3200,7600,16000,32000)")
    
    elif user_session['step'] == 'set_profit_target':
        try:
            target_amount = int(text.strip())
            if target_amount < 0:
                await update.message.reply_text("❌ Please enter a positive number or 0 to disable")
                return
                
            save_user_setting(user_id, 'profit_target', target_amount)
            user_session['step'] = 'main'
            
            if target_amount == 0:
                await update.message.reply_text(
                    "✅ Profit target disabled!\n\n"
                    "Bot will run continuously until manually stopped.",
                    reply_markup=get_bot_settings_keyboard(user_id)
                )
            else:
                await update.message.reply_text(
                    f"✅ Profit target set to: {target_amount:,} K\n\n"
                    f"Bot will automatically stop when profit reaches {target_amount:,} K",
                    reply_markup=get_bot_settings_keyboard(user_id)
                )
                
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number (e.g., 1000 for 1000 K target)")
    
    elif user_session['step'] == 'set_loss_target':
        try:
            target_amount = int(text.strip())
            if target_amount < 0:
                await update.message.reply_text("❌ Please enter a positive number or 0 to disable")
                return
                
            save_user_setting(user_id, 'loss_target', target_amount)
            user_session['step'] = 'main'
            
            if target_amount == 0:
                await update.message.reply_text(
                    "✅ Loss target disabled!\n\n"
                    "Bot will run continuously until manually stopped.",
                    reply_markup=get_bot_settings_keyboard(user_id)
                )
            else:
                await update.message.reply_text(
                    f"✅ Loss target set to: {target_amount:,} K\n\n"
                    f"Bot will automatically stop when loss reaches {target_amount:,} K",
                    reply_markup=get_bot_settings_keyboard(user_id)
                )
                
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number (e.g., 500 for 500 K target)")
    
    elif user_session['step'] == 'set_bs_pattern':
        pattern = text.strip().upper()
        
        # Validate BS pattern - only B and S allowed
        valid_chars = {'B', 'S', ','}
        if all(c in valid_chars for c in pattern.replace(' ', '')):
            clean_pattern = ','.join([p.strip() for p in pattern.split(',') if p.strip()])
            
            if save_formula_patterns(user_id, bs_pattern=clean_pattern):
                user_session['step'] = 'main'
                await update.message.reply_text(
                    f"✅ **BS Pattern Set Successfully!**\n\n"
                    f"• 📋 BS Formula - Follow BS Pattern (B,S only)\n\n"
                    f"**BS Pattern:** {clean_pattern}\n"
                    f"Starting from first position.\n\n"
                    f"Bot will now follow this BS pattern in BS Formula mode.\n"
                    f"**Note:** Only B (BIG) and S (SMALL) are allowed in BS Formula.",
                    reply_markup=get_bs_pattern_keyboard()
                )
            else:
                await update.message.reply_text("❌ Error saving BS pattern. Please try again.")
        else:
            await update.message.reply_text(
                "❌ Invalid BS pattern! Use only B (BIG), S (SMALL) and commas.\n"
                "Examples: B,S,B,B or S,S,B\n"
                "**Note:** Colour codes (R,G,V) are NOT allowed in BS Formula.\n"
                "Please enter a valid BS pattern:"
            )
    
    elif user_session['step'] == 'set_colour_pattern':
        pattern = text.strip().upper()
        
        # Validate Colour pattern - only G, R, V allowed
        valid_chars = {'G', 'R', 'V', ','}
        if all(c in valid_chars for c in pattern.replace(' ', '')):
            clean_pattern = ','.join([p.strip() for p in pattern.split(',') if p.strip()])
            
            if save_formula_patterns(user_id, colour_pattern=clean_pattern):
                user_session['step'] = 'main'
                
                colour_count = sum(1 for c in clean_pattern if c in ['R', 'G', 'V'])
                total_bets = len(clean_pattern.split(','))
                
                await update.message.reply_text(
                    f"✅ **Colour Pattern Set Successfully!**\n\n"
                    f"• 🔮 Colour Formula - Follow Colour Pattern (G,R,V only)\n\n"
                    f"**Colour Pattern:** {clean_pattern}\n"
                    f"**Colour Bets:** {colour_count}/{total_bets}\n"
                    f"Starting from first position.\n\n"
                    f"Pattern Guide:\n"
                    f"• R = 🔴 RED\n"
                    f"• G = 🟢 GREEN\n"
                    f"• V = 🟣 VIOLET\n\n"
                    f"Bot will now follow this Colour pattern in Colour Formula mode.\n"
                    f"**Note:** Only G (GREEN), R (RED), and V (VIOLET) are allowed in Colour Formula.",
                    reply_markup=get_colour_pattern_keyboard()
                )
            else:
                await update.message.reply_text("❌ Error saving Colour pattern. Please try again.")
        else:
            await update.message.reply_text(
                "❌ Invalid Colour pattern! Use only G (GREEN), R (RED), V (VIOLET) and commas.\n"
                "Examples: R,G,V,R or G,V,R\n"
                "**Note:** BIG/SMALL codes (B,S) are NOT allowed in Colour Formula.\n"
                "Please enter a valid Colour pattern:"
            )
    
    elif user_session['step'] == 'set_sl_pattern':
        pattern = text.strip()
        
        try:
            numbers = [int(x.strip()) for x in pattern.split(',')]
            if all(1 <= num <= 5 for num in numbers):
                if save_sl_pattern(user_id, pattern):
                    user_session['step'] = 'main'
                    await update.message.reply_text(
                        f"✅ **SL Pattern Set Successfully!**\n\n"
                        f"**Pattern:** {pattern}\n"
                        f"Pattern saved and ready for use with SL Bot.\n\n"
                        f"Now when you press **🤖 Run Bot**, it will use SL Layer system.",
                        reply_markup=get_main_keyboard(user_id)
                    )
                else:
                    await update.message.reply_text("❌ Error saving SL pattern. Please try again.")
            else:
                await update.message.reply_text(
                    "❌ Invalid pattern! Use only numbers 1-5 separated by commas.\n"
                    "Example: 1,2,3,4,5\n"
                    "Please enter a valid pattern:"
                )
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid pattern format! Use only numbers 1-5 separated by commas.\n"
                "Example: 1,2,3,4,5\n"
                "Please enter a valid pattern:"
            )
    
    # ===== BOT SETTINGS MENU HANDLING =====
    # Handle localized Bot Settings buttons
    elif text == localized_texts['random_big']:
        await set_random_big(update, context)
    elif text == localized_texts['random_small']:
        await set_random_small(update, context)
    elif text == localized_texts['random_bot']:
        await set_random_bot(update, context)
    elif text == localized_texts['follow_bot']:
        await set_follow_bot(update, context)
    elif text == localized_texts['bs_formula']:
        await bs_formula_command(update, context)
    elif text == localized_texts['colour_formula']:
        await colour_formula_command(update, context)
    elif text == localized_texts['bot_stats']:
        await show_bot_stats(update, context)
    elif text == localized_texts['set_bet_sequence']:
        user_session['step'] = 'set_bet_sequence'
        current_sequence = get_user_setting(user_id, 'bet_sequence', '100,300,700,1600,3200,7600,16000,32000')
        await update.message.reply_text(
            f"Current bet sequence: {current_sequence}\n"
            "Enter new bet sequence (comma separated e.g.,) 100,300,700,1600,3200,7600,16000,32000"
        )
    elif text == localized_texts['profit_target']:
        await set_profit_target_command(update, context)
    elif text == localized_texts['loss_target']:
        await set_loss_target_command(update, context)
    elif text == localized_texts['reset_stats']:
        await reset_bot_stats(update, context)
    elif text == localized_texts['back_main_menu']:
        user_session['step'] = 'main'
        await update.message.reply_text("🏠 Main Menu", reply_markup=get_main_keyboard(user_id))
    
    # ===== MAIN MENU HANDLING =====
    # Handle localized Main Menu buttons (with fallback to English)
    elif text == localized_texts['ck_login'] or text == "🔐 CK Login":
        await ck_login_command(update, context)
        
    elif text == localized_texts['bigwin_login'] or text == "🔐 777 Login":
        await bigwin_login_command(update, context)
        
    elif text == localized_texts['six_login'] or text == "🔐 6 Login":
        await six_login_command(update, context)
        
    elif text == localized_texts['balance'] or text == "💰 Balance":
        await balance_command(update, context)
        
    elif text == localized_texts['results'] or text == "📊 Results":
        await results_command(update, context)
        
    elif text == localized_texts['bet_big'] or text == "🎲 Bet BIG":
        await place_bet_handler(update, context, 13)
        
    elif text == localized_texts['bet_small'] or text == "🎯 Bet SMALL":
        await place_bet_handler(update, context, 14)
        
    elif text == localized_texts['bet_red'] or text == "🔴 Bet RED":
        await bet_red_command(update, context)
        
    elif text == localized_texts['bet_green'] or text == "🟢 Bet GREEN":
        await bet_green_command(update, context)
        
    elif text == localized_texts['bet_violet'] or text == "🟣 Bet VIOLET":
        await bet_violet_command(update, context)
        
    elif text == localized_texts['bot_settings'] or text == "⚙️ Bot Settings":
        await bot_settings_command(update, context)
        
    elif text == localized_texts['my_bets'] or text == "📈 My Bets":
        await my_bets_command(update, context)
        
    elif text == localized_texts['sl_layer'] or text == "📋 SL Layer":
        await sl_layer_command(update, context)
        
    elif text == localized_texts['language'] or text == "🌐 Language":
        await language_command(update, context)
        
    elif text == localized_texts['run_bot'] or text == "🤖 Run Bot":
        await run_bot_command(update, context)
        
    elif text == localized_texts['stop_bot'] or text == "🛑 Stop Bot":
        await stop_bot_command(update, context)
    
    # ===== LOGIN MENU HANDLING =====
    elif text == "📝 Enter Phone":
        user_sessions[user_id]['step'] = 'login_phone'
        await update.message.reply_text("Please enter your phone number (without country code):")
        
    elif text == "🔑 Enter Password":
        user_sessions[user_id]['step'] = 'login_password'
        await update.message.reply_text("Please enter your password:")
        
    elif text == "🚪 Login Now":
        await process_login(update, context, save_credentials=True)
    
    # ===== LANGUAGE SELECTION =====
    elif text == "🇺🇸 English":
        await set_english_language(update, context)
        
    elif text == "🇲🇲 Burmese":
        await set_burmese_language(update, context)
        
    elif text == "🇨🇳 Chinese":
        await set_chinese_language(update, context)
        
    elif text == "🇹🇭 Thailand":
        await set_thai_language(update, context)
        
    elif text == "🇵🇰 Pakistan":
        await set_pakistan_language(update, context)
    
    # ===== BACKWARD COMPATIBILITY - English buttons =====
    elif text == "🎲 Random BIG":
        await set_random_big(update, context)
        
    elif text == "🎯 Random SMALL":
        await set_random_small(update, context)
        
    elif text == "🔄 Random Bot":
        await set_random_bot(update, context)
        
    elif text == "📈 Follow Bot":
        await set_follow_bot(update, context)
        
    elif text == "📋 BS Formula":
        await bs_formula_command(update, context)
        
    elif text == "🔮 Colour Formula":
        await colour_formula_command(update, context)
        
    elif text == "📊 Bot Stats":
        await show_bot_stats(update, context)
        
    elif text == "🔢 Set Bet Sequence":
        user_session['step'] = 'set_bet_sequence'
        current_sequence = get_user_setting(user_id, 'bet_sequence', '100,300,700,1600,3200,7600,16000,32000')
        await update.message.reply_text(
            f"Current bet sequence: {current_sequence}\n"
            "Enter new bet sequence (comma separated e.g.,) 100,300,700,1600,3200,7600,16000,32000"
        )
        
    elif text == "🎯 Profit Target":
        await set_profit_target_command(update, context)
        
    elif text == "🎯 Loss Target":
        await set_loss_target_command(update, context)
        
    elif text == "🔄 Reset Stats":
        await reset_bot_stats(update, context)
    
    # ===== OTHER BUTTONS =====
    elif text == "🔢 Set BS Pattern":
        await set_bs_pattern_command(update, context)
        
    elif text == "👀 View BS Pattern":
        await view_bs_pattern_command(update, context)
        
    elif text == "🗑️ Clear BS Pattern":
        await clear_bs_pattern_command(update, context)
        
    elif text == "🔢 Set Colour Pattern":
        await set_colour_pattern_command(update, context)
        
    elif text == "👀 View Colour Pattern":
        await view_colour_pattern_command(update, context)
        
    elif text == "🗑️ Clear Colour Pattern":
        await clear_colour_pattern_command(update, context)
        
    elif text == "🔢 Set SL Pattern":
        await set_sl_pattern_command(update, context)
        
    elif text == "👀 View SL Pattern":
        await view_sl_pattern_command(update, context)
        
    elif text == "🔄 Reset SL Pattern":
        await reset_sl_pattern_command(update, context)
        
    elif text == "🔄 Force Wait Bot":
        await force_wait_bot_command(update, context)
        
    elif text == "📊 SL Stats":
        await sl_bot_stats_command(update, context)
        
    elif text == "↩️ Main Menu":
        user_session['step'] = 'main'
        await update.message.reply_text("🏠 Main Menu", reply_markup=get_main_keyboard(user_id))
        
    elif text == "↩️ Bot Settings":
        user_session['step'] = 'main'
        await bot_settings_command(update, context)
        
    elif text == "↩️ Back":
        user_session['step'] = 'main'
        await update.message.reply_text("🏠 Main Menu", reply_markup=get_main_keyboard(user_id))
    
    else:
        await update.message.reply_text(
            "Please use the buttons below to navigate.",
            reply_markup=get_main_keyboard(user_id)
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")
    
    if update and update.message:
        await update.message.reply_text(
            "❌ An error occurred. Please try again later.",
            reply_markup=get_main_keyboard()
        )

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Please set your BOT_TOKEN in the code!")
        return
    
    init_database()
    migrate_database()  # Run migration on startup
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    logger.info("Auto Lottery Bot starting...")
    print("🤖 Auto Lottery Bot is running...")
    print("🔧 Database migration system: Enabled")
    print("🌐 Multi-language support: Enabled")
    print("🔄 Auto-fix missing database columns: Enabled")
    print("🎰 Features: Wait for Win/Loss before next bet")
    print("🔧 Modes: BIG Only, SMALL Only, Random Bot, Follow Bot")
    print("📋 BS Formula Pattern Betting System (B,S only)")
    print("🔮 Colour Formula Pattern Betting System (G,R,V only)")
    print("📋 SL Layer Pattern Betting System - BS/COLOUR PATTERN MODE REQUIRED")
    print("🔢 Bet Sequence System: 100,300,700,1600,3200,7600,16000,32000")
    print("🎯 Profit/Loss Target System")
    print("📊 Auto Statistics Tracking")
    print("🔴🟢🟣 Colour Betting Support (RED, GREEN, VIOLET)")
    print("🔐 Supported Platforms: CK Lottery, 777 Big Win, 6 Lottery")
    print("📢 Channel Join Requirement: Enabled")
    print("🆕 NEW: Separate BS Formula (B,S only) and Colour Formula (G,R,V only)")
    print("🆕 NEW: Force Wait Bot Command for SL 2")
    print("✅ FIXED: SL 2,3,4,5 now properly starts in WAIT BOT mode")
    print("✅ FIXED: Stop Bot button immediately stops all betting")
    print("💰 WAIT BOT: No amount display, Fake betting, Win/Loss messages only")
    print("🔄 FIXED: No duplicate Win/Loss messages in Wait Bot mode")
    print("🆕 NEW: Issue tracking system to prevent duplicate messages")
    print("✅ FIXED: BS/Colour Pattern Position now displays correctly")
    print("✅ FIXED: Bet Count now displays correctly in all messages")
    print("🏆 NEW: Total Win calculation and display for every WIN")
    print("🔄 NEW: Win တိုင်း အရှေ့ဆုံး SL ပြန်စခြင်း")
    print("✅ FIXED: SL Bot Bet Count မတက်ဘဲ Bet Result Update ပြတဲ့ပြဿနာ")
    print("✅ FIXED: 'already processed' issue for SL Bot Win/Loss messages")
    print("✅ FIXED: Current Step 1 ကနေ Loss ဖြစ်ရင် Current Step 2 ဖြစ်အောင်ပြင်ဆင်ခြင်း")
    print("✅ FIXED: Bet Sequence ဇကျော်နေတဲ့ ပြဿနာ - 10K ပြီးရင် 30K ထိုးမယ်")
    print("🎯 NEW: Default Bet Sequence: 100,300,700,1600,3200,7600,16000,32000")
    print("🌐 NEW: Language Selection - English, Burmese, Chinese, Thailand, Pakistan")
    print("🔄 NEW: Dynamic Keyboard Localization - Bot Settings menu changes with language")
    print("⏹️  Press Ctrl+C to stop.")
    
    application.run_polling()

if __name__ == "__main__":
    main()