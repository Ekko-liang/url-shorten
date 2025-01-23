from flask import Flask, request, jsonify, render_template, redirect
import hashlib
import redis
import os
import logging

app = Flask(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 使用Redis数据库
redis_url = os.getenv('REDIS_URL')
if not redis_url:
    logger.error("REDIS_URL not set in environment variables")
    raise ValueError("REDIS_URL environment variable is required")

try:
    redis_client = redis.from_url(redis_url)
    redis_client.ping()  # Test the connection
    logger.info("Successfully connected to Redis")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {str(e)}")
    raise

@app.route('/')
def index():
    logger.info("Serving index page")
    return render_template('index.html')

@app.route('/shorten', methods=['POST'])
def shorten_url():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            logger.warning("No URL provided in request")
            return jsonify({'error': 'No URL provided'}), 400

        original_url = data['url']
        if not original_url:
            logger.warning("Empty URL provided")
            return jsonify({'error': 'URL cannot be empty'}), 400

        # Generate a short hash for the URL
        hash_object = hashlib.md5(original_url.encode())
        short_id = hash_object.hexdigest()[:6]
        
        # Store in Redis
        try:
            redis_client.set(short_id, original_url)
            logger.info(f"Stored URL mapping: {short_id} -> {original_url}")
        except Exception as e:
            logger.error(f"Redis error while storing URL: {str(e)}")
            return jsonify({'error': 'Failed to store URL'}), 500
        
        # Use hardcoded domain for Vercel deployment
        base_url = "https://url-shorten-beryl.vercel.app"
        short_url = f"{base_url}/{short_id}"
        logger.info(f"Generated short URL: {short_url}")
        return jsonify({'short_url': short_url})

    except Exception as e:
        logger.error(f"Unexpected error in /shorten: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/<short_id>')
def redirect_to_url(short_id):
    try:
        logger.info(f"Attempting to redirect {short_id}")
        original_url = redis_client.get(short_id)
        
        if original_url is None:
            logger.warning(f"URL not found for ID: {short_id}")
            return 'URL not found', 404
            
        original_url = original_url.decode('utf-8')
        logger.info(f"Redirecting {short_id} to {original_url}")
        return redirect(original_url, code=302)

    except Exception as e:
        logger.error(f"Error during redirect: {str(e)}")
        return 'Error processing redirect', 500

if __name__ == '__main__':
    app.run(debug=True, port=5003)
