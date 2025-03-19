import json
from datetime import datetime, time
import pytz
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATA_FILE = 'data.json'
ADMIN_CHAT_ID = 000000000  # Replace with your admin chat ID
USER_CHAT_ID = 000000000   # Replace with your user chat ID
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

# Command handlers
async def start(update, context):
    logger.debug("Received /start command.")
    await update.message.reply_text("Hi! I'm here to help you remember your meds and meals. Use /help for commands!")

async def help_command(update, context):
    logger.debug("Received /help command.")
    message = (
        "Here’s how I can help you, darling:\n"
        "- /addmed <name> <time> [days] - Add a medication (e.g., /addmed PillA 10:00 Mon Wed Fri)\n"
        "- /setmeal <type> <time> - Set meal time (e.g., /setmeal breakfast 08:00)\n"
        "- /report - View medication logs (admin only)\n"
        "- /myprogress - See your progress\n"
    )
    await update.message.reply_text(message)

# add med command handler
async def add_med(update, context):
    logger.debug("Received /addmed command.")
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Sorry, only my creator can use this command.")
        logger.warning("Unauthorized /addmed command attempted.")
        return
    try:
        args = context.args
        if len(args) < 2:
            raise ValueError("Usage: /addmed <name> <time> [days]")
        med_name = args[0]
        time_str = args[1]
        days = args[2:] if len(args) > 2 else ['daily']
        from datetime import datetime
        datetime.strptime(time_str, '%H:%M')
        data = load_data()
        if any(m['name'] == med_name for m in data['medications']):
            raise ValueError("Medication name already exists.")
        med = {'name': med_name, 'time': time_str, 'days': days}
        data['medications'].append(med)
        save_data(data)
        h, m_val = map(int, time_str.split(':'))
        job_time = time(hour=h, minute=m_val, tzinfo=TIME_ZONE)
        context.job_queue.run_daily(send_med_reminder, job_time, name=med_name)
        await update.message.reply_text(f"Added {med_name} at {time_str} on {', '.join(days)}.")
        logger.info(f"Added medication {med_name} scheduled at {time_str} on {days}.")
    except Exception as e:
        await update.message.reply_text(f"Oops! Error: {str(e)}")
        logger.error(f"Error in /addmed: {e}")


# set meal command handler
async def set_meal(update, context):
    logger.debug("Received /setmeal command.")
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Sorry, only my creator can use this command.")
        logger.warning("Unauthorized /setmeal command attempted.")
        return
    try:
        args = context.args
        if len(args) != 2:
            raise ValueError("Usage: /setmeal <type> <time>")
        meal_type = args[0].lower()
        time_str = args[1]
        if meal_type not in ['breakfast', 'lunch', 'dinner']:
            raise ValueError("Meal type must be breakfast, lunch, or dinner.")
        from datetime import datetime
        datetime.strptime(time_str, '%H:%M')
        data = load_data()
        job_id = f"{meal_type}"
        existing_jobs = [job for job in context.job_queue.jobs() if job.name == job_id]
        for job in existing_jobs:
            job.schedule_removal()
        h, m_val = map(int, time_str.split(':'))
        job_time = time(hour=h, minute=m_val, tzinfo=TIME_ZONE)
        context.job_queue.run_daily(send_meal_reminder, job_time, name=meal_type)
        data['meals'][meal_type] = time_str
        save_data(data)
        await update.message.reply_text(f"Set {meal_type} time to {time_str}. Yum!")
        logger.info(f"Set meal time for {meal_type} at {time_str}.")
    except Exception as e:
        await update.message.reply_text(f"Oops! Error: {str(e)}")
        logger.error(f"Error in /setmeal: {e}")


if __name__ == '__main__':
    logger.info("Bot starting...")
