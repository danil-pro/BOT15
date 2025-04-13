import threading
from main import run_bot
from admin import run_flask

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot)
    flask_thread = threading.Thread(target=run_flask)

    bot_thread.start()
    flask_thread.start()

    bot_thread.join()
    flask_thread.join()
