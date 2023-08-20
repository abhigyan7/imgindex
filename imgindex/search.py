#!/usr/bin/env python3

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

from flask import current_app

from werkzeug.utils import secure_filename

from PIL import Image

from werkzeug.exceptions import abort

from imgindex.auth import login_required
from imgindex.db import get_db

import datetime
import os

bp = Blueprint('search', __name__)

@bp.route('/')
@login_required
def index():
    db = get_db()
    images = db.execute(
        'SELECT i.id, username, created, taken, width, height, file_size, file_name, owner'
        ' FROM image i JOIN user u ON i.owner = u.id'
        ' ORDER BY created DESC'
    ).fetchall()

    return render_template('search/index.html', images=images)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image_file(image_file):
    filename = secure_filename(image_file.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    image_file.save(filepath)
    return filepath

def get_image_file_data(filename):
    file_size = os.stat(filename).st_size
    image = Image.open(filename)
    width, height = image.size
    return file_size, width, height

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        try:
            taken = datetime.datetime.strptime(request.form['taken'], "%Y-%m-%d")
        except ValueError:
            # the taken field is empty
            taken = None
        image_file = request.files['image_file']
        owner = g.user['id']
        if image_file and allowed_file(image_file.filename):
            file_name = save_image_file(image_file)
            file_size, width, height = get_image_file_data(file_name)
        else:
            error = "Invalid file"

        error = None

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO image (taken, width, height, file_size, file_name, owner)'
                ' VALUES (?, ?, ?, ?, ?, ?)',
                (taken, width, height, file_size, file_name, owner)
            )
            db.commit()
            return redirect(url_for('search.index'))

    return render_template('search/create.html')

def get_image(id, check_owner=True):
    image = get_db().execute(
        'SELECT i.id, created, taken, width, height, file_size, file_name, owner'
        ' FROM image i JOIN user u ON i.owner = u.id'
        ' where i.id = ?',
        (id,)
    ).fetchone()

    if image is None:
        abort(404, f"Image id {id} doesn't exist.")

    if check_owner and image['owner'] != g.user['id']:
        abort(403)


    return image

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    image = get_image(id)

    if request.method == 'POST':
        taken = request.form['taken']
        owner = g.user['id']
        file_size, width, height = get_image_file_data(image['file_name'])

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

    if image['taken'] is not None:
        taken_rendered = datetime.datetime.strftime(image['taken'], "%Y-%m-%d")
    else:
        taken_rendered = None
    return render_template('search/update.html', image=image, taken_rendered=taken_rendered)

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    image = get_image(id)
    os.remove(image['file_name'])
    db = get_db()
    db.execute('DELETE FROM image WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('search.index'))
