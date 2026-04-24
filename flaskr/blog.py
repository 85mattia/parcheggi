from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

from flaskr.auth import login_required
from flaskr.db import get_db
from datetime import datetime,timedelta
from pprint import pprint
import psycopg2.extras
import psycopg2
from psycopg2 import OperationalError, InterfaceError

bp = Blueprint('blog', __name__)

currentPage = ""
currentDate = datetime.today()
currentSetPage = ""
 

@bp.route('/')
def index():
    return render_template('blog/index.html')
    

@bp.route('/<page>/griglia', methods=('GET', 'POST'))
@login_required
def griglia(page):
    global currentPage
    global currentDate
    currentPage = page
    currentDate = datetime.today()
    dateStr = currentDate.strftime('%d-%m-%Y')
    location = "venezia"
    if page == "Venezia Oggi":
        n = 15
    if page == "Venezia Domani":
        currentDate = currentDate + timedelta(days=1)
        dateStr = currentDate.strftime('%d-%m-%Y')
        n = 15
    if page == "Mestre Oggi":
        location = "mestre"
        n = 10
    if page == "Mestre Domani":
        location = "mestre"
        currentDate = currentDate + timedelta(days=1)
        dateStr = currentDate.strftime('%d-%m-%Y')
        n = 10
    arr = ["conten"] * n
    try:
        db = get_db()
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            'SELECT * FROM prenotazioni WHERE location = %s',
            (location,))
        prenotazioni = cur.fetchall()
    finally:
        db.close()
    
    weekDay = currentDate.date().weekday()
    currentDayType = "feriale"
    if weekDay == 5:
        currentDayType = "sabato"
    if weekDay == 6 or isFestivo(currentDate.date()):
        currentDayType = "festivo"
    res = [pren for pren in prenotazioni if pren["repeat"] == currentDayType or (pren["repeat"] == "no" and pren["giorno"].date() == currentDate.date())]
    #res = [p for p in res if p["repeat"] == currentDayType]
    datiTable = [[]]
    datiTable.clear()
    for posto in range(n):
        prenInPosto = [r for r in res if r["n_parcheggio"] == posto+1]
        row = []
        row.clear()
        for ora in range(24):
            delId = ""
            prenInOra = [r for r in prenInPosto if ora in range(r["dalle_ore"], r["alle_ore"])]
            if len(prenInOra) == 1:
                if ora == prenInOra[0]["dalle_ore"]:
                    lenCell = prenInOra[0]["alle_ore"] - prenInOra[0]["dalle_ore"]
                    if prenInOra[0]["note"] != "":
                        row.append({"matricola":prenInOra[0]["note"],"lenCell":str(lenCell),"delId":delId,"annullaStr":"annulla"})
                    else:
                        if prenInOra[0]["matricola"] == g.user['username']:
                            delId = prenInOra[0]["id"]
                        row.append({"matricola":prenInOra[0]["matricola"],"lenCell":str(lenCell),"delId":delId,"annullaStr":"annulla"})
            elif len(prenInOra) == 0:
                row.append({"matricola":"","lenCell":str(1)})
            else:
                return "errore : piu prenotazioni per l'ora " + str(ora)
        datiTable.append(row)
    return render_template('blog/griglia.html', page=page, nPosti=n, dati=datiTable, dateStr=dateStr, tipo=currentDayType)
    
@bp.route('/setting_menu', methods=('GET', 'POST'))
@login_required
def setting_menu():
    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        'SELECT * FROM users WHERE admin = %s',
        (1,))
    admins = cur.fetchall()
    db.close()
    admins = [d for d in admins if d['username'] != g.user["username"]]
    return render_template('blog/setting_menu.html', admins=admins)
    
@bp.route('/<setPage>/setting', methods=('GET', 'POST'))
@login_required
def setting(setPage):
    global currentSetPage
    currentSetPage = setPage
    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        'SELECT * FROM prenotazioni WHERE location = %s AND repeat != %s',
        (currentSetPage.lower(),"no",)
    )
    assegnazioni = cur.fetchall()
    db.close()
    totPosti=10
    if setPage == "Venezia":
        totPosti = 15
    return render_template('blog/setting.html', setPage=setPage, val=assegnazioni , totPosti=totPosti)
    
@bp.route('/<loc>/salvaSetting', methods=('POST', 'GET'))
@login_required
def salvaSetting(loc):
    dataForm = request.form #dict
    data = {key: value for key, value in dataForm.items() if value != ""}
    arrToSave = []
    arrToSave.clear()
    for rowNumber in range(0,50):
        resDict = {k: v for k, v in data.items() if k.endswith('.' + str(rowNumber))}
        resDictCopy = resDict.copy()
        if len(resDict) > 0:
            for key, value in resDictCopy.items():
                newKey = key[0:key.find(".")]
                resDict[newKey] = resDict.pop(key)
            arrToSave.append(resDict)
    arrToEdit = [d for d in arrToSave if len(d) == 6 and d["id"] != ""]
    arrToAdd = [d for d in arrToSave if len(d) == 5 and "id" not in d]
    error = validatePrenForm(arrToEdit + arrToAdd)
    if error != "":
        return error
    editInDb = []
    editInDb.clear()
    for d in arrToEdit:
        t = (g.user['id'],d["nPosto"],d["dalle"],d["alle"],datetime.today(),loc.lower(), d["repeat"],"", d["note"],d["id"])
        editInDb.append(t)
    addInDb = []
    addInDb.clear()
    for d in arrToAdd:
        t = (g.user['id'],d["nPosto"],d["dalle"],d["alle"],datetime.today(),loc.lower(), d["repeat"],"", d["note"])
        addInDb.append(t)
    db = get_db()
    cur = db.cursor()
    cur.executemany('UPDATE prenotazioni SET (author_id, n_parcheggio, dalle_ore, alle_ore, giorno, location, repeat, matricola, note) = (%s,%s,%s,%s,%s,%s,%s,%s,%s) WHERE id = %s', editInDb)
    cur.executemany(
        'INSERT INTO prenotazioni (author_id, n_parcheggio, dalle_ore, alle_ore, giorno, location, repeat, matricola, note)'
        ' VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',addInDb)
    db.commit()
    db.close()
    flash("salvataggio avvento con successo")
    return render_template('blog/setting_menu.html')
    
@bp.route('/<obj_id>/delete_row_setting', methods=('GET', 'POST'))
@login_required
def delete_row_setting(obj_id):
    db = get_db()
    curr = db.cursor()
    curr.execute('DELETE FROM prenotazioni WHERE id = %s', (obj_id,))
    db.commit()
    db.close()
    flash("cancellato elemento " + obj_id)
    return render_template('blog/setting_menu.html')
    
def validatePrenForm(prenotazioni):
    for p in prenotazioni:
        if int(p["dalle"]) >= int(p["alle"]):
            return "errore : fine deve essere maggiore di inizio per parcheggio n " + p["nPosto"]
    for n in range(1,16):
        prenInPosto = [r for r in prenotazioni if r["nPosto"] == n]
        if len(prenInPosto) > 2:
            return "errore : piu di due prenotazioni per parcheggio n " + p["nPosto"]
        if len(prenInPosto) == 2:
            if overlaps(range(int(prenInPosto[0]["dalle"]),int(prenInPosto[0]["alle"])),range(int(prenInPosto[1]["dalle"]),int(prenInPosto[1]["alle"]))):
                return "errore : orari sovrapposti per parcheggio n " + p["nPosto"]
    return ""
        
@bp.route('/<obj_id>/annullaPrenotazione', methods=('GET', 'POST'))
@login_required
def annullaPrenotazione(obj_id):
    db = get_db()
    cur = db.cursor()
    cur.execute('DELETE FROM prenotazioni WHERE id = %s', (obj_id,))
    db.commit()
    db.close()
    return render_template('blog/message.html', message="Prenotazione Annullata")
    
    
@bp.route('/prenota', methods=('POST',))
@login_required
def prenota():
    global currentPage
    global currentDate
    location = "venezia"
    if currentPage == "Mestre Oggi" or currentPage == "Mestre Domani":
        location = "mestre"
    if request.method == 'POST':
        data = request.form
        nPosto = int(data["nPosto"])
        dalle = data["dalle"]
        alle = data["alle"]
        currentLoc = "venezia"
        if currentPage == "Mestre Oggi" or currentPage == "Mestre Domani":
            currentLoc = "mestre"
            if nPosto > 10 or nPosto < 1:
                return "numero posto non valido"
        elif currentPage == "Venezia Oggi" or currentPage == "Venezia Domani":
            if nPosto > 15 or nPosto < 1:
                return "numero posto non valido"
        else:
            return "errore currentPage string"
        if int(dalle) >= int(alle):
            return "errore date"
        if int(alle) - int(dalle) < 6:
            return "errore : devi prenotare almeno 6 ore"
        db = get_db()
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            'SELECT * FROM prenotazioni WHERE location = %s',
            (location,)
        )
        prenotazioni = cur.fetchall()
        db.close()
        weekDay = currentDate.date().weekday()
        currentDayType = "feriale"
        if weekDay == 5:
            currentDayType = "sabato"
        if weekDay == 6 or isFestivo(currentDate.date()):
            currentDayType = "festivo"
        res = [pren for pren in prenotazioni if pren["repeat"] == currentDayType or (pren["repeat"] == "no" and pren["giorno"].date() == currentDate.date())]
        
        if len(res) > 0:
            if g.user['username'] != "2959796":
                test = [p for p in res if p["matricola"] == g.user['username']]
                if len(test) > 0:
                    return render_template('blog/message.html', message="errore : hai gia prenotato per questo giorno")
            prenInPosto = [r for r in res if r["n_parcheggio"] == nPosto]
            ranges = []
            ranges.clear()
            for pren in prenInPosto:
                ranges.append(range(pren["dalle_ore"],pren["alle_ore"]))
            rangeToTest = range(int(dalle),int(alle))
            if len(ranges) > 0:
                for r in ranges:
                    if overlaps(r,rangeToTest):
                        return render_template('blog/message.html', message="Errore : fascia già prenotata")
        db = get_db()
        cur = db.cursor()
        cur.execute(
            'INSERT INTO prenotazioni (author_id, matricola, n_parcheggio, dalle_ore, alle_ore, giorno, location, repeat, note )'
            ' VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
            (g.user['id'], g.user['username'], nPosto, dalle, alle, currentDate, currentLoc, "no", "")
        )
        db.commit()
        db.close()
    p = currentPage
    return render_template('blog/message.html', message="Prenotazione Eseguita")

@bp.route('/eliminaUtente', methods=('POST',))
@login_required
def eliminaUtente():
    if request.method == 'POST':
        data = request.form
        db = get_db()
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            'SELECT * FROM users WHERE username = %s',
            (data["matricola"],)
        )
        utente = cur.fetchall()
        db.close()
        if len(utente) > 1:
            return "errore: esistono piu utenti con matricola " + data["matricola"]
        if len(utente) == 0:
            return "errore: non esistono utenti con matricola " + data["matricola"]
        db = get_db()
        cur = db.cursor()
        cur.execute('DELETE FROM users WHERE id = %s', (utente[0]["id"],))
        db.commit()
        db.close()
    return render_template('blog/message.html', message="Utente Eliminato")
    
@bp.route('/aggiungiAdmin', methods=('POST',))
@login_required
def aggiungiAdmin():
    if request.method == 'POST':
        data = request.form
        db = get_db()
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            'SELECT * FROM users WHERE username = %s',
            (data["mat"],)
        )
        utente = cur.fetchall()
        db.close()
        if len(utente) == 0:
            return "matricola " + data["mat"] + " non trovata"
        db = get_db()
        cur = db.cursor()
        cur.execute(
            'UPDATE users SET admin = %s'
            ' WHERE id = %s',
            (1, int(utente[0]["id"]))
            )
        db.commit()
        db.close()
    return render_template('blog/message.html', message="aggiunto admin " + data["mat"])
    
@bp.route('/rimuoviAdmin', methods=('POST',))
@login_required
def rimuoviAdmin():
    if request.method == 'POST':
        data = request.form
        db = get_db()
        cur = db.cursor()
        cur.execute(
            'UPDATE users SET admin = %s'
            ' WHERE username = %s',
            (0, data["matricola"])
            )
        db.commit()
        db.close()
    return render_template('blog/message.html', message="rimosso admin " + data["matricola"])
    
def overlaps(x, y):
    return max(x.start,y.start) < min(x.stop+1,y.stop+1)
    
def isFestivo(date):
    if date.month == 1 and date.day == 1:
        return True
    if date.month == 1 and date.day == 6:
        return True
    if date.month == 4 and date.day == 6:
        return True
    if date.month == 4 and date.day == 25:
        return True
    if date.month == 5 and date.day == 1:
        return True
    if date.month == 6 and date.day == 2:
        return True
    if date.month == 8 and date.day == 15:
        return True
    if date.month == 11 and date.day == 1:
        return True
    if date.month == 12 and date.day == 8:
        return True
    if date.month == 12 and date.day == 25:
        return True
    if date.month == 12 and date.day == 26:
        return True
    if date.month == 12 and date.day == 31:
        return True
    return False
