#!/usr/bin/env python3

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

from flask import current_app
from flask import send_file, send_from_directory

from werkzeug.utils import secure_filename, safe_join

from werkzeug.exceptions import abort

from imgindex.auth import login_required
from imgindex.db import get_db

import datetime
import os
import json

from PIL import Image
import torch
import clip
import numpy as np

import numpy as np

bp = Blueprint('search', __name__)
device = "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

@bp.route('/', methods=('GET', 'POST'))
@login_required
def index():
    db = get_db()
    query = request.form.get("query", "")
    sort_type = request.form.get('sort', 'created')
    sort_order = request.form.get('sort-order', 'DESC')

    current_app.logger.info(f"{sort_type=}")
    current_app.logger.info(f"{sort_order=}")

    if query == "":
        images = db.execute(
            'SELECT i.id, username, created, width, height, file_size, file_name, owner'
            ' FROM image i JOIN user u ON i.owner = u.id'
            ' ORDER BY {} {} ;'.format(sort_type, sort_order)
           ).fetchall()
        current_app.logger.info(f"{images=}")
        return render_template('search/index.html', images=images, sort_type=sort_type, sort_order=sort_order)

    query_embedding = model.encode_text(clip.tokenize([query])).to(device)[0]
    query_embedding = json.dumps(query_embedding.tolist())
    current_app.logger.info(f"{query_embedding}")
    images = db.execute(
        "WITH matches as ("
        "  SELECT rowid, distance FROM vss_image "
        "  WHERE vss_search(image_embedding, ?) limit 20"
        ")"
        "SELECT i.id, created, width, height, file_size, file_name, owner"
                            " FROM matches JOIN image i ON i.rowid = matches.rowid",
        [query_embedding] ).fetchall()
    current_app.logger.info(f"{images=}")

    return render_template('search/index.html', images=images, query=query, sort_type=sort_type, sort_order=sort_order)

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
        image_file = request.files['image_file']
        owner = g.user['id']
        error = None
        if image_file and allowed_file(image_file.filename):
            file_name = save_image_file(image_file)
            file_size, width, height = get_image_file_data(file_name)
            image_tensor = preprocess(Image.open(file_name)).unsqueeze(0).to(device)
            with torch.no_grad():
                image_features = model.encode_image(image_tensor).cpu().numpy()
        else:
            error = "Invalid file"

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO image (width, height, file_size, file_name, owner)'
                ' VALUES (?, ?, ?, ?, ?)',
                (width, height, file_size, file_name, owner)
            )
            db.commit()
            rowid = db.execute(
                "select rowid from image where image_embedding is null limit 1"
            ).fetchone()
            if rowid is None:
                current_app.logger.error(f"No image tuple with null embedding")
            current_app.logger.info(f"{rowid=}")
            db.execute(
                'UPDATE image SET image_embedding = ? where rowid = ?',
                [image_features[0].tobytes(), rowid[0]]
            )
            db.commit()
            db.execute("DELETE FROM vss_image;")
            db.commit()
            db.execute(
                "INSERT INTO vss_image (rowid, image_embedding)"
                "  SELECT rowid, image_embedding from image;"
            )
            db.commit()
            return redirect(url_for('search.index'))

    return render_template('search/create.html')

def get_image(id, check_owner=True):
    image = get_db().execute(
        'SELECT i.id, created, width, height, file_size, file_name, owner'
        ' FROM image i JOIN user u ON i.owner = u.id'
        ' where i.id = ?',
        (id,)
    ).fetchone()

    if image is None:
        abort(404, f"Image id {id} doesn't exist.")

    if check_owner and image['owner'] != g.user['id']:
        abort(403)

    return image

@bp.route('/<int:id>/detail', methods=('GET', 'POST'))
@login_required
def detail(id):
    image = get_image(id)
    return render_template('search/detail.html', image=image)

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
        #     'SELECT i.id, username, created, width, height, file_size, file_name, owner'
        #     ' FROM image i JOIN user u ON i.owner = u.id'
        #     ' ORDER BY owner ASC'
        # ).fetchall()
