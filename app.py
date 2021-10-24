from datetime import datetime
from enum import unique
from flask.helpers import flash, url_for
from peewee import *
from flask import Flask, app, session, render_template, request, redirect, abort
from functools import wraps
from miniTweeter.app import DATABASE

app = Flask(__name__)
app.secret_key = '2bba76bc66ff5f0a50ccd2d1d70f5333'

# Database

DATABASE = 'todolist.db'
database= SqliteDatabase(DATABASE)

class BaseModel(Model):
    class Meta:
        database = database

class User(BaseModel):
    username = CharField(unique=True)
    email = CharField(unique=True)
    password = CharField()
    joined_at = DateTimeField(default = datetime.datetime.now())

class Task(BaseModel):
    user = ForeignKeyField(User, backref='tasks')
    event = TextField()
    event_date = DateField()
    done = BooleanField(default = False)
    updated_at = DateTimeField(default = datetime.dateime.now())

@app.before_request
def before_request():
    database.connect()

@app.after_request
def after_request(response):
    database.close()
    return response

# End Database

# Helper Function

def auth_user(user):
    session['logged_in'] = True
    session['user_id'] = user.id
    session['username'] = user.username

def get_current_user():
    if session.get('logged_in'):
        return User.get(User.id == session['user_id'])

def if_not_loggedIn(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
    
def if_loggedIn(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in'):
            return redirect(url_for('homepage'))
        return f(*args, **kwargs)
    return decorated_function

# End Helper Function

# Route

@app.route('/')
def homepage():
    return render_template('index.html')

@app.route('/dashboard') # harus log in dulu
def dashboard():
    user = get_current_user()
    return render_template('dasboard.html')

@app.route('/register', methods = ['GET', 'POST'])
def register():
    if request.method == 'POST' and request.form['username', 'email', 'password']:
        try:
            with database.atomic():
                user = User.create(
                    username = request.form['username'],
                    email = request.form['email'],
                    password = request.form['password'],
                )
                flash('akun berhasil didaftarkan! Silakan login untuk masuk ke dalam akun!')
            return redirect (url_for('login'))
        except IntegrityError:
            flash('coba daftar pakai username atau email yang lain!')
    return render_template('register.html')

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST' and request.form['email', 'password']:
        try:
            user = User.get(
                (User.email == request.form['email'])
                and
                (User.password == request.form['password'])
            )
        except User.DoesNotExist:
            flash('email atau password salah!')
        else:
            auth_user(user)
            return redirect (url_for('dasboard'))
    return render_template('login.html')


# End Route