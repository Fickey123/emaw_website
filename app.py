import os
import requests
import MySQLdb.cursors
import smtplib
import base64
import re
import yt_dlp
import json
import atexit
import time
from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from email.message import EmailMessage
from email.mime.text import MIMEText
from flask_mail import Mail, Message
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for flashing messages (e.g., in contact form)

# MySQL Config for FreeDB
app.config['MYSQL_HOST'] = 'sql.freedb.tech'
app.config['MYSQL_USER'] = 'freedb_fic_user'
app.config['MYSQL_PASSWORD'] = '8jBemu8X%TRDZB$'
app.config['MYSQL_DB'] = 'freedb_emaw_db'
app.config['MYSQL_PORT'] = 3306

# Initialize MySQL
mysql = MySQL(app)


admin = Blueprint('admin', __name__)
UPLOAD_FOLDER = 'static/uploads'

# Hardcoded credentials (can be replaced with DB later)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'emaw123'  # Change this to something secure

# Daraja credentials (Sandbox)
consumer_key = "MGWYGhq9UpMsHG97j3TkVNzTBP4lT1qC8uFttn8EcfhynQzT"
consumer_secret = "L1UOpTZJzzFVAnnnHdOgdrIAuzhktXfup6rOrYLrrwdoiY7JbUiq9fGNNHI6fLvz"
shortcode = "5620516"  # Replace with your Paybill or shortcode
passkey = "878f5ecd21d68a0760993346761398f553a8b0e9e0a5a06d3603b9804966f888"

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
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM board_members")
    members = cursor.fetchall()
    return render_template("admin_board.html", board_members=members, active_page='board_members')


@app.route("/admin/board_members/add", methods=["POST"])
def add_board_member():
    name = request.form['name']
    title = request.form['title']
    position = request.form['position']
    region = request.form['region']
    church = request.form['church']
    image = request.files['image']
    
    if image:
        filename = secure_filename(image.filename)
        image_path = os.path.join('static/uploads', filename)
        image.save(image_path)

        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO board_members (name, title, position, region, church, image)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, title, position, region, church, filename))
        mysql.connection.commit()
    
    return redirect("/admin/board_members")


@app.route("/admin/board_members/edit/<int:id>", methods=["POST"])
def edit_board_member(id):
    data = request.get_json()
    name = data['name']
    title = data['title']
    position = data['position']
    region = data['region']
    church = data['church']

    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE board_members
        SET name=%s, title=%s, position=%s, region=%s, church=%s
        WHERE id=%s
    """, (name, title, position, region, church, id))
    mysql.connection.commit()

    return jsonify({"message": "Board member updated successfully"})


@app.route("/admin/board_members/delete/<int:id>", methods=["POST"])
def delete_board_member(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM board_members WHERE id=%s", (id,))
    mysql.connection.commit()
    return redirect("/admin/board_members")


# Display pastors admin page
@app.route('/admin/pastors')
def admin_pastors():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # <- Use DictCursor here
    cursor.execute("""
        SELECT * FROM pastors 
        ORDER BY FIELD(title, 'Bishop', 'Reverend','Apostle', 'Pastor')
    """)
    pastors = cursor.fetchall()
    return render_template('admin_pastors.html', pastors=pastors, active_page='pastors')

# Upload new pastor
@app.route('/admin/pastors/add', methods=['POST'])
def add_pastor():
    name = request.form['name']
    title = request.form['title']
    church = request.form['church']
    region = request.form['region']
    bio = request.form['bio']
    image_file = request.files['image']

    if image_file:
        filename = secure_filename(image_file.filename)
        image_path = os.path.join(UPLOAD_FOLDER, filename)
        image_file.save(image_path)

        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO pastors (name, title, church, region, bio, image) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, title, church, region, bio, filename))
        mysql.connection.commit()

    return redirect(url_for('admin_pastors'))

# Inline edit pastor
@app.route('/admin/pastors/edit/<int:id>', methods=['POST'])
def edit_pastor(id):
    data = request.get_json()
    title = data['title']
    name = data['name']
    church = data['church']
    region = data['region']
    bio = data['bio']

    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE pastors
        SET title = %s, name = %s, church = %s, region = %s, bio = %s
        WHERE id = %s
    """, (title, name, church, region, bio, id))
    mysql.connection.commit()
    return jsonify({'status': 'success'})

# Delete pastor
@app.route('/admin/pastors/delete/<int:id>', methods=['POST'])
def delete_pastor(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM pastors WHERE id = %s", (id,))
    mysql.connection.commit()
    return redirect(url_for('admin_pastors'))


@app.route("/admin/churches", methods=["GET", "POST"])
def admin_churches():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":
        name = request.form["name"]
        region = request.form["region"]
        lead_title = request.form["lead_title"]
        lead_name = request.form["lead_name"]
        other_pastors = request.form.getlist("other_pastors[]")  # List of strings
        other_titles = request.form.getlist("other_titles[]")    # Corresponding titles
        image_file = request.files.get("order_of_events_image")

        other_pastor_entries = [
            f"{t.strip()} {n.strip()}" for t, n in zip(other_titles, other_pastors) if n.strip()
        ]
        other_pastors_str = ", ".join(other_pastor_entries)

        lead_full = f"{lead_title.strip()} {lead_name.strip()}"

        image_filename = None
        if image_file and image_file.filename:
            image_filename = secure_filename(image_file.filename)
            image_path = os.path.join("static/uploads", image_filename)
            image_file.save(image_path)

        cursor.execute("""
            INSERT INTO churches (name, region, lead_pastor_name, other_pastors, order_of_events_image)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, region, lead_full, other_pastors_str, image_filename))
        mysql.connection.commit()

        return redirect(url_for('admin_churches'))

    # GET logic - fetch and display churches
    cursor.execute("SELECT * FROM churches ORDER BY region ASC, name ASC")
    churches = cursor.fetchall()
    return render_template("admin_churches.html", churches=churches, active_page='churches')

@app.route("/admin/churches/upload", methods=["POST"])
def upload_church():
    name = request.form['name']
    region = request.form['region']
    lead_title = request.form['lead_title']
    lead_name = request.form['lead_pastor_name']
    lead_full = f"{lead_title} {lead_name}"

    other_titles = request.form.getlist("other_titles[]")
    other_names = request.form.getlist("other_names[]")

    others_combined = ", ".join(f"{t} {n}" for t, n in zip(other_titles, other_names)) if other_titles else None

    image = request.files['order_of_events_image']
    filename = secure_filename(image.filename)
    image.save(os.path.join(app.root_path, 'static/uploads', filename))

    cursor = mysql.connection.cursor()
    cursor.execute("""
        INSERT INTO churches (name, region, lead_pastor_name, other_pastors, order_of_events_image)
        VALUES (%s, %s, %s, %s, %s)
    """, (name, region, lead_full, others_combined, filename))
    mysql.connection.commit()

    return redirect("/admin/churches")

@app.route("/admin/churches/edit/<int:id>", methods=["POST"])
def edit_church(id):
    name = request.form.get("name")
    region = request.form.get("region")
    lead = request.form.get("lead_pastor_name")
    others = request.form.get("other_pastors")
    
    # Handle file upload
    file = request.files.get("order_of_events_image")
    filename = None
    if file and file.filename:
        filename = secure_filename(file.filename)
        file.save(os.path.join("static/uploads", filename))

    cursor = mysql.connection.cursor()

    if filename:
        cursor.execute("""
            UPDATE churches
            SET name = %s, region = %s, lead_pastor_name = %s, other_pastors = %s, order_of_events_image = %s
            WHERE id = %s
        """, (name, region, lead, others, filename, id))
    else:
        cursor.execute("""
            UPDATE churches
            SET name = %s, region = %s, lead_pastor_name = %s, other_pastors = %s
            WHERE id = %s
        """, (name, region, lead, others, id))

    mysql.connection.commit()
    return jsonify({"status": "success"})

@app.route("/admin/churches/delete/<int:id>", methods=["POST"])
def delete_church(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM churches WHERE id = %s", (id,))
    mysql.connection.commit()
    return redirect(url_for('admin_churches'))

@app.route("/admin/events_announcements", methods=["GET", "POST"])
def admin_events_announcements():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":
        form_type = request.form.get("form_type")
        print("Received POST request for:", form_type)

        if form_type == "announcement":
            message = request.form.get("message")
            expire_at = request.form.get("expire_at")

            print("Announcement Form:", message, expire_at)

            if message and expire_at:
                try:
                    cursor.execute(
                        "INSERT INTO announcements (message, expire_at) VALUES (%s, %s)",
                        (message, expire_at)
                    )
                    mysql.connection.commit()
                    flash("Announcement added successfully.", "success")
                except Exception as e:
                    mysql.connection.rollback()
                    print("Error inserting announcement:", e)
                    flash("Failed to add announcement.", "error")
            else:
                flash("Both message and expiration date are required.", "error")

        elif form_type == "event":
            title = request.form.get("title")
            date = request.form.get("start_date")
            end_date = request.form.get("end_date") or None
            time = request.form.get("time")
            venue = request.form.get("venue")

            print("Event Form:", title, date, end_date, time, venue)

            if title and date and time and venue:
                try:
                    cursor.execute(
                        "INSERT INTO events (title, date, end_date, time, venue) VALUES (%s, %s, %s, %s, %s)",
                        (title, date, end_date, time, venue)
                    )
                    mysql.connection.commit()
                    flash("Event added successfully.", "success")
                except Exception as e:
                    mysql.connection.rollback()
                    print("Error inserting event:", e)
                    flash("Failed to add event.", "error")
            else:
                flash("All event fields are required.", "error")

    # Fetch upcoming events
    try:
        cursor.execute("SELECT * FROM events WHERE date >= CURDATE() ORDER BY date ASC")
        events = cursor.fetchall()
    except Exception as e:
        print("Error fetching events:", e)
        events = []

    # Fetch active announcements
    try:
        cursor.execute("SELECT * FROM announcements WHERE expire_at >= NOW() ORDER BY expire_at ASC")
        announcements = cursor.fetchall()
    except Exception as e:
        print("Error fetching announcements:", e)
        announcements = []

    return render_template("admin_events_announcements.html", events=events, announcements=announcements)



@app.route("/admin/events", methods=["GET", "POST"])
def admin_events():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

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
        mysql.connection.commit()

    cursor.execute("SELECT * FROM events ORDER BY date ASC")
    events = cursor.fetchall()

    return render_template("admin_events.html", events=events)

@app.route("/admin/announcements", methods=["GET", "POST"])
def admin_announcements():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":
        message = request.form["message"]
        expire_at = request.form["expire_at"]  # format: YYYY-MM-DD HH:MM
        cursor.execute("INSERT INTO announcements (message, expire_at) VALUES (%s, %s)",
                       (message, expire_at))
        mysql.connection.commit()

    cursor.execute("SELECT * FROM announcements ORDER BY expire_at ASC")
    announcements = cursor.fetchall()

    return render_template("admin_announcements.html", announcements=announcements)

# Upload Event
@app.route("/admin/events/upload", methods=["POST"])
def upload_event():
    title = request.form["event"]
    date = request.form["event_date"]
    end_date = request.form.get("end_date") or None
    time = request.form["event_time"]
    venue = request.form["venue"]

    cursor = mysql.connection.cursor()
    cursor.execute("""
        INSERT INTO events (title, date, end_date, time, venue)
        VALUES (%s, %s, %s, %s, %s)
    """, (title, date, end_date, time, venue))
    mysql.connection.commit()
    return redirect("/admin/events-announcements")

# Upload Announcement
@app.route("/admin/announcements/upload", methods=["POST"])
def upload_announcement():
    announcement = request.form["announcement"]
    expiry_date = request.form["expiry_date"]
    expiry_time = request.form["expiry_time"]

    expiry_datetime = f"{expiry_date} {expiry_time}"

    cursor = mysql.connection.cursor()
    cursor.execute("""
        INSERT INTO announcements (announcement, expiry_datetime)
        VALUES (%s, %s)
    """, (announcement, expiry_datetime))
    mysql.connection.commit()
    return redirect("/admin/events-announcements")

# Inline Edit Event
@app.route("/admin/events/edit/<int:event_id>", methods=["POST"])
def edit_event(event_id):
    data = request.get_json()
    new_title = data.get("title")
    new_date = data.get("date")
    new_end_date = data.get("end_date") or None
    new_time = data.get("time")
    new_venue = data.get("venue")

    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE events 
        SET title = %s, date = %s, end_date = %s, time = %s, venue = %s 
        WHERE id = %s
    """, (new_title, new_date, new_end_date, new_time, new_venue, event_id))
    mysql.connection.commit()
    return jsonify(status="success")

# Inline Edit Announcement
@app.route("/admin/announcements/edit/<int:announcement_id>", methods=["POST"])
def edit_announcement(announcement_id):
    data = request.get_json()
    new_message = data.get("message")
    new_expire = data.get("expire_at")

    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE announcements 
        SET message = %s, expire_at = %s 
        WHERE id = %s
    """, (new_message, new_expire, announcement_id))
    mysql.connection.commit()
    return jsonify(status="success")

# Delete Event
@app.route("/admin/events/delete/<int:event_id>", methods=["POST"])
def delete_event(event_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
    mysql.connection.commit()
    return jsonify(status="deleted")

# Delete Announcement
@app.route("/admin/announcements/delete/<int:announcement_id>", methods=["POST"])
def delete_announcement(announcement_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM announcements WHERE id = %s", (announcement_id,))
    mysql.connection.commit()
    return jsonify(status="deleted")


@app.route('/admin/upload_gallery', methods=['GET', 'POST'])
def upload_gallery():
    if request.method == 'POST':
        file = request.files['image']
        description = request.form['description']
        category = request.form['category']

        # Updated category check
        allowed_categories = ['pastors', 'congregation', 'events', 'churches']

        if file and category in allowed_categories:
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))

            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO gallery (filename, description, category) VALUES (%s, %s, %s)",
                (filename, description, category)
            )
            mysql.connection.commit()
            cursor.close()
            flash("Image uploaded successfully", "success")
            return redirect(url_for('upload_gallery'))

    # Fetch all gallery images
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM gallery ORDER BY uploaded_at DESC")
    images = cursor.fetchall()
    cursor.close()

    return render_template('admin_upload_gallery.html', images=images)

@app.route('/admin/delete_image/<int:image_id>', methods=['POST'])
def delete_image(image_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch file path
    cursor.execute("SELECT filename FROM gallery WHERE id = %s", (image_id,))
    result = cursor.fetchone()

    if result:
        filename = result['filename']
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        # Delete from disk
        if os.path.exists(file_path):
            os.remove(file_path)

        # Delete from DB
        cursor.execute("DELETE FROM gallery WHERE id = %s", (image_id,))
        mysql.connection.commit()

    return redirect(url_for('upload_gallery'))



# Home Page
@app.route('/')
def home():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM events WHERE date >= %s ORDER BY date ASC LIMIT 2", (datetime.today(),))
    upcoming_events = cur.fetchall()
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
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch board members
    cursor.execute("""
        SELECT id, name, image, title, position, region, church
        FROM board_members
    """)
    members = cursor.fetchall()

    # Fetch pastors (ordered by rank)
    cursor.execute("""
        SELECT * FROM pastors
        ORDER BY FIELD(title, 'Bishop', 'Reverend', 'Apostle', 'Pastor')
    """)
    pastors = cursor.fetchall()

    # Build pastor image lookup
    pastor_lookup = {
        (f"{p['title'].strip()} {p['name'].strip()}", p['region'].strip().lower()): p['image']
        for p in pastors
    }

    # Fetch churches with timestamps
    cursor.execute("SELECT *, id AS church_id FROM churches ORDER BY id ASC")  # id used as creation order
    churches = cursor.fetchall()

    # Group churches by region
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
        # Track earliest church ID for tie-breaking sort
        if region not in region_first_church_id:
            region_first_church_id[region] = church_id

    # Sort regions:
    # 1. Nairobi first
    # 2. Then by number of churches (descending)
    # 3. Then by first added church ID (ascending)
    sorted_regions = sorted(
        region_map.keys(),
        key=lambda r: (
            r.lower() != "nairobi",                    # Nairobi first
            -len(region_map[r]),                       # More churches higher
            region_first_church_id[r]                  # Earlier added region breaks tie
        )
    )

    # Build sorted region map
    sorted_region_map = {r: region_map[r] for r in sorted_regions}

    # Parse other pastors
    for region, church_list in sorted_region_map.items():
        for church in church_list:
            raw = church.get('other_pastors', '') or ''
            church['parsed_other_pastors'] = parse_other_pastors(raw)

    return render_template("leadership.html",
                           board_members=members,
                           pastors=pastors,
                           churches_by_region=sorted_region_map)





# Sermons & Gallery
@app.route('/sermons')
def sermons():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch gallery images
    cursor.execute("SELECT * FROM gallery WHERE category = 'pastors' ORDER BY uploaded_at DESC")
    pastors_gallery = cursor.fetchall()

    cursor.execute("SELECT * FROM gallery WHERE category = 'congregation' ORDER BY uploaded_at DESC")
    congregation_gallery = cursor.fetchall()

    cursor.execute("SELECT * FROM gallery WHERE category = 'events' ORDER BY uploaded_at DESC")
    events_gallery = cursor.fetchall()

    cursor.execute("SELECT * FROM gallery WHERE category = 'churches' ORDER BY uploaded_at DESC")
    churches_gallery = cursor.fetchall()

    # Check cache file
    cache_file = 'sermons.json'
    cache_expiry_seconds = 3 * 60 * 60  # 3 hours

    sermons = []
    if os.path.exists(cache_file):
        modified_time = os.path.getmtime(cache_file)
        if time.time() - modified_time < cache_expiry_seconds:
            with open(cache_file, 'r') as f:
                sermons = json.load(f)
        else:
            fetch_latest_sermons()
            with open(cache_file, 'r') as f:
                sermons = json.load(f)
    else:
        fetch_latest_sermons()
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
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
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch upcoming events
    cursor.execute("SELECT * FROM events WHERE date >= CURDATE() ORDER BY date ASC")
    events = cursor.fetchall()

    # Fetch valid announcements
    cursor.execute("SELECT * FROM announcements WHERE expire_at >= NOW() ORDER BY expire_at ASC")
    announcements = cursor.fetchall()

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
    access_token = get_access_token()

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": "https://emawchurch.org//mpesa/callback",  # Update this to your live domain!
        "AccountReference": "Donation",
        "TransactionDesc": "Church Donation"
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload, headers=headers
    )
    print("DARAJA RESPONSE:", response.status_code, response.text)  # Add this to see the real issue
    return jsonify(response.json())

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
                      sender="emawkenya700@gmail.com",
                      recipients=["emawkenya700@gmail.com"])
        msg.body = f"A donation of KES {amount} was made by phone number: {phone}."
        mail.send(msg)
    except Exception as e:
        print("Email sending failed:", e)

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})


def get_access_token():
    url = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(consumer_key, consumer_secret))
    
    print("Access Token Response:", response.status_code, response.text)  # Debug line
    
    return response.json()['access_token']


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
