#!/usr/bin/env python3

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

from werkzeug.exceptions import abort

from imgindex.auth import login_required
from imgindex.db import get_db

import datetime

bp = Blueprint('search', __name__)

@bp.route('/')
@login_required
def index():
    db = get_db()
    images = db.execute(
        'SELECT i.id, username, created, taken, width, height, file_size, owner'
        ' FROM image i JOIN user u ON i.owner = u.id'
        ' ORDER BY created DESC'
    ).fetchall()

    print(images)

    return render_template('search/index.html', images=images)

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        taken = datetime.datetime.strptime(request.form['taken'], "%Y-%m-%d")
        width = request.form['taken']
        height = request.form['height']
        file_size = request.form['file_size']
        owner = g.user['id']

        print(f"{taken}")

        error = None

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO image (taken, width, height, file_size, owner)'
                ' VALUES (?, ?, ?, ?, ?)',
                (taken, width, height, file_size, owner)
            )
            db.commit()
            return redirect(url_for('search.index'))

    return render_template('search/create.html')

def get_image(id, check_owner=True):
    image = get_db().execute(
        'SELECT i.id, created, taken, width, height, file_size, owner'
        ' FROM image i JOIN user u ON i.owner = u.id'
        ' where u.id = ?',
        (id,)
    ).fetchone()

    if image is None:
        abort(404, f"Image id {id} doesn't exist.")

    if check_author and image['owner_id'] != g.user['id']:
        abort(403)

    return post

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_image(id)

    if request.method == 'POST':
        taken = request.form['taken']
        width = request.form['taken']
        height = request.form['height']
        file_size = request.form['file_size']
        owner = g.user['id']

        error = None

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE image SET taken= ?, width= ?, height= ?, file_size= ?, owner= ?'
                ' WHERE id = ?',
                (taken, width, height, file_size, owner, id)
            )
            db.commit()
            return redirect(url_for('search.index'))

    return render_template('search/update.html', post=post)

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_image(id)
    db = get_db()
    db.execute('DELETE FROM image WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index'))
