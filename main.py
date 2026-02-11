import telebot
import traceback
from functools import wraps
from database import init_db, add_user, get_user, get_stats, update_user_data, logger
from config import BOT_TOKEN, ADMIN_IDS

bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Преобразуем объект пользователя в словарь для add_user
    user_dict = {
        'id': message.from_user.id,
        'username': message.from_user.username,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name,
        'language_code': message.from_user.language_code,
        'is_bot': message.from_user.is_bot
    }

    # Просто вызываем функцию — вся сложность спрятана в database.py
    add_user(user_dict)

    welcome_text = f"""
    Привет, {message.from_user.first_name}! 
    Теперь я знаю о тебе всё необходимое и запомнил это навсегда.
    """
    bot.reply_to(message, welcome_text)

# 5. Обработчик команды /help
@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
    Вот что я пока умею:
    /start - Поздороваться и начать работу
    /help - Показать это сообщение
    /keys - Показать, что ключи загружены (тихая проверка)
    Просто текст - Я его вежливо повторю.
    """
    bot.reply_to(message, help_text)

# Декоратор для обработки ошибок во всех хендлерах
def handle_errors(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        try:
            return func(message, *args, **kwargs)
        except KeyError as e:
            logger.error(f"KeyError в {func.__name__}: {e}\n{traceback.format_exc()}")
            bot.reply_to(message, "⚠️ Ошибка в данных. Попробуйте позже или напишите /start")
        except Exception as e:
            logger.error(f"Ошибка в {func.__name__}: {e}\n{traceback.format_exc()}")
            bot.reply_to(message, "❌ Произошла внутренняя ошибка. Разработчик уведомлен.")

    return wrapper


@bot.message_handler(commands=['profile'])
@handle_errors
def show_profile(message):
    user_data = get_user(message.from_user.id)

    if not user_data:
        bot.reply_to(message, "Кажется, мы не знакомы. Напиши /start.")
        return

    # Безопасный доступ к данным - показываем ВСЕ поля
    profile_text = f"""
    👤 *Твой профиль:*
    ID: `{user_data.get('user_id', 'N/A')}`
    Username: @{user_data.get('username', 'отсутствует')}
    Имя: {user_data.get('first_name') or 'Не указано'}
    Фамилия: {user_data.get('last_name') or 'Не указано'}
    Язык: {user_data.get('language_code') or 'не определён'}
    Бот: {'Да' if user_data.get('is_bot') else 'Нет'}
    
    📅 *Даты:*
    Зарегистрирован: {user_data.get('created_at', 'неизвестно')[:10]}
    Последний визит: {user_data.get('last_seen', 'неизвестно')[:19]}
    
    ⚙️ *Настройки ИИ:*
    Модель: `{user_data.get('ai_model', 'не настроена')}`
    Креативность: {user_data.get('temperature', 'не настроена')}"""

    bot.reply_to(message, profile_text, parse_mode='Markdown')


@bot.message_handler(commands=['stats'])
def show_stats(message):
    # Простая проверка на админа (подставьте свой Telegram ID)
    if message.from_user.id not in ADMIN_IDS:  # Замените на ваш ID
        bot.reply_to(message, "Эта команда только для разработчика.")
        return

    stats = get_stats()
    if stats:
        stats_text = f"""
        📈 Статистика бота:
        Всего пользователей: {stats['total_users']}
        Активных сегодня: {stats['active_today']}
        С настройками ИИ: {stats['users_with_settings']}
        """
        bot.reply_to(message, stats_text, parse_mode='html')
    else:
        bot.reply_to(message, "Не удалось получить статистику.")


# 7. Обработчик ЛЮБОГО текстового сообщения
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"Ты написал: '{message.text}'. Я пока только учусь отвечать по-умному!")


# Инициализируем базу данных при запуске
if not init_db():
    print("❌ Не удалось инициализировать базу данных. Бот не может работать.")
    exit(1)

if __name__ == "__main__":
    print("🤖 Бот запускается...")
    bot.infinity_polling(none_stop=True)
