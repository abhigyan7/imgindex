#!/usr/bin/env python3

import sqlite3
import sqlite_vss

import os

import click
from flask import current_app, g

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.enable_load_extension(True)
        sqlite_vss.load(g.db)

    return g.db

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()
    return

def init_db():
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf-8'))
    os.mkdir(f"{current_app.config['UPLOAD_FOLDER']}")
    return

@click.command('init-db')
def init_db_command():
    init_db()
    click.echo("Initialized the database.")
    return

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
