import os
import time
import logging
import requests

from telegram import Bot
from http import HTTPStatus
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'my_logger.log', maxBytes=50000000, backupCount=5
)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в чат телеграмма."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Сообщение: {message}, успешно отправлено в чат')
    except Exception as error:
        logger.error(f'Ошибка! Сообщение не отправлено {error}')
        raise Exception(f'Ошибка при отправке сообщения {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        status_homework = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.exceptions.RequestException as error:
        logger.error(f'Сбой: {error}')
        raise Exception(f'сбой: {error}')

    if status_homework.status_code != HTTPStatus.OK:
        status_homework.raise_for_status()
        error_message = 'Некоректный ответ от сервера. != 200'
        logger.error(error_message)
        raise Exception(error_message)
    return status_homework.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    try:
        homeworks_list = response['homeworks']
    except KeyError as error:
        error_message = f'Ошибка формата данных. homeworks не список {error}'
        logger.error(error_message)
        raise KeyError(error_message)

    if 'homeworks' not in response:
        error_message = 'В ответе API отсутствует ключ homeworks'
        logger.error(error_message)
        raise KeyError(error_message)
    elif 'current_date' not in response:
        error_message = 'В ответе API отсутствует ключ current_date'
        logger.error(error_message)
        raise KeyError(error_message)
    else:
        if not isinstance(homeworks_list, list):
            logger.error('Пришел неверный тип данных от сервера!')
            raise TypeError('Пришел неверный тип данных от сервера!')
        return homeworks_list


def parse_status(homework):
    """извлекает из информации о конкретной домашней работе"""
    """статус этой работы."""
    if 'homework_name' not in homework:
        error_message = 'Отсутствует ключ homework_name'
        logger.error(error_message)
        raise KeyError(error_message)
    else:
        homework_name = homework.get('homework_name')

    if 'status' not in homework:
        error_message = 'Отсутствует ключ status или работа сдана на проверку'
        logger.error(error_message)
        raise KeyError(error_message)
    else:
        homework_status = homework.get('status')
        if homework_status not in HOMEWORK_STATUSES:
            logger.error(f'Неопознанный статус: {homework_status}')
            raise KeyError(f'Неопознанный статус: {homework_status}')

    verdict = HOMEWORK_STATUSES.get(homework_status)
    return (f'Изменился статус проверки работы '
            f'"{homework_name}". {verdict}')


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if PRACTICUM_TOKEN is None:
        logger.critical('Отсутствует обязательная переменная окружения:'
                        'PRACTICUM_TOKEN '
                        'Программа принудительно остановлена.')
        return False
    if TELEGRAM_TOKEN is None:
        logger.critical('Отсутствует обязательная переменная окружения: '
                        'TELEGRAM_TOKEN '
                        'Программа принудительно остановлена.')
        return False
    if TELEGRAM_CHAT_ID is None:
        logger.critical('Отсутствует обязательная переменная окружения: '
                        'TELEGRAM_CHAT_ID '
                        'Программа принудительно остановлена.')
        return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error_message = 'Токены недоступны'
        logger.error(error_message)
        raise Exception(error_message)

    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            if response:
                homework = check_response(response)
                logger.info('Есть новости')
                message = parse_status(homework)
                send_message(bot, message)
            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
