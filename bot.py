import json
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATA_FILE = 'data.json'

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

if __name__ == '__main__':
    logger.info("Bot starting...")
