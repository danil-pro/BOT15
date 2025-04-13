import telebot
from telebot import types
from telebot.types import ChatPermissions
from config import TOKEN, BOT_TAG, client_instructions, translator_instructions, GROUP_LINK
from datetime import datetime, timedelta
import time
from admin import RegisteredUser, MuteWord, app, db

bot = telebot.TeleBot(TOKEN)
admin_user = [1375260728, 6682774535]

client_states = {}
translator_states = {}
translator_answers = {}

translator_questions = [
    "1️⃣ Как вас зовут?\n\n(Имя, под которым вас будут знать клиенты.)",
    "2️⃣ В каком городе вы находитесь?\n\n(Например: Берлин, Гамбург, Мюнхен.)",
    "3️⃣ Какой у вас уровень немецкого языка?\nВыберите: A1, A2, B1, B2, C1, C2, Nativ (Родной)",
    "4️⃣ Какая ваша примерная почасовая ставка (€)?\n(Например: 15)",
    "5️⃣ Как с вами можно связаться?\n@username или номер телефона"
]


@bot.message_handler(commands=['help'])
def help_command(message):
    if message.from_user.id in admin_user:
        help_text = (
            "📋 <b>Доступные команды (админ):</b>\n"
            "/stats — статистика пользователей\n"
            "/mute user_id время — замутить пользователя\n"
            "/unmute user_id — размутить пользователя\n"
            "/ban user_id — забанить пользователя\n"
            "/unban user_id — разбанить пользователя\n"
            "/info — ваша информация\n"
            "/cancel — отменить регистрацию"
        )
    else:
        help_text = (
            "📋 <b>Доступные команды:</b>\n"
            "/info — ваша информация\n"
            "/cancel — отменить регистрацию"
        )

    bot.send_message(message.chat.id, help_text, parse_mode="HTML")


@bot.message_handler(commands=['mute'])
def mute_user(message):
    if message.chat.type == 'private':
        bot.send_message(message.chat.id, "❗ Команда работает только в группе.")
        return

    from_id = message.from_user.id
    if from_id not in admin_user:
        bot.send_message(message.chat.id, "❌ Только администраторы могут использовать эту команду.")
        return

    args = message.text.strip().split()
    if len(args) != 3:
        bot.send_message(message.chat.id, "❗ Использование: /mute <user_id> <время_в_минутах>")
        return

    try:
        user_id = int(args[1])
        minutes = int(args[2])
        until_date = int((datetime.utcnow() + timedelta(minutes=minutes)).timestamp())

        permissions = ChatPermissions(can_send_messages=False)

        bot.restrict_chat_member(message.chat.id, user_id, until_date, permissions=permissions)

        bot.send_message(message.chat.id, f"🔇 Пользователь {message.from_user.first_name} замучен на {minutes} мин.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при mute: {e}")


@bot.message_handler(commands=['unmute'])
def unmute_user(message):
    if message.chat.type == 'private':
        bot.send_message(message.chat.id, "❗ Команда работает только в группе.")
        return

    from_id = message.from_user.id
    if from_id not in admin_user:
        bot.send_message(message.chat.id, "❌ Только администраторы могут использовать эту команду.")
        return

    args = message.text.strip().split()
    if len(args) != 2:
        bot.send_message(message.chat.id, "❗ Использование: /unmute <user_id>")
        return

    try:
        user_id = int(args[1])

        # Разрешаем всё
        permissions = ChatPermissions(can_send_messages=True)

        bot.restrict_chat_member(message.chat.id, user_id, None, permissions=permissions)
        bot.send_message(message.chat.id, f"🔊 Пользователь {message.from_user.first_name} размучен.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при unmute: {e}")


@bot.message_handler(commands=['cancel'])
def cancel_registration(message):
    if message.chat.type != "private":
        return

    user_id = str(message.from_user.id)

    if user_id in client_states:
        del client_states[user_id]
        bot.send_message(message.chat.id, "❌ Регистрация клиента отменена.")
        return

    if user_id in translator_states:
        del translator_states[user_id]
        if user_id in translator_answers:
            del translator_answers[user_id]
        bot.send_message(message.chat.id, "❌ Регистрация переводчика отменена.")
        return

    bot.send_message(message.chat.id, "ℹ️ Вы не находитесь в процессе регистрации.")


@bot.message_handler(commands=['info'])
def info(message):
    if message.chat.type != "private":
        bot.send_message(message.chat.id, "❗ Пожалуйста, используйте эту команду в личных сообщениях.")
        return

    user_id = message.from_user.id
    with app.app_context():
        user = RegisteredUser.query.get(user_id)

    if user is None:
        bot.send_message(message.chat.id, "❗ Вы ещё не зарегистрированы. Введите /start.")
        return

    info_text = f"🔹 Ваша роль: {user.role}\n🔹 Город: {user.city}"

    if user.role == "Translator":
        info_text += (
            f"\n🔹 Имя: {user.name}"
            f"\n🔹 Уровень языка: {user.language_level}"
            f"\n🔹 Ставка (€/час): {user.price}"
            f"\n🔹 Контакт: {user.contact}"
        )

    bot.send_message(message.chat.id, info_text)


@bot.message_handler(commands=['stats'])
def stats(message):
    user_id = message.from_user.id

    if message.chat.type != "private":
        return

    if user_id not in admin_user:
        return

    try:
        with app.app_context():
            users = RegisteredUser.query.all()

            total_users = len(users)
            translators = sum(1 for u in users if u.role == "Translator")
            clients = total_users - translators

        bot.send_message(
            message.chat.id,
            f"📊 <b>Статистика пользователей:</b>\n"
            f"Всего: {total_users}\n"
            f"Переводчики: {translators}\n"
            f"Клиенты: {clients}",
            parse_mode="HTML"
        )

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Произошла ошибка: {str(e)}")


@bot.message_handler(content_types=['new_chat_members'])
def welcome(message):
    for new_user in message.new_chat_members:
        permissions = ChatPermissions(can_send_messages=False)

        bot.restrict_chat_member(message.chat.id, new_user.id, 10000, permissions=permissions)

        welcome_text = f'''Добро пожаловать в группу "Переводчики Германии" пройдите регистрацию в {BOT_TAG} для полного доступа.'''
        msg = bot.send_message(message.chat.id, welcome_text)
        time.sleep(10)
        bot.delete_message(message.chat.id, message_id=msg.message_id)


@bot.message_handler(commands=['start'])
def handle_start(message):
    if message.chat.type != "private":
        return
    user_id = message.from_user.id
    with app.app_context():
        existing = RegisteredUser.query.filter_by(id=user_id).first()
    print(existing)

    if existing:
        bot.send_message(message.chat.id, "✅ Вы уже зарегистрированы.")
        return

    welcome_text = (
        '👋 Добро пожаловать в группу "Переводчики Германии"!\n\n'
        'Наша группа помогает найти переводчика в вашем городе (более 40 городов) для сопровождения к врачу, '
        'в государственные учреждения (Jobcenter, Ausländerbehörde), а также для помощи с документами, письмами'
        ' и в других повседневных ситуациях.\n\n'
        'Если вы владеете языком, вы можете найти клиентов и предложить свои услуги.\n\n'
        '🔹 *Выберите вашу роль:*\n'
        '• Если вы переводчик, нажмите "Переводчик"\n'
        '• Если вы ищете переводчика, нажмите "Клиент"'
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("Клиент"), types.KeyboardButton("Переводчик"))

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)


# Нажата кнопка "Клиент"
@bot.message_handler(func=lambda m: m.text == "Клиент")
def register_client_start(message):
    user_id = message.from_user.id
    with app.app_context():
        existing = RegisteredUser.query.filter_by(id=user_id).first()

    if existing:
        bot.send_message(message.chat.id, "✅ Вы уже зарегистрированы как клиент.")
        return
    client_states[user_id] = True
    bot.send_message(message.chat.id, "✏️ Пожалуйста, укажите ваш город (например: Берлин, Гамбург, Мюнхен).")


# Ответ клиента с городом
@bot.message_handler(func=lambda m: m.text == "Переводчик")
def register_translator_start(message):
    user_id = message.from_user.id
    with app.app_context():
        existing = RegisteredUser.query.filter_by(id=user_id).first()

    if existing:
        bot.send_message(message.chat.id, "✅ Вы уже зарегистрированы как переводчик.")
        return
    translator_states[user_id] = 0
    translator_answers[user_id] = []
    bot.send_message(message.chat.id, translator_questions[0])


# Обработка ответов
# Переводчик: обработка шагов
@bot.message_handler(func=lambda m: m.chat.type == "private")
def handle_private_message(message):
    user_id = message.from_user.id

    # Клиент
    if user_id in client_states:
        city = message.text.strip()
        with app.app_context():
            user = RegisteredUser(
                id=user_id,
                role='Client',
                name=None,
                city=city,
                language_level=None,
                price=None,
                contact='',
                banned=False
            )
            db.session.add(user)
            db.session.commit()
        del client_states[user_id]

        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text="🔗 Перейти в группу", url=GROUP_LINK)
        markup.add(button)

        bot.send_message(message.chat.id, "✅ Спасибо! Вы зарегистрированы как клиент."
                         , reply_markup=types.ReplyKeyboardRemove())
        bot.send_message(message.chat.id, client_instructions(), reply_markup=markup)
        return

    # Переводчик
    if user_id in translator_states:
        step = translator_states[user_id]
        user_input = message.text.strip()

        # Обработка шага выбора языка (шаг 2)
        if step == 2:
            valid_levels = ["A1", "A2", "B1", "B2", "C1", "C2", "Nativ(Родной)"]
            if user_input not in valid_levels:
                bot.send_message(message.chat.id, "❗ Пожалуйста, выберите уровень из кнопок ниже.")
                return
            translator_answers[user_id].append(user_input)
        else:
            translator_answers[user_id].append(user_input)

        translator_states[user_id] += 1
        next_step = translator_states[user_id]

        if next_step < len(translator_questions):
            if next_step == 2:
                # Показать кнопки выбора языка
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                levels = ["A1", "A2", "B1", "B2", "C1", "C2", "Nativ(Родной)"]
                markup.add(*[types.KeyboardButton(lvl) for lvl in levels])
                bot.send_message(message.chat.id, translator_questions[next_step], reply_markup=markup)
            else:
                bot.send_message(message.chat.id, translator_questions[next_step])
        else:
            # Финал: сохранить пользователя
            answers = translator_answers[user_id]
            try:
                price = float(answers[3])
            except ValueError:
                # Удаляем неверный ввод из общего состояния (а не локальной копии)
                translator_answers[user_id].pop()
                translator_states[user_id] = 3  # Вернуть на шаг ставки

                bot.send_message(
                    message.chat.id,
                    "❗ Пожалуйста, введите корректную числовую ставку (например, 15 или 20.5)."
                )
                return

            with app.app_context():
                user = RegisteredUser(
                    id=user_id,
                    role='Translator',
                    name=answers[0],
                    city=answers[1],
                    language_level=answers[2],
                    price=price,
                    contact=answers[4],
                    banned=False
                )
                db.session.add(user)
                db.session.commit()

            del translator_states[user_id]
            del translator_answers[user_id]

            markup = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(text="🔗 Перейти в группу", url=GROUP_LINK)
            markup.add(button)

            # Очистка кнопок
            bot.send_message(message.chat.id, "✅ Спасибо! Вы зарегистрированы как переводчик.",
                             reply_markup=types.ReplyKeyboardRemove())
            bot.send_message(message.chat.id, translator_instructions(), reply_markup=markup)


@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.chat.type == 'private':
        bot.send_message(message.chat.id, "❗ Команда работает только в группе.")
        return

    from_user_id = message.from_user.id
    if from_user_id not in admin_user:
        bot.send_message(message.chat.id, "❌ Только администраторы могут использовать эту команду.")
        return

    args = message.text.strip().split()
    target_id = int(args[1])
    with app.app_context():
        existing = RegisteredUser.query.filter_by(id=target_id).first()

    if len(args) != 2:
        bot.send_message(message.chat.id, "❗ Использование: /ban_id <user_id>")
        return

    try:
        bot.ban_chat_member(message.chat.id, target_id)
        bot.send_message(message.chat.id, f"🚫 Пользователь `{message.from_user.first_name}` был заблокирован.",
                         parse_mode='Markdown')
        with app.app_context():
            existing.banned = True

            db.session.add(existing)
            db.session.commit()
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при бане: {str(e)}")


@bot.message_handler(commands=['unban'])
def unban(message):
    if message.chat.type == 'private':
        bot.send_message(message.chat.id, "❗ Команда работает только в группе.")
        return

    from_user_id = message.from_user.id

    if from_user_id not in admin_user:
        bot.send_message(message.chat.id, "❌ Только администраторы могут использовать эту команду.")
        return

    args = message.text.strip().split()
    target_id = int(args[1])
    with app.app_context():
        existing = RegisteredUser.query.filter_by(id=target_id).first()

    if len(args) != 2:
        bot.send_message(message.chat.id, "❗ Использование: /unban_id <user_id>")
        return

    try:
        bot.unban_chat_member(message.chat.id, target_id, only_if_banned=True)
        bot.send_message(message.chat.id, f"✅ Пользователь `{message.from_user.first_name}` был разбанен.",
                         parse_mode='Markdown')
        with app.app_context():
            existing.banned = False

            db.session.add(existing)
            db.session.commit()

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при разбане: {str(e)}")


@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'])
def delete_spam(message):
    from_user_id = message.from_user.id
    with app.app_context():
        existing = RegisteredUser.query.filter_by(id=from_user_id).first()

    if not message.text:
        return  # Пропускаем стикеры, фото и т.д.
    with app.app_context():
        if existing:
            if existing.banned:
                bot.ban_chat_member(message.chat.id, from_user_id)
        muted_words = [w.word for w in MuteWord.query.all()]
    message_text = message.text.lower()
    if any(keyword in message_text for keyword in muted_words):
        try:
            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            print(f"Удалено сообщение от {message.from_user.id} за спам.")
        except Exception as e:
            print(f"❌ Не удалось удалить сообщение: {e}")


def run_bot():
    print("🔁 Стартуем бота...")
    bot.infinity_polling()
