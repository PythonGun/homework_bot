class SendMessageFail(Exception):
    """Исключение отправки сообщения."""
    pass


class APIResponseStatusCodeException(Exception):
    """Исключение сбоя запроса к API."""
    pass


class CheckResponseTypeException(Exception):
    """Исключение неверного формата ответа API."""
    pass


class UnknownStatusHWException(Exception):
    """Исключение неизвестного статуса домашки."""
    pass


class DecoderJsonException(Exception):
    """Исключение при декодировании json."""
    pass
