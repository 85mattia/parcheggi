import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import hashlib

from flaskr.db import get_db
import psycopg2
import psycopg2.extras

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            admin = 0
            n = getUsersCount()
            print("ci sono " + str(n) + " users")
            if n == 0:    
                admin = 1
            hpassword = password.encode()
            hash_object = hashlib.sha256(hpassword)
            hashed_password = hash_object.hexdigest()
            
            db = get_db()
            curr = db.cursor()
            curr.execute(
                "INSERT INTO users (username, password, admin) VALUES (%s, %s , %s)",
                (str(username), hashed_password,admin)
            )
            db.commit()
            flash('Registrazione effettuata')
        except psycopg2.IntegrityError:
            flash(f"Utente {username} già registrato.")
        finally:
            db.close()
            return redirect(url_for("auth.login"))

    return render_template('auth/register.html')
    
@bp.route('/reset_password', methods=('GET', 'POST'))
def reset_password():
    return render_template('auth/reset_password.html')
    
    
@bp.route('/cambia_password', methods=('GET', 'POST'))
def cambia_password():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hpassword = password.encode()
        hash_object = hashlib.sha256(hpassword)
        hashed_password = hash_object.hexdigest()
        db = get_db()
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            'SELECT * FROM users WHERE username = %s',
            (username,)
        )
        utente = cur.fetchone()
        db.close()
        if utente is None:
            flash("matricola non trovata")
        else:
            db = get_db()
            cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
            'UPDATE users SET password = %s WHERE id = %s',
                (hashed_password,utente["id"])
            )
            db.commit()
            db.close()
            flash("la password è stata modificata, puoi eseguire il login")
            return redirect(url_for("auth.login"))
            
    return render_template('auth/reset_password.html')
    
@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        try:
            curr = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            curr.execute(
                "SELECT * FROM users WHERE username = %s", (username,)
            )
            user = curr.fetchone()
        finally:
            db.close()

        if user is None:
            error = 'Matricola non trovata, devi effettuare la registrazione'
        else:
            hpassword = password.encode()
            input_hash_object = hashlib.sha256(hpassword)
            input_hashed_password = input_hash_object.hexdigest()
            if input_hashed_password != user['password']:
                error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error, "error")

    return render_template('auth/login.html')
    
@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        db = get_db()
        try:
            curr = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            curr.execute(
                'SELECT * FROM users WHERE id = %s', (user_id,)
            )
            g.user = curr.fetchone()
        finally:
            db.close()
        
@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
    
def getUsersCount():
    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM users')
    utenti = cur.fetchall()
    db.close()
    return len(utenti)
    
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view