import os
import sys
import time
import logging
import json as simplejson
from http import HTTPStatus

import requests
import telegram
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

import exceptions

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'logger.log', maxBytes=50000000, backupCount=5, encoding='utf-8'
)
logger.addHandler(handler)
# Добавляем вывод лога в консоль
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
streamHandler = logging.StreamHandler(sys.stdout)
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

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
    except telegram.TelegramError as error:
        logger.error(f'Ошибка! Сообщение не отправлено {error}')


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
        print(status_homework.content)
    except requests.exceptions.RequestException as error:
        message_error = f'Сбой при запросе к endpoint: {error}'
        logger.error(message_error)
        raise exceptions.APIResponseStatusCodeException(message_error)

    try:
        if status_homework.status_code != HTTPStatus.OK:
            status_homework.raise_for_status()
            error_message = 'Некоректный ответ от сервера. != 200'
            logger.error(error_message)
            raise exceptions.APIResponseStatusCodeException(error_message)
        return status_homework.json()
    except simplejson.JSONDecodeError:
        error_message = 'Ошибка преобразования в json'
        logger.error(error_message)
        raise exceptions.DecoderJsonException(error_message)


def check_response(response):
    """Проверяет ответ API на корректность."""
    try:
        homeworks_list = response['homeworks']
    except KeyError as error:
        error_message = f'Ошибка доступа по ключу {error}'
        logger.error(error_message)
        raise KeyError(error_message)

    if homeworks_list is None:
        error_message = 'В ответе отсутствует словарь'
        logger.error(error_message)
        raise exceptions.CheckResponseTypeException(error_message)
    if 'current_date' not in response:
        error_message = 'В ответе API отсутствует ключ current_date'
        logger.error(error_message)
        raise KeyError(error_message)
    if not isinstance(homeworks_list, list):
        logger.error('Пришел неверный тип данных от сервера!')
        raise TypeError('Пришел неверный тип данных от сервера!')
    return homeworks_list


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе."""
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

    verdict = HOMEWORK_STATUSES[homework_status]
    if verdict is None:
        error_message = 'Нет статуса домашки'
        logger.error(error_message)
        raise exceptions.UnknownStatusHWException(error_message)
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
        raise (error_message)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    logger.info('Бот инициирован')
    current_timestamp = int(time.time()) - 1209600

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks) != 0:
                logger.info('Есть новости')
                message = parse_status(homeworks[0])
                send_message(bot, message)
            current_timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
