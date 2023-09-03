#!/usr/bin/env python3

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

from flask import current_app
from flask import send_file, send_from_directory

from werkzeug.utils import secure_filename, safe_join

from PIL import Image

from werkzeug.exceptions import abort

from imgindex.auth import login_required
from imgindex.db import get_db

import datetime
import os

import numpy as np

bp = Blueprint('search', __name__)

sort_mode = np.array([False, False , False, False])

@bp.route('/')
@login_required
# def index():
#     db = get_db()
#     images = db.execute(
#         'SELECT i.id, username, created, taken, width, height, file_size, file_name, owner'
#         ' FROM image i JOIN user u ON i.owner = u.id'
#         ' ORDER BY created ASC'
#     ).fetchall()

#     return render_template('search/index.html', images=images)

def index():
    db = get_db()
    sort_type = request.args.get('sort', 'date')
    query = 'SELECT i.id, username, created, taken, width, height, file_size, file_name, owner'+' FROM image i JOIN user u ON i.owner = u.id'+' ORDER BY '
    global sort_mode

    if np.logical_or.reduce(sort_mode) == True: s_mode = 'desc' 
    else: s_mode = 'asc'

    if sort_type == "date":
        if sort_mode[0] == False:
            sort_mode[0] = True
            query += 'created ASC'
        else:
            sort_mode[0] = False
            query += 'created DESC'
        u_sort_mode = np.array([sort_mode[0], False, False, False])
        sort_mode = u_sort_mode
    elif sort_type == "size":
        if sort_mode[1] == False:
            sort_mode[1] = True
            query += 'file_size ASC'
        else:
            sort_mode[1] = False
            query += 'file_size DESC'
        u_sort_mode = np.array([ False, sort_mode[1],False, False])
        sort_mode = u_sort_mode
    elif sort_type == "user":
        if sort_mode[2] == False:
            sort_mode[2] = True
            query += 'owner ASC'
        else:
            sort_mode[2] = False
            query += 'owner DESC'
        u_sort_mode = np.array([ False, False, sort_mode[2], False])
        sort_mode = u_sort_mode        

    elif sort_type == "name":
        if sort_mode[3] == False:
            sort_mode[3] = True
            query += 'file_name ASC'
        else:
            sort_mode[3] = False
            query += 'file_name DESC'
        u_sort_mode = np.array([ False, False, False, sort_mode[3]])
        sort_mode = u_sort_mode
 
    images = db.execute(query).fetchall()
    return render_template('search/index.html', images=images, prev_sort_opt = sort_type, s_mode = s_mode)

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

@bp.route('/uploads/<id>')
def send_uploaded_file(id):
    image = get_image(id)
    root_dir = os.getcwd()
    return send_from_directory(root_dir, image['file_name'])

        # images = db.execute(
        #     'SELECT i.id, username, created, taken, width, height, file_size, file_name, owner'
        #     ' FROM image i JOIN user u ON i.owner = u.id'
        #     ' ORDER BY owner ASC'
        # ).fetchall()