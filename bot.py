import json
from datetime import datetime, time
import pytz
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATA_FILE = 'data.json'
USER_CHAT_ID = 000000000  # Replace with your user chat ID
BOT_TOKEN = "your bot token from BotFather"
TIME_ZONE = pytz.timezone('Asia/Tehran')

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        logger.debug("Data loaded successfully.")
        return data
    except FileNotFoundError:
        logger.warning("Data file not found. Using default structure.")
        return {
            'medications': [],
            'meals': {'breakfast': None, 'lunch': None, 'dinner': None},
            'logs': []
        }

def save_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        logger.debug("Data saved successfully.")
    except Exception as e:
        logger.error(f"Error saving data: {e}")

# Reminder function for med
async def send_med_reminder(context):
    job = context.job
    med_name = job.name
    logger.debug(f"Sending medication reminder for {med_name}.")
    data = load_data()
    med = next((m for m in data['medications'] if m['name'] == med_name), None)
    if med:
        today = datetime.now(TIME_ZONE).strftime('%a')
        if 'days' in med and med['days'] != ['daily'] and today not in med['days']:
            logger.info(f"Medication {med_name} is not scheduled for today ({today}).")
            return
        message = f"Time to take your {med_name}. 💊"
        keyboard = [[InlineKeyboardButton("Taken", callback_data=f"taken_{med_name}_{datetime.now(TIME_ZONE).date().isoformat()}")]]
        await context.bot.send_message(chat_id=USER_CHAT_ID, text=message, reply_markup=InlineKeyboardMarkup(keyboard))
        logger.info(f"Sent reminder for {med_name}.")
    else:
        logger.warning(f"Medication {med_name} not found in data.")

# Reminder function for meal
async def send_meal_reminder(context):
    job = context.job
    meal_type = job.name
    logger.debug(f"Sending meal reminder for {meal_type}.")
    await context.bot.send_message(chat_id=USER_CHAT_ID, text=f"Time for {meal_type}. 🍽️")

# callback handler
async def button_callback(update, context):
    query = update.callback_query
    await query.answer()
    data_str = query.data
    logger.debug(f"Button pressed with data: {data_str}")
    if data_str.startswith('taken_'):
        _, med_name, date_str = data_str.split('_', 2)
        date = datetime.fromisoformat(date_str).date()
        data = load_data()
        data['logs'].append({'med': med_name, 'date': date.isoformat(), 'taken': True})
        save_data(data)
        await query.edit_message_text(text=f"You've taken {med_name} on {date_str}. Great job! 🎉")
        logger.info(f"Logged intake for {med_name} on {date_str}.")

if __name__ == '__main__':
    logger.info("Bot starting...")
