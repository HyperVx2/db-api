
# -*- coding: utf-8 -*-

"""server: db-api."""

from __future__ import absolute_import

__version__ = '1.0.6'

import base64
import decimal
import json
from datetime import datetime

import flask.json
from flask import Flask
from flask import request
from flask import jsonify
from flask import send_file
from werkzeug.exceptions import HTTPException
from flask_cors import CORS
from io import BytesIO

import mysql.connector

try:
    from .google_directory import create_client_from_env
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    create_client_from_env = None


class AppJSONEncoder(json.JSONEncoder):
    """app: json encoder."""

    def default(self, o):
        """default: self."""
        if isinstance(o, decimal.Decimal):
            # Convert decimal instance to string
            return str(o)

        if isinstance(o, bytes):
            # Convert bytes instance to string, json
            try:
                o = o.decode('utf-8')
                try:
                    o = json.loads(o)
                    return o
                except json.decoder.JSONDecodeError:
                    return str(o)

            except UnicodeDecodeError:
                return str(o)

        if isinstance(o, bytearray):
            # Convert bytearray instance to string
            o = o.decode('utf-8')
            return str(o)

        return super().default(o)


APP = Flask(__name__)
CORS(APP, support_credentials=True)

APP.json_encoder = AppJSONEncoder
APP.config['JSONIFY_PRETTYPRINT_REGULAR'] = True     # default False
APP.config['JSON_SORT_KEYS'] = False                 # default True
APP.config['JSONIFY_MIMETYPE'] = 'application/json'  # default 'application/json'


@APP.route("/", methods=['GET'])
def root():
    """GET: Show Status."""
    return jsonify(status=200, message="OK", version=__version__), 200


@APP.route("/api", methods=['GET'])
def show_databases():
    """GET: /api Show Databases."""
    sql = "SHOW DATABASES"
    rows = fetchall(sql)
    return jsonify(rows), 200


@APP.route("/api/<database>", methods=['GET'])
def show_tables(database=None):
    """GET: /api/<database> Show Database Tables."""
    database = request.view_args['database']
    sql = "SHOW TABLES FROM " + database
    rows = fetchall(sql)
    return jsonify(rows), 200


@APP.route("/api/<database>/<table>", methods=['GET'])
def get_many(database=None, table=None):
    """GET: /api/<database>/<table> Show Database Table fields."""
    # ?query=true List rows of table. fields=id,name&limit=2,5
    database = request.view_args['database']
    table = request.view_args['table']

    fields = request.args.get("fields", '*')
    limit = request.args.get("limit", None)

    if not request.query_string:
        sql = "SHOW FIELDS FROM " + database + "." + table
    else:
        sql = "SELECT " + fields + " FROM " + database + "." + table

    if limit:
        sql += " LIMIT " + limit

    rows = fetchall(sql)

    if rows:
        return jsonify(rows), 200

    return jsonify(status=404, message="Not Found"), 404


@APP.route("/api/<database>/<table>/<key>", methods=['GET'])
def get_one(database=None, table=None, key=None):
    """GET: /api/<database>/<table>:id."""
    # Retrieve a row by primary key. id?fields= fields=&column=
    database = request.view_args['database']
    table = request.view_args['table']
    key = request.view_args['key']

    fields = request.args.get("fields", '*')
    column = request.args.get("column", 'id')

    sql = "SELECT " + fields + " FROM " + database + "." + table
    sql += " WHERE " + column + "='" + key + "'"

    row = fetchone(sql)

    if row:
        return jsonify(row), 200

    return jsonify(status=404, message="Not Found"), 404

@APP.route("/api/<database>/rfid/users", methods=['GET'])
def get_rfid_users(database=None):
    """GET: /api/<database>/rfid/users -> list of user_id, rfid_uid, and type.

    Returns a list of all users with their RFID UIDs from user_rfid table.

    Response:
    - 200: [{"user_id": str, "rfid_uid": str, "type": str}, ...]
    - 404: {status: 404, message: "Not Found"}
    """
    database = request.view_args['database']

    sql = "SELECT user_id, rfid_uid, type FROM " + database + ".user_rfid"

    rows = fetchall(sql)

    if rows:
        result = [{"user_id": row[0], "rfid_uid": row[1], "type": row[2]} for row in rows]
        return jsonify(result), 200

    return jsonify(status=404, message="Not Found"), 404


@APP.route("/api/<database>/rfid/<rfidUID>", methods=['GET'])
def get_user_by_rfid(database=None, rfidUID=None):
    """GET: /api/<database>/rfid/<rfidUID> -> user by RFID UID.

    Returns the complete user record from user_rfid table by RFID UID.

    Response:
    - 200: {"user_id": str, "rfid_uid": str, "type": str}
    - 404: {status: 404, message: "Not Found"}
    """
    database = request.view_args['database']
    rfidUID = request.view_args['rfidUID']

    sql = "SELECT user_id, rfid_uid, type FROM " + database + ".user_rfid WHERE rfid_uid=%s LIMIT 1"

    row = fetchone_params(sql, (rfidUID,))

    if row:
        return jsonify({"user_id": row[0], "rfid_uid": row[1], "type": row[2]}), 200

    return jsonify(status=404, message="Not Found"), 404


@APP.route("/api/<database>/google/sync", methods=['POST'])
def sync_google_users(database=None):
    """POST: /api/<database>/google/sync.
    
    Sync all Google Workspace users to database.
    
    Response:
    - 201: {"status": 201, "message": "Sync completed", "users_synced": int}
    - 503: {"status": 503, "message": "Google API not available"}
    - 500: {"status": 500, "message": error message}
    """
    database = request.view_args['database']
    
    if not GOOGLE_AVAILABLE:
        return jsonify(status=503, message="Google API not configured"), 503
    
    try:
        google_client = create_client_from_env()
        if not google_client:
            return jsonify(status=503, 
                         message="Google credentials not configured"), 503
        
        # Log sync start
        log_id = log_sync_start(database, 'full')
        
        # Fetch all users from Google
        users = google_client.list_all_users()
        
        # Sync users to database
        users_synced = 0
        for user in users:
            if sync_user_to_db(database, user):
                users_synced += 1
        
        # Log sync completion
        log_sync_complete(database, log_id, users_synced, 0)
        
        return jsonify(status=201,
                      message="Sync completed",
                      users_synced=users_synced), 201
                      
    except Exception as e:
        log_sync_failed(database, log_id, str(e))
        return jsonify(status=500, message=str(e)), 500


@APP.route("/api/<database>/google/sync/photos", methods=['POST'])
def sync_google_photos(database=None):
    """POST: /api/<database>/google/sync/photos.
    
    Sync all Google Workspace user photos to database.
    
    Response:
    - 201: {"status": 201, "message": "Photo sync completed", "photos_synced": int}
    - 503: {"status": 503, "message": "Google API not available"}
    - 500: {"status": 500, "message": error message}
    """
    database = request.view_args['database']
    
    if not GOOGLE_AVAILABLE:
        return jsonify(status=503, message="Google API not configured"), 503
    
    try:
        google_client = create_client_from_env()
        if not google_client:
            return jsonify(status=503,
                         message="Google credentials not configured"), 503
        
        # Log sync start
        log_id = log_sync_start(database, 'photo')
        
        # Get all user IDs from database
        sql = "SELECT id, primary_email FROM " + database + ".google_users"
        users = fetchall(sql)
        
        photos_synced = 0
        for user_row in users:
            user_id = user_row[0]
            email = user_row[1]
            
            # Fetch photo from Google
            photo_result = google_client.get_user_photo(email)
            if photo_result:
                photo_data, mime_type = photo_result
                if sync_photo_to_db(database, user_id, photo_data, mime_type):
                    photos_synced += 1
        
        # Log sync completion
        log_sync_complete(database, log_id, 0, photos_synced)
        
        return jsonify(status=201,
                      message="Photo sync completed",
                      photos_synced=photos_synced), 201
                      
    except Exception as e:
        log_sync_failed(database, log_id, str(e))
        return jsonify(status=500, message=str(e)), 500


@APP.route("/api/<database>/google/users", methods=['GET'])
def get_google_users(database=None):
    """GET: /api/<database>/google/users.
    
    Get all synced Google Workspace users from database.
    Query params: limit (optional)
    
    Response:
    - 200: [{user fields}, ...]
    - 404: {"status": 404, "message": "Not Found"}
    """
    database = request.view_args['database']
    limit = request.args.get("limit", None)
    
    sql = (
        "SELECT id, primary_email, given_name, family_name, external_id, "
        "department, org_description, suspended, is_admin, last_login_time, synced_at "
        "FROM " + database + ".google_users ORDER BY primary_email"
    )
    
    if limit:
        sql += " LIMIT " + limit
    
    rows = fetchall(sql)
    
    if rows:
        result = []
        for row in rows:
            result.append({
                "id": row[0],
                "primaryEmail": row[1],
                "givenName": row[2],
                "familyName": row[3],
                "externalId": row[4],
                "department": row[5],
                "orgDescription": row[6],
                "suspended": bool(row[7]),
                "isAdmin": bool(row[8]),
                "lastLoginTime": row[9].isoformat() if row[9] else None,
                "syncedAt": row[10].isoformat() if row[10] else None,
            })
        return jsonify(result), 200
    
    return jsonify(status=404, message="Not Found"), 404


@APP.route("/api/<database>/google/users/<userKey>", methods=['GET'])
def get_google_user(database=None, userKey=None):
    """GET: /api/<database>/google/users/<userKey>.
    
    Get specific synced Google user by email or ID.
    
    Response:
    - 200: {user fields}
    - 404: {"status": 404, "message": "Not Found"}
    """
    database = request.view_args['database']
    user_key = request.view_args['userKey']
    
    sql = (
        "SELECT id, primary_email, given_name, family_name, external_id, "
        "department, org_description, suspended, is_admin, last_login_time, synced_at "
        "FROM " + database + ".google_users "
        "WHERE primary_email=%s OR external_id=%s LIMIT 1"
    )
    
    row = fetchone_params(sql, (user_key, user_key))
    
    if row:
        return jsonify({
            "id": row[0],
            "primaryEmail": row[1],
            "givenName": row[2],
            "familyName": row[3],
            "externalId": row[4],
            "department": row[5],
            "orgDescription": row[6],
            "suspended": bool(row[7]),
            "isAdmin": bool(row[8]),
            "lastLoginTime": row[9].isoformat() if row[9] else None,
            "syncedAt": row[10].isoformat() if row[10] else None,
        }), 200
    
    return jsonify(status=404, message="Not Found"), 404


@APP.route("/api/<database>/google/users/<userKey>/photo", methods=['GET'])
def get_google_user_photo(database=None, userKey=None):
    """GET: /api/<database>/google/users/<userKey>/photo.
    
    Get synced Google user photo by email or ID.
    Returns image directly with proper MIME type.
    
    Response:
    - 200: Binary image data
    - 404: {"status": 404, "message": "Not Found"}
    """
    database = request.view_args['database']
    user_key = request.view_args['userKey']
    
    # First get user ID from email or ID
    sql_user = (
        "SELECT id FROM " + database + ".google_users "
        "WHERE primary_email=%s OR id=%s LIMIT 1"
    )
    user_row = fetchone_params(sql_user, (user_key, user_key))
    
    if not user_row:
        return jsonify(status=404, message="User not found"), 404
    
    user_id = user_row[0]
    
    # Get photo
    sql_photo = (
        "SELECT photo_data, mime_type FROM " + database + ".google_user_photos "
        "WHERE user_id=%s LIMIT 1"
    )
    photo_row = fetchone_params(sql_photo, (user_id,))
    
    if photo_row and photo_row[0]:
        photo_data = photo_row[0]
        mime_type = photo_row[1] or 'image/jpeg'
        return send_file(
            BytesIO(photo_data),
            mimetype=mime_type,
            as_attachment=False
        )
    
    return jsonify(status=404, message="Photo not found"), 404


@APP.route("/api/<database>/attendance/log", methods=['POST'])
def log_user_attendance(database=None):
    """POST: /api/<database>/attendance/log.
    
    Log user attendance/login.
    
    Request Body (JSON):
    {
        "userID": "string",
        "primaryEmail": "string"
    }
    
    Response:
    - 201: {"status": 201, "message": "Attendance logged", "id": int}
    - 400: {"status": 400, "message": "Missing required fields"}
    - 500: {"status": 500, "message": error message}
    """
    database = request.view_args['database']
    
    if not request.is_json:
        return jsonify(status=400, message="Content-Type must be application/json"), 400
    
    data = request.get_json()
    
    user_id = data.get('userID')
    primary_email = data.get('primaryEmail')
    
    if not user_id or not primary_email:
        return jsonify(status=400, 
                      message="Missing required fields: userID and primaryEmail"), 400
    
    try:
        # Get current datetime
        login_time = datetime.now()
        
        # Insert attendance record
        cnx = sql_connection()
        cur = cnx.cursor(buffered=True)
        
        sql = (
            "INSERT INTO " + database + ".user_attendance "
            "(user_id, primary_email, login_time) VALUES (%s, %s, %s)"
        )
        
        cur.execute(sql, (user_id, primary_email, login_time))
        cnx.commit()
        
        attendance_id = cur.lastrowid
        
        cur.close()
        cnx.close()
        
        return jsonify(status=201,
                      message="Attendance logged",
                      id=attendance_id,
                      loginTime=login_time.isoformat()), 201
    
    except Exception as e:
        return jsonify(status=500, message=str(e)), 500


@APP.route("/api", methods=['POST'])
def post_api():
    """POST: /api."""
    if request.is_json:
        return jsonify(status=415, post='json'), 415

    if request.form:
        return jsonify(status=415, post='form'), 415

    if request.files:
        return jsonify(status=415, post='files'), 415

    if request.stream:

        if request.content_type == 'image/jpg':
            return jsonify(status=415, post='stream', content_type='image/jpg'), 415

        if request.content_type == 'application/octet-stream':
            return jsonify(status=415,
                           post='stream',
                           content_type='application/octet-stream'), 415

        if str(request.content_type).lower().startswith('text/plain'):
            return jsonify(status=415, post='stream', content_type='text/plain'), 415

        if str(request.content_type).lower().startswith('text/sql'):
            return post_sql()

        return jsonify(status=415, post='stream'), 415

    return jsonify(status=415,
                   error='Unsupported Media Type',
                   method='POST'), 415


@APP.route("/api/<database>/<table>", methods=['POST'])
def post_insert(database=None, table=None):
    """POST: /api/<database>/<table>."""
    # Create a new row. key1=val1,key2=val2.
    database = request.view_args['database']
    table = request.view_args['table']

    if request.is_json:
        return post_json(database, table)

    if request.form:
        return post_form(database, table)

    _return = {'status': 417,
               'message': 'Expectation Failed',
               'details': 'Can Not Meet Expectation: request-header field',
               'method': 'POST',
               'insert': False}
    return jsonify(_return), 417


@APP.route("/api/<database>/<table>/<key>", methods=['DELETE'])
def delete_one(database=None, table=None, key=None):
    """DELETE: /api/<database>/<table>:id."""
    # Delete a row by primary key id?column=
    database = request.view_args['database']
    table = request.view_args['table']
    key = request.view_args['key']

    column = request.args.get("column", 'id')

    sql = "DELETE FROM " + database + "." + table
    sql += " WHERE " + column + "='" + key + "'"

    delete = sqlcommit(sql)

    if delete > 0:
        return jsonify(status=211, message="Deleted", delete=True), 211

    return jsonify(status=466, message="Failed Delete", delete=False), 466


@APP.route("/api/<database>/<table>/<key>", methods=['PATCH'])
def patch_one(database=None, table=None, key=None):
    """PATCH: /api/<database>/<table>:id."""
    # Update row element by primary key (single key/val) id?column=
    database = request.view_args['database']
    table = request.view_args['table']
    key = request.view_args['key']

    column = request.args.get("column", 'id')

    if not request.headers['Content-Type'] == 'application/json':
        return jsonify(status=412, errorType="Precondition Failed"), 412

    post = request.get_json()

    if len(post) > 1:
        _return = {'status': 405,
                   'errorType': 'Method Not Allowed',
                   'errorMessage': 'Single Key-Value Only',
                   'update': False}
        return jsonify(_return), 405

    for _key in post:
        field = _key
        value = post[_key]

    sql = "UPDATE " + database + "." + table
    sql += " SET " + field + "='" + value + "' WHERE " + column + "='" + key + "'"

    update = sqlcommit(sql)

    if update > 0:
        return jsonify(status=201, message="Created", update=True), 201

    return jsonify(status=465, message="Failed Update", update=False), 465


@APP.route("/api/<database>/<table>", methods=['PUT'])
def put_replace(database=None, table=None):
    """PUT: /api/<database>/<table>."""
    # Replace existing row with new row. key1=val1,key2=val2."""
    database = request.view_args['database']
    table = request.view_args['table']

    if not request.headers['Content-Type'] == 'application/json':
        return jsonify(status=412, errorType="Precondition Failed"), 412

    post = request.get_json()

    placeholders = ['%s'] * len(post)

    fields = ",".join([str(key) for key in post])
    places = ",".join([str(key) for key in placeholders])

    records = []
    for key in post:
        records.append(post[key])

    sql = "REPLACE INTO " + database + "." + table
    sql += " (" + fields + ") VALUES (" + places + ")"

    replace = sqlexec(sql, records)

    if replace > 0:
        return jsonify(status=201,
                       message="Created",
                       replace=True,
                       rowid=replace), 201

    return jsonify(status=461, message="Failed Create", replace=False), 461


@APP.errorhandler(404)
def not_found(_e=None):
    """Not_Found: HTTP File Not Found 404."""
    message = {'status': 404, 'errorType': 'Not Found: ' + request.url}
    return jsonify(message), 404


@APP.errorhandler(Exception)
def handle_exception(_e):
    """Exception: HTTP Exception."""
    if isinstance(_e, HTTPException):
        return jsonify(status=_e.code,
                       errorType="HTTP Exception",
                       errorMessage=str(_e)), _e.code

    if type(_e).__name__ == 'OperationalError':
        return jsonify(status=512,
                       errorType="OperationalError",
                       errorMessage=str(_e)), 512

    if type(_e).__name__ == 'InterfaceError':
        return jsonify(status=512,
                       errorType="InterfaceError",
                       errorMessage=str(_e)), 512

    if type(_e).__name__ == 'ProgrammingError':
        return jsonify(status=512,
                       errorType="ProgrammingError",
                       errorMessage=str(_e)), 512

    if type(_e).__name__ == 'AttributeError':
        return jsonify(status=512,
                       errorType="AttributeError",
                       errorMessage=str(_e)), 512

    res = {'status': 500, 'errorType': 'Internal Server Error'}
    res['errorMessage'] = str(_e)
    return jsonify(res), 500


def post_sql():
    """post: sql."""
    post = request.data
    sql = post.decode('utf-8')

    cnx = sql_connection()
    cur = cnx.cursor(buffered=True)

    try:
        for result in cur.execute(sql, multi=True):

            if result.with_rows:
                return jsonify(result.fetchall()), 200

            cnx.commit()
            return jsonify(status=201,
                           statment=result.statement,
                           rowcount=result.rowcount,
                           lastrowid=result.lastrowid), 201
    finally:
        cur.close()
        cnx.close()

    return jsonify(status=202, method='POST'), 202


def post_json(database, table):
    """post: json data application/json."""
    post = request.get_json()

    placeholders = ['%s'] * len(post)

    fields = ",".join([str(key) for key in post])
    places = ",".join([str(key) for key in placeholders])

    records = []
    for key in post:
        records.append(post[key])

    sql = "INSERT INTO " + database + "." + table
    sql += " (" + fields + ") VALUES (" + places + ")"

    insert = sqlexec(sql, records)

    if insert > 0:
        return jsonify(status=201,
                       message="Created",
                       insert=True,
                       rowid=insert), 201

    return jsonify(status=461, message="Failed Create", insert=False), 461


def post_form(database, table):
    """post: form data application/x-www-form-urlencoded."""
    credentials = request.form.get('credentials', None)

    if credentials:

        columns = []
        records = []
        for key in request.form.keys():
            if key == 'credentials':
                continue
            columns.append(key)
            records.append(request.form[key])

        count = len(request.form) - 1
        placeholders = ['%s'] * count

        places = ",".join([str(key) for key in placeholders])

        fields = ",".join([str(key) for key in columns])

        base64_user, base64_pass = base64_untoken(credentials.encode('ascii'))

        sql = "INSERT INTO " + database + "." + table
        sql += " (" + fields + ") VALUES (" + places + ")"

        insert = sqlinsert(sql, records, base64_user, base64_pass)

        if insert > 0:
            return jsonify(status=201,
                           message="Created",
                           method="POST",
                           insert=True,
                           rowid=insert), 201

        return jsonify(status=461,
                       message="Failed Create",
                       method="POST",
                       insert=False), 461

    return jsonify(status=401,
                   message='Unauthorized',
                   details='No valid authentication credentials for target resource',
                   method='POST',
                   insert=False), 401


def base64_untoken(base64_bytes):
    """base64: untoken."""
    token_bytes = base64.b64decode(base64_bytes)
    untoken = token_bytes.decode('ascii')
    base64_user = untoken.split(":", 1)[0]
    base64_pass = untoken.split(":", 1)[1]
    return base64_user, base64_pass


def fetchall(sql):
    """sql: fetchall."""
    cnx = sql_connection()
    cur = cnx.cursor(buffered=True)
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    cnx.close()
    return rows


def fetchone(sql):
    """sql: fetchone."""
    cnx = sql_connection()
    cur = cnx.cursor(buffered=True)
    cur.execute(sql)
    row = cur.fetchone()
    cur.close()
    cnx.close()
    return row


def fetchone_params(sql, params):
    """sql: fetchone with params."""
    cnx = sql_connection()
    cur = cnx.cursor(buffered=True)
    cur.execute(sql, params)
    row = cur.fetchone()
    cur.close()
    cnx.close()
    return row


def sqlexec(sql, values):
    """sql: exec values."""
    cnx = sql_connection()
    cur = cnx.cursor(buffered=True)
    cur.execute(sql, values)
    cnx.commit()
    lastrowid = cur.lastrowid
    cur.close()
    cnx.close()
    return lastrowid


def sqlcommit(sql):
    """sql: commit."""
    cnx = sql_connection()
    cur = cnx.cursor(buffered=True)
    cur.execute(sql)
    cnx.commit()
    rowcount = cur.rowcount
    cur.close()
    cnx.close()
    return rowcount


def sqlinsert(sql, values, user, password):
    """sql: insert values, user, password."""
    cnx = sql_connection(user, password)
    cur = cnx.cursor(buffered=True)
    cur.execute(sql, values)
    cnx.commit()
    lastrowid = cur.lastrowid
    cur.close()
    cnx.close()
    return lastrowid


def sql_connection(user=None, password=None):
    """sql: connection."""
    if not user:
        user = request.authorization.username

    if not password:
        password = request.authorization.password

    config = {
        'user':                   user,
        'password':               password,
        'host':                   request.headers.get('X-Host', '127.0.0.1'),
        'port':               int(request.headers.get('X-Port', '3306')),
        'database':               request.headers.get('X-Db', ''),
        'raise_on_warnings':      request.headers.get('X-Raise-Warnings', True),
        'get_warnings':           request.headers.get('X-Get-Warnings', True),
        'auth_plugin':            request.headers.get('X-Auth-Plugin', 'mysql_native_password'),
        'use_pure':               request.headers.get('X-Pure', True),
        'use_unicode':            request.headers.get('X-Unicode', True),
        'charset':                request.headers.get('X-Charset', 'utf8'),
        'connection_timeout': int(request.headers.get('X-Connection-Timeout', 10)),
    }
    _db = mysql.connector.connect(**config)
    return _db


def sync_user_to_db(database, user):
    """Sync Google user data to database.
    
    Args:
        database: Database name
        user: User dictionary from Google API
        
    Returns:
        Boolean indicating success
    """
    try:
        cnx = sql_connection()
        cur = cnx.cursor(buffered=True)
        
        # Parse last login time
        last_login = None
        if user.get('lastLoginTime'):
            try:
                # Google format: 2023-11-27T10:30:00.000Z
                last_login = datetime.fromisoformat(
                    user['lastLoginTime'].replace('Z', '+00:00')
                )
            except (ValueError, AttributeError):
                pass
        
        sql = (
            "REPLACE INTO " + database + ".google_users "
            "(id, primary_email, given_name, family_name, external_id, "
            "department, org_description, suspended, is_admin, last_login_time) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        
        values = (
            user.get('id'),
            user.get('primaryEmail'),
            user.get('givenName'),
            user.get('familyName'),
            user.get('externalId'),
            user.get('department'),
            user.get('orgDescription'),
            user.get('suspended', False),
            user.get('isAdmin', False),
            last_login
        )
        
        cur.execute(sql, values)
        cnx.commit()
        cur.close()
        cnx.close()
        return True
        
    except Exception as e:
        print(f"Error syncing user {user.get('primaryEmail')}: {e}")
        return False


def sync_photo_to_db(database, user_id, photo_data, mime_type):
    """Sync Google user photo to database.
    
    Args:
        database: Database name
        user_id: Google user ID
        photo_data: Binary photo data
        mime_type: Photo MIME type
        
    Returns:
        Boolean indicating success
    """
    try:
        cnx = sql_connection()
        cur = cnx.cursor(buffered=True)
        
        sql = (
            "REPLACE INTO " + database + ".google_user_photos "
            "(user_id, photo_data, mime_type) VALUES (%s, %s, %s)"
        )
        
        cur.execute(sql, (user_id, photo_data, mime_type))
        cnx.commit()
        cur.close()
        cnx.close()
        return True
        
    except Exception as e:
        print(f"Error syncing photo for user {user_id}: {e}")
        return False


def log_sync_start(database, sync_type):
    """Log the start of a sync operation.
    
    Args:
        database: Database name
        sync_type: Type of sync ('full', 'user', 'photo')
        
    Returns:
        Log ID
    """
    try:
        cnx = sql_connection()
        cur = cnx.cursor(buffered=True)
        
        sql = (
            "INSERT INTO " + database + ".google_sync_log "
            "(sync_type, sync_status) VALUES (%s, %s)"
        )
        
        cur.execute(sql, (sync_type, 'started'))
        cnx.commit()
        log_id = cur.lastrowid
        cur.close()
        cnx.close()
        return log_id
        
    except Exception as e:
        print(f"Error logging sync start: {e}")
        return None


def log_sync_complete(database, log_id, users_synced, photos_synced):
    """Log the completion of a sync operation.
    
    Args:
        database: Database name
        log_id: Log entry ID
        users_synced: Number of users synced
        photos_synced: Number of photos synced
    """
    try:
        cnx = sql_connection()
        cur = cnx.cursor(buffered=True)
        
        sql = (
            "UPDATE " + database + ".google_sync_log "
            "SET sync_status=%s, users_synced=%s, photos_synced=%s, "
            "completed_at=NOW() WHERE id=%s"
        )
        
        cur.execute(sql, ('completed', users_synced, photos_synced, log_id))
        cnx.commit()
        cur.close()
        cnx.close()
        
    except Exception as e:
        print(f"Error logging sync completion: {e}")


def log_sync_failed(database, log_id, error_message):
    """Log a failed sync operation.
    
    Args:
        database: Database name
        log_id: Log entry ID
        error_message: Error message
    """
    try:
        cnx = sql_connection()
        cur = cnx.cursor(buffered=True)
        
        sql = (
            "UPDATE " + database + ".google_sync_log "
            "SET sync_status=%s, error_message=%s, completed_at=NOW() "
            "WHERE id=%s"
        )
        
        cur.execute(sql, ('failed', error_message, log_id))
        cnx.commit()
        cur.close()
        cnx.close()
        
    except Exception as e:
        print(f"Error logging sync failure: {e}")


def main():
    """main: app."""
    APP.run(port=8980, debug=False)


if __name__ == "__main__":
    main()
