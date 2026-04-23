import sqlite3
from datetime import datetime

import click
from flask import current_app, g
import psycopg2
from psycopg2 import pool



def get_db():
    #g.db = psycopg2.connect("postgresql://neondb_owner:npg_xEAwknidml13@ep-tiny-forest-amdj78wg-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")
    db = psycopg2.connect(dbname='neondb', 
                                user='neondb_owner', 
                                password='npg_xEAwknidml13', 
                                host='ep-tiny-forest-amdj78wg-pooler.c-5.us-east-1.aws.neon.tech', 
                                port='5432', 
                                sslmode='require',
                                channel_binding='require')
    return db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()
        
def init_db():
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        curr = db.cursor()
        curr.execute(f.read().decode('utf8'))
        db.commit()
        db.close()


@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')


sqlite3.register_converter(
    "timestamp", lambda v: datetime.fromisoformat(v.decode())
)
def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)