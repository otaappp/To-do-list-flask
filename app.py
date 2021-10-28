import datetime
# import re
from flask import Flask, app, session, render_template, request, redirect, abort
from enum import unique
from flask.helpers import flash, url_for
from peewee import *
from functools import wraps

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
    updated_at = DateTimeField(default = datetime.datetime.now)

@app.before_request
def before_request():
    database.connect()

@app.after_request
def after_request(response):
    database.close()
    return response

def create_tables():
    with database:
        database.create_tables([User, Task])

# End Database

# Helper Function

def auth_user(user):
    session['logged_in'] = True
    session['username'] = user.username

def get_current_user():
    if session.get('logged_in'):
        return User.get(User.username == session['username'])

def mustLogIn(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
    
def ifLoggedIn(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in'):
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# End Helper Function

# Route

@app.route('/')
def homepage():
    return render_template('index.html')

@app.route('/register', methods = ['GET', 'POST'])
@ifLoggedIn
def register():
    if request.method == 'POST' and request.form['username'] and request.form['email'] and request.form['password']:
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
@ifLoggedIn
def login():
    if request.method == 'POST' and request.form['email'] and request.form['password']:
        try:
            user = User.get(
                (User.email == request.form['email'])
                &
                (User.password == request.form['password'])
            )
        except User.DoesNotExist:
            flash('email atau password salah!')
        else:
            auth_user(user)
            return redirect (url_for('dashboard', username=user.username))
    return render_template('login.html')

@app.route('/logout')
@mustLogIn
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/popuser')
@mustLogIn
def popuser():
    try:
        user = User.get(User.username == session['username'])
    except User.DoesNotExist:
        return redirect(url_for('login'))
    else:
        Task.delete().where(Task.user == user.id).execute()
        User.delete().where(User.id == user.id).execute()
        return redirect(url_for('logout'))

@app.route('/<username>')
@mustLogIn
def dashboard(username):
    user = get_current_user()
    tasks = (
        Task.select()
        .where((Task.user == user.id) & (Task.event_date == datetime.date.today()))
        .order_by(Task.event.asc())
    )
    return render_template('dashboard.html', tasks=tasks)

@app.route('/add-task', methods = ['GET', 'POST'])
@mustLogIn
def addTask():
    if request.method == 'POST' and request.form['event'] and request.form['eventDate']:
        user = get_current_user()
        eventDateTransform = request.form['eventDate'].split("-")
        Task.create(
            user = user.id,
            event = request.form['event'],
            event_date = datetime.date(
                int(eventDateTransform[0]),
                int(eventDateTransform[1]),
                int(eventDateTransform[2])
            )
        )
        flash('Task berhasil ditambahkan!')
        return redirect(url_for('addTask'))
    return render_template('addTask.html')

@app.route('/view', methods = ['GET', 'POST'])
@mustLogIn
def allTask():
    user = User.get(User.username == session['username'])
    tasks = (
        Task.select(Task.event_date)
        .where(Task.user == user.id)
        .order_by(Task.event_date.desc())
        .distinct()
    )
    if request.method == 'POST':
        fromTransform = request.form['from'].split("-")
        fromIndex = datetime.date(int(fromTransform[0]), int(fromTransform[1]), int(fromTransform[2]))
        toTransform = request.form['to'].split("-") 
        toIndex = datetime.date(int(toTransform[0]), int(toTransform[1]), int(toTransform[2]))
        filtered = (
            Task.select()
            .where((Task.user == user.id) & (Task.event_date.between(fromIndex, toIndex)))
            .order_by(Task.event_date.asc())
            .distinct()
        )
        return render_template('view.html', filtered=filtered)
    return render_template('view.html', tasks=tasks)
    
@app.route('/view/<time>')
@mustLogIn
def onDate(time):
    timeTransform = time.split("-")
    index = datetime.date(int(timeTransform[0]), int(timeTransform[1]), int(timeTransform[2]))
    try:
        user = User.get(User.username == session['username'])
    except User.DoesNotExist:
        return redirect(url_for('login'))
    else:
        try:
            tasks = (
                Task.select()
                .where((Task.user == user.id) & (Task.event_date == index))
                .order_by(Task.event.asc())
            )
        except Task.DoesNotExist:
            abort(404)
        return render_template('viewDate.html', tasks=tasks, time=time)

@app.route('/upcoming')
@mustLogIn
def upcomingTask():
    user = get_current_user()
    tasks = (
        Task.select()
        .where((Task.user == user.id) & (Task.event_date > datetime.date.today()))
        .order_by(Task.event_date.asc())
    )
    return render_template('upcoming.html', tasks=tasks)

@app.route('/done/<time>/<id>')
@mustLogIn
def asDone(time, id):
    query = (
        Task.update(done = True)
        .where(Task.id == id)
        .execute()
    )
    timeTransform = time.split("-")
    index = datetime.date(int(timeTransform[0]), int(timeTransform[1]), int(timeTransform[2]))
    if index == datetime.date.today():
        return redirect(url_for('dashboard', username=session['username']))
    return redirect(url_for('onDate', time=time))

@app.route('/undone/<time>/<id>')
@mustLogIn
def asUndone(time, id):
    query = (
        Task.update(done = False)
        .where(Task.id == id)
        .execute()
    )
    timeTransform = time.split("-")
    index = datetime.date(int(timeTransform[0]), int(timeTransform[1]), int(timeTransform[2]))
    if index == datetime.date.today():
        return redirect(url_for('dashboard', username=session['username']))
    return redirect(url_for('onDate', time=time))

@app.route('/destroy/<time>/<id>')
@mustLogIn
def destroy(time, id):
    query = (
        Task.delete()
        .where(Task.id == id)
        .execute()
    )
    timeTransform = time.split("-")
    index = datetime.date(int(timeTransform[0]), int(timeTransform[1]), int(timeTransform[2]))
    if index == datetime.date.today():
        return redirect(url_for('dashboard', username=session['username']))
    return redirect(url_for('onDate', time=time))

@app.route('/edit/<time>/<id>', methods = ['GET', 'POST'])
@mustLogIn
def edit(time, id):
    if request.method == 'POST' and request.form['event'] and request.form['eventDate']:
        query = (
            Task.update(event = request.form['event'], event_date = request.form['eventDate'])
            .where(Task.id == id)
            .execute()
        )
        timeTransform = time.split("-")
        index = datetime.date(int(timeTransform[0]), int(timeTransform[1]), int(timeTransform[2]))
        flash('Task Berhasil diedit!')
        if index == datetime.date.today():
            return redirect(url_for('dashboard', username=session['username']))
        return redirect(url_for('onDate', time=time))
    user = get_current_user()
    getTask = (
        Task.select()
        .where((Task.user == user.id) & (Task.id == id))
    )
    return render_template('editTask.html', task=getTask, oldTime=time)

# End Route