import datetime
import json
import random
import string
import os
import os.path
import math
import subprocess

from flask import Flask, request, render_template, abort, send_from_directory, session, redirect, url_for
from flask_discord import DiscordOAuth2Session, requires_authorization, Unauthorized

import config
from db import pool

from magic import Magic

app = Flask(__name__)
app.secret_key = config.flask_secret
app.static_folder = "static"

# os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true"  # !! Only in development environment.

app.config["DISCORD_CLIENT_ID"] = config.oauth["OAUTH2_CLIENT_ID"]  # Discord client ID.
app.config["DISCORD_CLIENT_SECRET"] = config.oauth["OAUTH2_CLIENT_SECRET"]  # Discord client secret.
app.config["DISCORD_REDIRECT_URI"] = config.domain + "/callback"  # URL to your callback endpoint.

discord = DiscordOAuth2Session(app)

mime = Magic(mime=True)

app_info = {
    "name": config.name,
    "color": config.color
}


# size in human-readable size
# Made by Fred Cirera
def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


class User:
    def __init__(self, token):
        conn = pool.get_connection()
        cursor = conn.cursor()
        self.token = token
        cursor.execute("SELECT name, discord_id FROM users WHERE token=?", (self.token,))
        self._user = cursor.fetchone()
        self.is_logged = True if self._user else False
        self.name = self._user[0] if self.is_logged else None
        self.discord_id = self._user[1] if self.is_logged else None
        conn.close()


def generate_token(length):
    return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(length))


@app.route("/api/discord/")
def discord_login():
    return discord.create_session(["identify"])


@app.route("/api/login", methods=["POST"])
def api_login():
    if request.method == "POST":
        conn = pool.get_connection()
        cursor = conn.cursor()
        try:
            if not request.form["token"] or request.form["token"] == "":
                tmp = generate_token(25)
                cursor.execute("INSERT INTO users (token, ip) VALUES (?, ?)",
                               (tmp, request.headers['X-Forwarded-For']))
                session["token"] = tmp
            else:
                cursor.execute("SELECT (token) FROM users WHERE token=?", (request.form["token"],))

                is_token_exist = cursor.fetchone()
                if not is_token_exist:
                    return "Token is invalid", 400
                session["token"] = is_token_exist[0]
        except KeyError:
            tmp = generate_token(25)
            cursor.execute("INSERT INTO users (token, ip) VALUES (?, ?)",
                           (tmp, request.headers['X-Forwarded-For']))
            session["token"] = tmp

        conn.close()
    session.permanent = True
    return redirect(url_for("index_upload"))


@app.route("/callback/")
def callback():
    discord.callback()
    user = discord.fetch_user()
    conn = pool.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT token FROM users WHERE discord_id=?", (user.id,))
    data = cursor.fetchone()
    if not data:
        tmp = generate_token(25)
        cursor.execute("INSERT INTO users (token, ip, discord_id, name) VALUES (?, ?, ?, ?)",
                       (tmp, request.headers['X-Forwarded-For'], discord.user_id, user.name))
        session["token"] = tmp
        session.modified = True
    else:
        session["token"] = data[0]
        session.modified = True
    session.permanent = True
    conn.close()
    return redirect(url_for("index_upload"))


@app.errorhandler(Unauthorized)
def redirect_unauthorized(e):
    return redirect(url_for("login"))


@app.route("/upload")
def upload():
    return render_template("upload.html", app_info=app_info, domain=config.domain, user=User(session.get('token')))


@app.route('/i/<path:path>')
def send_uploads(path):
    conn = pool.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT mimetype FROM files WHERE id=?", (os.path.splitext(path)[0],))
    mimetype = cursor.fetchone()[0]
    conn.close()
    if mimetype.split("/")[0] == "text":
        mimetype = "text/plain"
    return send_from_directory('uploads', path, mimetype=mimetype)


@app.route('/t/<path:path>')
def thumbnails(path):
    return send_from_directory('thumbnails', path)


#Discord friendly
@app.route('/sf/<path:path>')
def social_files(path):
    return send_from_directory('socials', path)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("index_upload"))


@app.route('/changename', methods=["POST"])
def change_name():
    if 'token' in request.form and 'name' in request.form:
        if User(request.form["token"]).is_logged:
            conn = pool.get_connection()
            cursor = conn.cursor()

            cursor.execute("UPDATE users SET name=? WHERE token=?", (request.form["name"], request.form["token"]))
            conn.close()
            return redirect(url_for("index_upload"))
        else:
            raise Unauthorized
    else:
        return "Bad Request", 400


@app.route("/login")
def login():
    return render_template("login.html", app_info=app_info, domain=config.domain, user=User(session.get('token')))


@app.route("/changelog")
def changelog():
    return render_template("changelog.html", app_info=app_info, domain=config.domain, user=User(session.get('token')),
                           changelog=open("CHANGELOG", "r").read())


@app.route("/changelog/raw")
def changelog_raw():
    return send_from_directory(".", "CHANGELOG", mimetype="text/plain")


@app.route('/', methods=['GET', 'POST'])
def index_upload():
    if request.method == 'POST':
        profile = request.files['file']
        if profile.filename == '':
            return "File is empty", 400
        token = None
        token1 = None
        conn = pool.get_connection()
        cursor = conn.cursor()
        if 'token' not in request.form:
            cursor.execute("SELECT (token) FROM users WHERE ip=?", (request.headers['X-Forwarded-For'],))
            token1 = cursor.fetchone()
            if not token1:
                tmp = generate_token(25)
                cursor.execute("INSERT INTO users (token, ip) VALUES (?, ?)",
                               (tmp, request.headers['X-Forwarded-For']))
                token1 = tmp
            else:
                token1 = token1[0]
        else:
            token = request.form['token']
        token = token1 if not token else token
        cursor.execute("SELECT token, name FROM users WHERE token=?", (token,))

        is_token_exist = cursor.fetchone()
        if not is_token_exist:
            return "Token is invalid", 400
        tmp = generate_token(12)
        res = tmp + os.path.splitext(profile.filename)[1]
        profile.save(os.path.join('uploads', res))
        subprocess.call(['ffmpeg', '-i', os.path.join('uploads', res), '-ss', '00:00:00.000', '-vframes', '1',
                         os.path.join('thumbnails', os.path.splitext(res)[0] + ".jpg")])
        raw_file = open(os.path.join("socials", tmp + ".json"), "w")
        raw_file.write(json.dumps(
            {"author_name": f"Uploaded by {is_token_exist[1]}",
             "author_url": config.domain,
             "provider_name": f"Uploaded at {datetime.datetime.now().strftime('%d.%m.%Y')}",
             "provider_url": "https://discordapp.com/jobs"}))
        cursor.execute("INSERT INTO files (id, user, ext, mimetype, size) VALUES (?, ?, ?, ?, ?)",
                       (tmp, token, os.path.splitext(profile.filename)[1],
                        profile.mimetype, os.path.getsize(os.path.join("uploads", res))))
        conn.close()
        # print(request.form["html"])
        if 'redirect' in request.form and request.form["redirect"] == "1":
            return redirect(url_for("social", path=res))
        if 'social' in request.form and request.form["social"] == "y":
            return f"{config.domain}/s/{res}"
        else:
            return f"{config.domain}/i/{res}"
    else:
        return render_template("index.html", app_info=app_info, user=User(session.get("token")),
                               max_file_size=config.max_file_size)


@app.route("/social/<path:path>")
def social_old(path):
    return redirect(url_for("social", path=path))


@app.route("/s/<path:path>")
def social(path):
    try:
        conn = pool.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
                SELECT files.user, users.discord_id, users.name, files.id, files.ext, files.upload_date, files.mimetype, files.size 
                FROM files 
                INNER JOIN users 
                ON files.user = users.token 
                AND files.id=?""", (os.path.splitext(path)[0],))
        data = cursor.fetchone()
        conn.close()
        if not data or len(data) == 0:
            return "Not Found", 404
        file_info = {
            "user": data[0],
            "discord_id": data[1],
            "name": data[2],
            "id": data[3],
            "ext": data[4],
            "date": data[5],
            "mimetype": data[6],
            "size": sizeof_fmt(data[7])
        }
        return render_template("social.html",
                               domain=config.domain,
                               file=file_info,
                               app_info=app_info,
                               user=User(session.get('token')))
    except FileNotFoundError:
        return "Not Found", 404


@app.route("/gallery/<page>")
def gallery(page):
    if User(session.get("token")).is_logged:
        conn = pool.get_connection()
        cursor = conn.cursor()
        cursor.execute("""SELECT COUNT(*)
                              FROM files 
                              WHERE user=?""", (session.get("token"),))
        count = cursor.fetchone()
        cursor.execute("""SELECT files.id, files.ext, files.upload_date, files.mimetype
                              FROM files
                              INNER JOIN users 
                              ON files.user = users.token 
                              WHERE user=? 
                              ORDER BY upload_date DESC 
                              LIMIT 10 
                              OFFSET ?""", (session.get("token"), (int(page) - 1) * 10))
        data = cursor.fetchall()
        conn.close()
        data = [{
            "id": i[0],
            "ext": i[1],
            "date": i[2],
            "mime": i[3]
        } for i in data]

        return render_template(
            "gallery.html",
            app_info=app_info,
            domain=config.domain,
            page=int(page),
            count=count[0],
            files=data,
            user=User(session.get('token')),
            ceil=math.ceil)
    else:
        raise Unauthorized
