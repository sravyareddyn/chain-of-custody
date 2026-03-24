from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import sqlite3
import hashlib
import os
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    filename TEXT,
    uploaded_by TEXT,
    timestamp TEXT,
    hash TEXT,
    case_id TEXT,
    case_name TEXT
)''')

    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        evidence_id INTEGER,
        user TEXT,
        action TEXT,
        timestamp TEXT,
        result TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# ---------------- HASH FUNCTION ----------------
def generate_hash(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(4096):
            sha256.update(chunk)
    return sha256.hexdigest()

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ---------------- HOME ----------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verify/<int:id>', methods=['POST'])
def verify(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT filename, hash FROM evidence WHERE id=?", (id,))
    data = c.fetchone()

    filename = data[0]
    original_hash = data[1]

    filepath = f"uploads/{filename}"
    new_hash = generate_hash(filepath)

    if new_hash == original_hash:
        status = "File is Safe ✅"
    else:
        status = "File Tampered ⚠️"

    conn.close()

    return render_template('verify.html', status=status)

# ---------------- UPLOAD ----------------
@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    user = request.form['user']
    case_id = request.form['case_id']
    case_name = request.form['case_name']

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    file_hash = generate_hash(filepath)
    timestamp = str(datetime.now())

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO evidence (name, filename, uploaded_by, timestamp, hash, case_id, case_name) VALUES (?, ?, ?, ?, ?, ?, ?)",
          (file.filename, file.filename, user, timestamp, file_hash, case_id, case_name))
    conn.commit()
    conn.close()
    

    return redirect(url_for('dashboard'))

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM evidence")
    data = c.fetchall()
    conn.close()

    return render_template('dashboard.html', data=data)

# ---------------- VIEW ----------------
@app.route('/view/<int:eid>')
def view(eid):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM evidence WHERE id=?", (eid,))
    evidence = c.fetchone()

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], evidence[2])

    if not os.path.exists(filepath):
        status = "FILE MISSING ⚠️"
        current_hash = "N/A"
    else:
        current_hash = generate_hash(filepath)
        original_hash = evidence[5]
        status = "INTACT ✅" if current_hash == original_hash else "TAMPERED ❌"

    original_hash = evidence[5]

    status = "INTACT ✅" if current_hash == original_hash else "TAMPERED ❌"

    # LOG ENTRY
    c.execute("INSERT INTO logs (evidence_id, user, action, timestamp, result) VALUES (?, ?, ?, ?, ?)",
              (eid, "Examiner", "VIEW", str(datetime.now()), status))
    conn.commit()
    conn.close()

    return render_template('view.html',
                           evidence=evidence,
                           current_hash=current_hash,
                           original_hash=original_hash,
                           status=status)

# ---------------- LOGS ----------------
@app.route('/logs')
def logs():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM logs")
    logs = c.fetchall()
    conn.close()

    return render_template('logs.html', logs=logs)

@app.route('/tamper/<int:id>', methods=['POST'])
def tamper(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT filename FROM evidence WHERE id=?", (id,))
    file = c.fetchone()[0]

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file)

    with open(filepath, "a") as f:
        f.write("tampered")

    conn.close()

    return redirect(url_for('view', eid=id))

# ---------------- RUN ----------------
if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(host='0.0.0.0', port=5000, debug=True)
