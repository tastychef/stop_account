import os
import time
import re
import base64
from datetime import date
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import telebot

from config import EMAIL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID  # Импортируем данные из config.py

# Настройки OAuth
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CLIENT_SECRETS_FILE = "client_secret.json"

# Инициализация Telegram бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def check_emails():
    try:
        service = get_gmail_service()
        print("Gmail сервис успешно инициализирован")
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], q='is:unread').execute()
        messages = results.get('messages', [])

        print(f"Найдено {len(messages) if messages else 0} непрочитанных сообщений")

        if not messages:
            print("Нет новых сообщений")
            return

        for message in messages:
            try:
                msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()

                # Получаем тело письма
                if 'parts' in msg['payload']:
                    parts = msg['payload']['parts']
                    data = parts[0]['body']['data']
                else:
                    data = msg['payload']['body']['data']
                text = base64.urlsafe_b64decode(data).decode('utf-8')

                # Ищем нужный текст в теле письма
                if "Показы всех рекламных кампаний для логина" in text:
                    # Извлекаем логин
                    login_match = re.search(r'логина\s+(\S+)', text)
                    login = login_match.group(1) if login_match else "Неизвестный логин"

                    # Извлекаем время остановки
                    time_match = re.search(r'сегодня в (\d{2}:\d{2})', text)
                    stop_time = time_match.group(1) if time_match else "Неизвестное время"

                    # Получаем текущую дату
                    current_date = date.today().strftime("%d.%m.%Y")

                    # Формируем сообщение для Telegram
                    message_text = f"Остановка показов:\nЛогин: {login}\nВремя остановки: {current_date} {stop_time}"
                    print(f"Используемый TELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID}")  # Логирование chat ID
                    bot.send_message(TELEGRAM_CHAT_ID, message_text)
                    print("Уведомление отправлено")

                # Помечаем письмо как прочитанное
                service.users().messages().modify(userId='me', id=message['id'],
                                                  body={'removeLabelIds': ['UNREAD']}).execute()
                print("Обработано письмо")
            except Exception as e:
                print(f"Ошибка при обработке письма: {e}")

    except Exception as e:
        error_message = f"Произошла ошибка: {str(e)}"
        print(error_message)
        bot.send_message(TELEGRAM_CHAT_ID, error_message)


def main():
    # Проверка на наличие переменной PORT для Render.com
    port = os.getenv('PORT', 5000)  # Используем значение по умолчанию 5000, если PORT не установлен
    print("Бот запущен. Проверка почты каждые 15 секунд...")

    try:
        bot.send_message(TELEGRAM_CHAT_ID, "Бот запущен и готов к работе")
        print("Тестовое сообщение отправлено в Telegram")
    except Exception as e:
        print(f"Ошибка при отправке тестового сообщения: {e}")

    while True:
        try:
            check_emails()
        except Exception as e:
            print(f"Ошибка в главном цикле: {e}")
        time.sleep(15)  # Проверка каждые 15 секунд


if __name__ == "__main__":
    main()