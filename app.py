import os
import requests
import smtplib
import base64
import re
import yt_dlp
import json
import atexit
import time
import cloudinary
import cloudinary.uploader
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from email.message import EmailMessage
from email.mime.text import MIMEText
from flask_mail import Mail, Message
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from cloudinary.uploader import upload as cloudinary_upload
from psycopg2.extras import RealDictCursor

load_dotenv()

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for flashing messages (e.g., in contact form)

def get_db():
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=RealDictCursor
    )



admin = Blueprint('admin', __name__)

# Hardcoded credentials (can be replaced with DB later)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'emaw123'  # Change this to something secure

# Daraja credentials 
consumer_key = "MGWYGhq9UpMsHG97j3TkVNzTBP4lT1qC8uFttn8EcfhynQzT"
consumer_secret = "L1UOpTZJzzFVAnnnHdOgdrIAuzhktXfup6rOrYLrrwdoiY7JbUiq9fGNNHI6fLvz"
shortcode = "5620516"  # Replace with your Paybill or shortcode
passkey = "878f5ecd21d68a0760993346761398f553a8b0e9e0a5a06d3603b9804966f888"

# Cloudinary configuration
cloudinary.config(
  cloud_name = 'dtnchviep',
  api_key = '395915344537296',
  api_secret = 'zNsxZ9RpCHd7K6tkc0R8t-qXiWw',
  secure = True
)

# Flask Mail config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'emawkenya700@gmail.com'  # your gmail
app.config['MAIL_PASSWORD'] = 'vblgpjwjokimfzsz'     # generated app password
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)

# Stop scheduler when app exits
atexit.register(lambda: scheduler.shutdown())

# Secret Admin Login Route
@app.route('/super/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_board_members'))
        else:
            flash('Invalid credentials. Please try again.')
            return redirect(url_for('admin_login'))

    return render_template('admin_login.html')


# Admin Dashboard
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin_board.html')


# Logout
@app.route('/logout_admin')
def logout_admin():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


@app.route("/admin/board_members")
def admin_board_members():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM board_members")
    members = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("admin_board.html", board_members=members, active_page='board_members')


@app.route("/admin/board_members/add", methods=["POST"])
def add_board_member():
    conn = get_db()
    cur = conn.cursor()

    image = request.files['image']
    result = cloudinary.uploader.upload(image)
    image_url = result['secure_url']

    cur.execute("""
        INSERT INTO board_members (name, title, position, region, church, image)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        request.form['name'],
        request.form['title'],
        request.form['position'],
        request.form['region'],
        request.form['church'],
        image_url
    ))

    conn.commit()
    cur.close()
    conn.close()
    return redirect("/admin/board_members")


@app.route("/admin/board_members/edit/<int:id>", methods=["POST"])
def edit_board_member(id):
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE board_members
        SET name=%s, title=%s, position=%s, region=%s, church=%s
        WHERE id=%s
    """, (
        data['name'],
        data['title'],
        data['position'],
        data['region'],
        data['church'],
        id
    ))

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Updated"})


@app.route("/admin/board_members/delete/<int:id>", methods=["POST"])
def delete_board_member(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM board_members WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/admin/board_members")



# Display pastors admin page
@app.route('/admin/pastors')
def admin_pastors():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT * FROM pastors
        ORDER BY CASE title
            WHEN 'Bishop' THEN 1
            WHEN 'Reverend' THEN 2
            WHEN 'Apostle' THEN 3
            WHEN 'Pastor' THEN 4
        END
    """)

    pastors = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_pastors.html', pastors=pastors)

# Upload new pastor
@app.route('/admin/pastors/add', methods=['POST'])
def add_pastor():
    conn = get_db()
    cur = conn.cursor()

    image_url = cloudinary.uploader.upload(request.files['image'])['secure_url']

    cur.execute("""
        INSERT INTO pastors (name, title, church, region, bio, image)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        request.form['name'],
        request.form['title'],
        request.form['church'],
        request.form['region'],
        request.form['bio'],
        image_url
    ))

    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('admin_pastors'))

# Inline edit pastor
@app.route('/admin/pastors/edit/<int:id>', methods=['POST'])
def edit_pastor(id):
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE pastors
        SET title=%s, name=%s, church=%s, region=%s, bio=%s
        WHERE id=%s
    """, (
        data['title'],
        data['name'],
        data['church'],
        data['region'],
        data['bio'],
        id
    ))

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success"})

# Delete pastor
@app.route('/admin/pastors/delete/<int:id>', methods=['POST'])
def delete_pastor(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM pastors WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('admin_pastors'))


@app.route("/admin/churches", methods=["GET", "POST"])
def admin_churches():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == "POST":
        name = request.form["name"]
        region = request.form["region"]
        lead_title = request.form["lead_title"]
        lead_name = request.form["lead_name"]
        other_pastors = request.form.getlist("other_pastors[]")
        other_titles = request.form.getlist("other_titles[]")
        image_file = request.files.get("order_of_events_image")

        other_entries = [
            f"{t.strip()} {n.strip()}"
            for t, n in zip(other_titles, other_pastors) if n.strip()
        ]
        other_pastors_str = ", ".join(other_entries)
        lead_full = f"{lead_title.strip()} {lead_name.strip()}"

        image_url = None
        if image_file and image_file.filename:
            upload = cloudinary.uploader.upload(image_file)
            image_url = upload["secure_url"]

        cur.execute("""
            INSERT INTO churches (name, region, lead_pastor_name, other_pastors, order_of_events_image)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, region, lead_full, other_pastors_str, image_url))

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("admin_churches"))

    cur.execute("SELECT * FROM churches ORDER BY region ASC, name ASC")
    churches = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin_churches.html", churches=churches, active_page="churches")

@app.route("/admin/churches/edit/<int:id>", methods=["POST"])
def edit_church(id):
    conn = get_db()
    cur = conn.cursor()

    name = request.form.get("name")
    region = request.form.get("region")
    lead = request.form.get("lead_pastor_name")
    others = request.form.get("other_pastors")

    file = request.files.get("order_of_events_image")
    image_url = None
    if file and file.filename:
        image_url = cloudinary_upload(file)["secure_url"]

    if image_url:
        cur.execute("""
            UPDATE churches
            SET name=%s, region=%s, lead_pastor_name=%s, other_pastors=%s, order_of_events_image=%s
            WHERE id=%s
        """, (name, region, lead, others, image_url, id))
    else:
        cur.execute("""
            UPDATE churches
            SET name=%s, region=%s, lead_pastor_name=%s, other_pastors=%s
            WHERE id=%s
        """, (name, region, lead, others, id))

    conn.commit()
    cur.close()
    conn.close()
    return jsonify(status="success")


@app.route("/admin/churches/upload", methods=["POST"])
def upload_church():
    conn = get_db()
    cur = conn.cursor()

    name = request.form['name']
    region = request.form['region']
    lead_title = request.form['lead_title']
    lead_name = request.form['lead_pastor_name']
    lead_full = f"{lead_title} {lead_name}"

    other_titles = request.form.getlist("other_titles[]")
    other_names = request.form.getlist("other_names[]")
    others = ", ".join(f"{t} {n}" for t, n in zip(other_titles, other_names))

    image = request.files.get('order_of_events_image')
    image_url = None
    if image and image.filename:
        image_url = cloudinary.uploader.upload(image)["secure_url"]

    cur.execute("""
        INSERT INTO churches (name, region, lead_pastor_name, other_pastors, order_of_events_image)
        VALUES (%s, %s, %s, %s, %s)
    """, (name, region, lead_full, others, image_url))

    conn.commit()
    cur.close()
    conn.close()
    return redirect("/admin/churches")

@app.route("/admin/churches/delete/<int:id>", methods=["POST"])
def delete_church(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM churches WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("admin_churches"))

@app.route("/admin/events_announcements", methods=["GET", "POST"])
def admin_events_announcements():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == "POST":
        form_type = request.form.get("form_type")

        if form_type == "announcement":
            cur.execute(
                "INSERT INTO announcements (message, expire_at) VALUES (%s, %s)",
                (request.form["message"], request.form["expire_at"])
            )

        if form_type == "event":
            cur.execute("""
                INSERT INTO events (title, date, end_date, time, venue)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                request.form["title"],
                request.form["start_date"],
                request.form.get("end_date"),
                request.form["time"],
                request.form["venue"]
            ))

        conn.commit()

    cur.execute("SELECT * FROM events WHERE date >= CURRENT_DATE ORDER BY date ASC")
    events = cur.fetchall()

    cur.execute("SELECT * FROM announcements WHERE expire_at >= NOW() ORDER BY expire_at ASC")
    announcements = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("admin_events_announcements.html", events=events, announcements=announcements)


@app.route("/admin/events", methods=["GET", "POST"])
def admin_events():
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == "POST":
        title = request.form["title"]
        date = request.form["date"]
        end_date = request.form.get("end_date") or None
        time = request.form["time"]
        venue = request.form["venue"]

        cursor.execute(
            "INSERT INTO events (title, date, end_date, time, venue) VALUES (%s, %s, %s, %s, %s)",
            (title, date, end_date, time, venue)
        )
        conn.commit()

    cursor.execute("SELECT * FROM events ORDER BY date ASC")
    events = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("admin_events.html", events=events)

@app.route("/admin/announcements", methods=["GET", "POST"])
def admin_announcements():
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == "POST":
        message = request.form["message"]
        expire_at = request.form["expire_at"]

        cursor.execute(
            "INSERT INTO announcements (message, expire_at) VALUES (%s, %s)",
            (message, expire_at)
        )
        conn.commit()

    cursor.execute("SELECT * FROM announcements ORDER BY expire_at ASC")
    announcements = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("admin_announcements.html", announcements=announcements)

# Upload Event
@app.route("/admin/events/upload", methods=["POST"])
def upload_event():
    conn = get_db()
    cursor = conn.cursor()

    title = request.form["event"]
    date = request.form["event_date"]
    end_date = request.form.get("end_date") or None
    time = request.form["event_time"]
    venue = request.form["venue"]

    cursor.execute("""
        INSERT INTO events (title, date, end_date, time, venue)
        VALUES (%s, %s, %s, %s, %s)
    """, (title, date, end_date, time, venue))

    conn.commit()
    cursor.close()
    conn.close()
    return redirect("/admin/events-announcements")

# Upload Announcement
@app.route("/admin/announcements/upload", methods=["POST"])
def upload_announcement():
    conn = get_db()
    cursor = conn.cursor()

    announcement = request.form["announcement"]
    expiry_date = request.form["expiry_date"]
    expiry_time = request.form["expiry_time"]
    expiry_datetime = f"{expiry_date} {expiry_time}"

    cursor.execute("""
        INSERT INTO announcements (announcement, expiry_datetime)
        VALUES (%s, %s)
    """, (announcement, expiry_datetime))

    conn.commit()
    cursor.close()
    conn.close()
    return redirect("/admin/events-announcements")

# Inline Edit Event
@app.route("/admin/events/edit/<int:event_id>", methods=["POST"])
def edit_event(event_id):
    conn = get_db()
    cursor = conn.cursor()

    data = request.get_json()
    cursor.execute("""
        UPDATE events
        SET title = %s, date = %s, end_date = %s, time = %s, venue = %s
        WHERE id = %s
    """, (
        data.get("title"),
        data.get("date"),
        data.get("end_date") or None,
        data.get("time"),
        data.get("venue"),
        event_id
    ))

    conn.commit()
    cursor.close()
    conn.close()
    return jsonify(status="success")

# Inline Edit Announcement
@app.route("/admin/announcements/edit/<int:announcement_id>", methods=["POST"])
def edit_announcement(announcement_id):
    conn = get_db()
    cursor = conn.cursor()

    data = request.get_json()
    cursor.execute("""
        UPDATE announcements
        SET message = %s, expire_at = %s
        WHERE id = %s
    """, (data.get("message"), data.get("expire_at"), announcement_id))

    conn.commit()
    cursor.close()
    conn.close()
    return jsonify(status="success")

# Delete Event
@app.route("/admin/events/delete/<int:event_id>", methods=["POST"])
def delete_event(event_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
    conn.commit()

    cursor.close()
    conn.close()
    return jsonify(status="deleted")

# Delete Announcement
@app.route("/admin/announcements/delete/<int:announcement_id>", methods=["POST"])
def delete_announcement(announcement_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM announcements WHERE id = %s", (announcement_id,))
    conn.commit()

    cursor.close()
    conn.close()
    return jsonify(status="deleted")


@app.route('/admin/upload_gallery', methods=['GET', 'POST'])
def upload_gallery():
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        file = request.files['image']
        description = request.form['description']
        category = request.form['category']

        allowed_categories = ['pastors', 'congregation', 'events', 'churches']

        if file and category in allowed_categories:
            upload_result = cloudinary_upload(file)
            filename = upload_result['secure_url']

            cursor.execute(
                "INSERT INTO gallery (filename, description, category) VALUES (%s, %s, %s)",
                (filename, description, category)
            )
            conn.commit()
            flash("Image uploaded successfully", "success")
            return redirect(url_for('upload_gallery'))

    cursor.execute("SELECT * FROM gallery ORDER BY uploaded_at DESC")
    images = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('admin_upload_gallery.html', images=images)

@app.route('/admin/delete_image/<int:image_id>', methods=['POST'])
def delete_image(image_id):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT filename FROM gallery WHERE id = %s", (image_id,))
    result = cursor.fetchone()

    if result:
        cloudinary_url = result['filename']
        try:
            parts = cloudinary_url.split('/')
            version_index = parts.index('upload') + 1
            public_id = '/'.join(parts[version_index + 1:]).rsplit('.', 1)[0]
            cloudinary.uploader.destroy(public_id)
        except Exception as e:
            print(e)

        cursor.execute("DELETE FROM gallery WHERE id = %s", (image_id,))
        conn.commit()

    cursor.close()
    conn.close()
    return redirect(url_for('upload_gallery'))



# Home Page
@app.route('/')
def home():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        "SELECT * FROM events WHERE date >= %s ORDER BY date ASC LIMIT 2",
        (datetime.today(),)
    )
    upcoming_events = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('home.html', events_preview=upcoming_events)

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('.', 'sitemap.xml')

    
# About Us
@app.route('/about')
def about():
    return render_template('about.html')


# Ministries
@app.route('/ministries')
def ministries():
    return render_template('ministries.html')


@app.route("/leadership")
def leadership():
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT id, name, image, title, position, region, church
        FROM board_members
    """)
    members = cursor.fetchall()

    cursor.execute("""
        SELECT * FROM pastors
        ORDER BY
          CASE title
            WHEN 'Bishop' THEN 1
            WHEN 'Reverend' THEN 2
            WHEN 'Apostle' THEN 3
            WHEN 'Pastor' THEN 4
            ELSE 5
          END
    """)
    pastors = cursor.fetchall()

    pastor_lookup = {
        (f"{p['title'].strip()} {p['name'].strip()}", p['region'].strip().lower()): p['image']
        for p in pastors
    }

    cursor.execute("SELECT *, id AS church_id FROM churches ORDER BY id ASC")
    churches = cursor.fetchall()

    region_map = {}
    region_first_church_id = {}

    for c in churches:
        title = (c.get('lead_pastor_title') or '').strip()
        name = (c.get('lead_pastor_name') or '').strip()
        region = (c.get('region') or '').strip()
        church_id = c.get('church_id')

        lead_key = (f"{title} {name}".strip(), region.lower())
        c['lead_image'] = pastor_lookup.get(lead_key)

        region_map.setdefault(region, []).append(c)
        if region not in region_first_church_id:
            region_first_church_id[region] = church_id

    sorted_regions = sorted(
        region_map.keys(),
        key=lambda r: (
            r.lower() != "nairobi",
            -len(region_map[r]),
            region_first_church_id[r]
        )
    )

    sorted_region_map = {r: region_map[r] for r in sorted_regions}

    for region, church_list in sorted_region_map.items():
        for church in church_list:
            raw = church.get('other_pastors', '') or ''
            church['parsed_other_pastors'] = parse_other_pastors(raw)

    cursor.close()
    conn.close()

    return render_template(
        "leadership.html",
        board_members=members,
        pastors=pastors,
        churches_by_region=sorted_region_map
    )



# Sermons & Gallery
@app.route('/sermons')
def sermons():
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("SELECT * FROM gallery WHERE category = 'pastors' ORDER BY uploaded_at DESC")
    pastors_gallery = cursor.fetchall()

    cursor.execute("SELECT * FROM gallery WHERE category = 'congregation' ORDER BY uploaded_at DESC")
    congregation_gallery = cursor.fetchall()

    cursor.execute("SELECT * FROM gallery WHERE category = 'events' ORDER BY uploaded_at DESC")
    events_gallery = cursor.fetchall()

    cursor.execute("SELECT * FROM gallery WHERE category = 'churches' ORDER BY uploaded_at DESC")
    churches_gallery = cursor.fetchall()

    cursor.close()
    conn.close()

    cache_file = 'sermons.json'
    cache_expiry_seconds = 3 * 60 * 60

    sermons = []
    if os.path.exists(cache_file):
        if time.time() - os.path.getmtime(cache_file) < cache_expiry_seconds:
            with open(cache_file) as f:
                sermons = json.load(f)
        else:
            fetch_latest_sermons()
    else:
        fetch_latest_sermons()

    if os.path.exists(cache_file):
        with open(cache_file) as f:
            sermons = json.load(f)

    return render_template(
        'sermons.html',
        sermons=sermons,
        pastors=pastors_gallery,
        congregation=congregation_gallery,
        events=events_gallery,
        churches=churches_gallery
    )


# Events & Announcements
@app.route("/events")
def events():
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute(
        "SELECT * FROM events WHERE date >= CURRENT_DATE ORDER BY date ASC"
    )
    events = cursor.fetchall()

    cursor.execute(
        "SELECT * FROM announcements WHERE expire_at >= NOW() ORDER BY expire_at ASC"
    )
    announcements = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("events.html", events=events, announcements=announcements)


def fetch_latest_sermons():
    playlist_url = 'https://www.youtube.com/playlist?list=PLBHQfTlw_fqLU9H3EpDa5vN0P8S_x0W9B'
    ydl_opts = {
        'quiet': True,
        'extract_flat': False,
    }

    sermons = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            for item in info.get('entries', [])[:12]:
                sermons.append({
                    'video_id': item['id'],
                    'title': item['title'],
                    'video_url': f"https://www.youtube.com/watch?v={item['id']}",
                    'thumbnail': item.get('thumbnail', '')
                })
        with open('sermons.json', 'w') as f:
            json.dump(sermons, f)
        print("✅ Sermons updated.")
    except Exception as e:
        print(f"❌ Error fetching sermons: {e}")

# Start the background scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_latest_sermons, 'interval', hours=6)  # every 6 hours
scheduler.start()

@app.route('/ministries/bible-institute')
def bible_institute():
    return render_template('bible_institute.html')

@app.route('/ministries/children')
def children_ministry():
    return render_template('children_ministry.html')

@app.route('/ministries/music')
def music_ministry():
    return render_template('music_ministry.html')

@app.route('/ministries/outreach')
def outreach_ministry():
    return render_template('outreach_ministry.html')

@app.route('/ministries/youth')
def youth_ministry():
    return render_template('youth_ministry.html')

@app.route('/ministries/women_empowerment')
def women_empowerment():
    return render_template('women_empowerment.html')

@app.route('/ministries/media')
def media_ministry():
    return render_template('media_ministry.html')

@app.route('/ministries/intercessory', methods=['GET', 'POST'])
def intercessory_ministry():
    if request.method == 'POST':
        name = request.form.get('name')
        contact = request.form.get('contact')
        message = request.form.get('message')

        email = EmailMessage()
        email['Subject'] = 'New Prayer Request'
        email['From'] = 'emawkenya700@gmail.com'  # Replace with your Gmail
        email['To'] = 'emawkenya700@gmail.com'

        email.set_content(f'''
        New Prayer Request:

        Name: {name}
        Contact: {contact}
        Prayer Item:
        {message}
        ''')

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login('emawkenya700@gmail.com', 'phzkfbejjitnfrea')  # Replace with your credentials
                smtp.send_message(email)
            flash('Your prayer request has been sent successfully!', 'success')
        except Exception as e:
            flash('Failed to send your prayer request. Please try again later.', 'danger')
            print("Email error:", e)

        return redirect('/ministries/intercessory')

    return render_template('intercessory_ministry.html')

@app.route('/ministries/pastors')
def pastors_ministry():
    return render_template('pastors_ministry.html')

@app.route('/ministries/women')
def women_ministry():
    return render_template('women_ministry.html')

@app.route('/ministries/dorcas')
def dorcas_ministry():
    return render_template('dorcas_ministry.html')

@app.route('/ministries/family_therapy')
def family_therapy():
    return render_template('family_therapy.html')

@app.route('/ministries/prison')
def prison_ministry():
    return render_template('prison_ministry.html')

@app.route('/submit_prayer_request', methods=['POST'])
def submit_prayer_request():
    name = request.form.get('name')
    contact = request.form.get('contact')
    description = request.form.get('description')

    # Compose email
    msg = EmailMessage()
    msg['Subject'] = 'New Prayer Request'
    msg['From'] = 'emawkenya700@gmail.com'
    msg['To'] = 'emawkenya700@gmail.com'
    msg.set_content(f'''
    New Prayer Request Submitted

    Name: {name}
    Contact: {contact}

    Prayer Request:
    {description}
    ''')

    # Send email using Gmail SMTP
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login('emawkenya700@gmail.com', 'phzkfbejjitnfrea')
            smtp.send_message(msg)
        flash('Prayer request sent successfully!', 'success')
    except Exception as e:
        print("Error:", e)
        flash('Failed to send prayer request.', 'danger')

    return redirect(url_for('intercessory_ministry'))

@app.route('/submit_donation', methods=['POST'])
def submit_donation():
    currency = request.form['currency']
    amount = request.form['amount']
    method = request.form['method']

    # ✅ Redirect back to homepage (update 'home' if your homepage function is named differently)
    return redirect(url_for('home'))

@app.route('/ceremonies/baptism')
def baptism_ceremony():
    return render_template('baptism_ceremony.html')

@app.route('/ceremonies/communion')
def communion_ceremony():
    return render_template('communion_ceremony.html')

@app.route('/ceremonies/burial')
def burial_ceremony():
    return render_template('burial_ceremony.html')

@app.route('/ceremonies/dedication')
def dedication_ceremony():
    return render_template('dedication_ceremony.html')

@app.route('/ceremonies/wedding')
def wedding_ceremony():
    return render_template('wedding_ceremony.html')

@app.route('/ceremonies/ordination')
def ordination_ceremony():
    return render_template('ordination_ceremony.html')

@app.route('/pay/mpesa', methods=['GET'])
def stk_push():
    phone = request.args.get('phone')
    amount = request.args.get('amount')

    if not phone or not amount:
        return jsonify({"error": "Missing phone or amount"}), 400

    # Format phone to 2547xxxxxxxx
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    elif phone.startswith('+254'):
        phone = phone[1:]

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode((shortcode + passkey + timestamp).encode()).decode()

    try:
        access_token = get_access_token()
    except Exception as e:
        return jsonify({"error": f"Access token error: {str(e)}"}), 500

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": "https://emawchurch.org/mpesa/callback",
        "AccountReference": "Donation",
        "TransactionDesc": "Church Donation"
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    print("STK Push Payload:", payload)
    print("Headers Sent:", headers)

    response = requests.post(
        "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload, headers=headers
    )

    print("DARAJA RESPONSE:", response.status_code, response.text)

    try:
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": "Invalid JSON in response", "raw": response.text}), response.status_code

@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    print("Raw JSON received:", request.data)  # Add this
    data = request.get_json(force=True)        # Change this line

    print("Parsed JSON:", data)  # Add this
    # Extract payment info
    try:
        body = data['Body']['stkCallback']
        amount = body['CallbackMetadata']['Item'][0]['Value']
        phone = body['CallbackMetadata']['Item'][4]['Value']
    except:
        amount = "Unknown"
        phone = "Unknown"

    # Send email
    try:
        msg = Message("New Church Donation Received",
                      sender="musiadaniel21@gmail.comm",
                      recipients=["musiadaniel21@gmail.com"])
        msg.body = f"A donation of KES {amount} was made by phone number: {phone}."
        mail.send(msg)
    except Exception as e:
        print("Email sending failed:", e)

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})


def get_access_token():
    url = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(consumer_key, consumer_secret))
    
    print("Access Token Response:", response.status_code, response.text)  # Debug

    if response.status_code != 200:
        raise Exception("Failed to get access token")

    access_token = response.json().get('access_token')
    print("Access Token Used:", access_token)  # Confirm it's the one being used

    return access_token


def send_thank_you_email(to_email, amount):
    body = f"Thank you for your donation of KES {amount} to our ministry. God bless you!"
    msg = MIMEText(body)
    msg['Subject'] = "Donation Received"
    msg['From'] = "emawkenya700@gmail.com"
    msg['To'] = to_email

    # Update with your SMTP server
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login("emawkenya700@gmail.com", "vblgpjwjokimfzsz")
        server.send_message(msg)


def parse_other_pastors(raw_text):
    if not raw_text:
        return []

    # Split by comma (your database stores them as comma-separated)
    parts = [part.strip() for part in raw_text.split(",") if part.strip()]
    return parts



# Run the Flask app
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
