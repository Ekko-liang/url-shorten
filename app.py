from flask import Flask, request, jsonify, render_template
import hashlib
import sqlite3
import os

app = Flask(__name__)

# Initialize in-memory SQLite database for Vercel (since Vercel's filesystem is read-only)
def init_db():
    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS urls
        (id TEXT PRIMARY KEY, original_url TEXT)
    ''')
    conn.commit()
    return conn

# Global connection for in-memory database
db_conn = init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shorten', methods=['POST'])
def shorten_url():
    original_url = request.json.get('url')
    if not original_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    # Generate a short hash for the URL
    hash_object = hashlib.md5(original_url.encode())
    short_id = hash_object.hexdigest()[:6]
    
    # Store in database
    c = db_conn.cursor()
    try:
        c.execute('INSERT INTO urls (id, original_url) VALUES (?, ?)',
                 (short_id, original_url))
        db_conn.commit()
    except sqlite3.IntegrityError:
        # If the short_id already exists, just return it
        pass
    
    # Get the base URL from request
    base_url = request.headers.get('X-Forwarded-Proto', 'http') + '://' + request.headers.get('X-Forwarded-Host', request.host)
    short_url = f"{base_url}/{short_id}"
    return jsonify({'short_url': short_url})

@app.route('/<short_id>')
def redirect_to_url(short_id):
    c = db_conn.cursor()
    c.execute('SELECT original_url FROM urls WHERE id = ?', (short_id,))
    result = c.fetchone()
    
    if result is None:
        return 'URL not found', 404
    return render_template('redirect.html', url=result[0])

# For local testing
if __name__ == '__main__':
    app.run(debug=True, port=5003)
