from flask import Flask, request, jsonify, render_template, redirect
import hashlib
import redis
import os

app = Flask(__name__)

# 使用Redis数据库
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
redis_client = redis.from_url(redis_url)

@app.route('/')
def index():
    print("Accessing index page")  # Debug log
    return render_template('index.html')

@app.route('/shorten', methods=['POST'])
def shorten_url():
    print("Received shorten request")  # Debug log
    original_url = request.json.get('url')
    if not original_url:
        print("No URL provided")  # Debug log
        return jsonify({'error': 'No URL provided'}), 400
    
    # Generate a short hash for the URL
    hash_object = hashlib.md5(original_url.encode())
    short_id = hash_object.hexdigest()[:6]
    
    # Store in Redis
    redis_client.set(short_id, original_url)
    
    # Use hardcoded domain for Vercel deployment
    base_url = "https://url-shorten-beryl.vercel.app"
    short_url = f"{base_url}/{short_id}"
    print(f"Generated short URL: {short_url}")  # Debug log
    return jsonify({'short_url': short_url})

@app.route('/<short_id>')
def redirect_to_url(short_id):
    print(f"Accessing short URL with ID: {short_id}")  # Debug log
    original_url = redis_client.get(short_id)
    
    if original_url is None:
        print(f"URL not found for ID: {short_id}")  # Debug log
        return 'URL not found', 404
        
    print(f"Redirecting to: {original_url.decode('utf-8')}")  # Debug log
    return redirect(original_url.decode('utf-8'), code=302)

# For local testing
if __name__ == '__main__':
    app.run(debug=True, port=5003)
