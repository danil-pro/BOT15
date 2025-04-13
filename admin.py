from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
from sqlalchemy.exc import SQLAlchemyError
from config import USER_DB_FILE
from functools import wraps
from models import RegisteredUser, MuteWord, db

# from main import load_users, load_spam_words

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = USER_DB_FILE
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'password':  # Replace with secure credentials
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    translators = RegisteredUser.query.filter_by(role='Translator').all()
    print(translators)
    clients = RegisteredUser.query.filter_by(role='Client').all()
    banned_users = RegisteredUser.query.filter_by(banned=True).all()
    print(banned_users)
    muted_words = [w.word for w in MuteWord.query.all()]

    return render_template('dashboard.html', translators=translators, clients=clients,
                          banned_users=banned_users, muted_words=muted_words)


@app.route('/ban_user/<int:user_id>', methods=['POST'])
@login_required
def ban_user(user_id):
    user = RegisteredUser.query.get_or_404(user_id)
    user.banned = True
    db.session.commit()
    flash(f'User {user_id} has been banned.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/unban_user/<int:user_id>', methods=['POST'])
@login_required
def unban_user(user_id):
    user = RegisteredUser.query.get_or_404(user_id)
    user.banned = False
    db.session.commit()
    flash(f'User {user_id} has been unbanned.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/mute_word', methods=['POST'])
@login_required
def mute_word():
    word = request.form['word'].strip().lower()

    if not word:
        flash("⚠️ Пустое слово не может быть добавлено.", 'error')
        return redirect(url_for('dashboard'))

    existing = MuteWord.query.filter_by(word=word).first()

    if existing:
        flash(f"⚠️ Слово '{word}' уже в списке.", 'error')
    else:
        try:
            new_word = MuteWord(word=word)
            db.session.add(new_word)
            db.session.commit()
            flash(f"✅ Слово '{word}' добавлено в список фильтрации.", 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"❌ Ошибка при добавлении слова: {e}", 'error')

    return redirect(url_for('dashboard'))


@app.route('/unmute_word/<word>', methods=['POST'])
@login_required
def unmute_word(word):
    word = word.strip().lower()
    existing = MuteWord.query.filter_by(word=word).first()

    if existing:
        try:
            db.session.delete(existing)
            db.session.commit()
            flash(f"✅ Слово '{word}' удалено из фильтра.", 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"❌ Ошибка при удалении: {e}", 'error')
    else:
        flash(f"⚠️ Слово '{word}' не найдено в базе.", 'error')

    return redirect(url_for('dashboard'))


def run_flask():
    print("🌐 Flask стартует...")
    with app.app_context():
        db.create_all()
        print("✅ База данных создана.")
    app.run(debug=True, port=5000, use_reloader=False)


