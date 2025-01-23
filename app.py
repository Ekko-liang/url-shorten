from flask import Flask, request, jsonify, render_template, redirect
import hashlib
import redis
import os
import logging
import traceback
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_redis_client():
    redis_url = os.getenv('REDIS_URL')
    logger.info(f"Using Redis URL: {redis_url[:20]}...")  # 只显示URL的前20个字符，保护敏感信息
    
    if not redis_url:
        raise ValueError("REDIS_URL environment variable is required")
        
    try:
        client = redis.from_url(redis_url)
        # 测试连接
        client.ping()
        logger.info("Redis connection successful")
        return client
    except Exception as e:
        logger.error(f"Redis connection error: {str(e)}")
        logger.error(traceback.format_exc())
        raise

# 初始化Redis客户端
try:
    redis_client = get_redis_client()
except Exception as e:
    logger.error(f"Failed to initialize Redis: {str(e)}")
    redis_client = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/debug')
def debug():
    """Debug endpoint to check Redis connection"""
    try:
        if redis_client is None:
            return jsonify({
                'status': 'error',
                'message': 'Redis client not initialized'
            }), 500
            
        # 测试Redis连接
        redis_client.ping()
        
        return jsonify({
            'status': 'ok',
            'redis_connected': True,
            'env_vars': {
                'REDIS_URL_EXISTS': bool(os.getenv('REDIS_URL')),
                'REDIS_URL_LENGTH': len(os.getenv('REDIS_URL', ''))
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/shorten', methods=['POST'])
def shorten_url():
    try:
        if redis_client is None:
            return jsonify({'error': 'Redis not initialized'}), 500

        logger.info("Headers: %s", dict(request.headers))
        logger.info("Request data: %s", request.get_data(as_text=True))
        
        try:
            data = request.get_json()
            logger.info("Parsed JSON data: %s", data)
        except Exception as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return jsonify({'error': 'Invalid JSON data'}), 400

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        if 'url' not in data:
            return jsonify({'error': 'URL field is required'}), 400

        original_url = data['url']
        if not original_url:
            return jsonify({'error': 'URL cannot be empty'}), 400

        # Generate a short hash for the URL
        hash_object = hashlib.md5(original_url.encode())
        short_id = hash_object.hexdigest()[:6]
        
        # Test Redis connection before attempting to store
        try:
            redis_client.ping()
            logger.info("Redis connection test successful")
        except Exception as e:
            logger.error(f"Redis connection test failed: {str(e)}")
            return jsonify({'error': 'Database connection error'}), 500
        
        # Store in Redis
        try:
            redis_client.set(short_id, original_url)
            logger.info(f"Successfully stored in Redis: {short_id} -> {original_url}")
            
            # Verify the storage
            stored_url = redis_client.get(short_id)
            if stored_url:
                logger.info(f"Verification successful: {stored_url.decode('utf-8')}")
            else:
                logger.error("Verification failed: URL not found after storage")
                return jsonify({'error': 'Failed to verify URL storage'}), 500
                
        except Exception as e:
            logger.error(f"Redis storage error: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': f'Failed to store URL: {str(e)}'}), 500
        
        base_url = "https://url-shorten-beryl.vercel.app"
        short_url = f"{base_url}/{short_id}"
        logger.info(f"Generated short URL: {short_url}")
        return jsonify({'short_url': short_url})

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/<short_id>')
def redirect_to_url(short_id):
    try:
        if redis_client is None:
            return 'Database not initialized', 500
            
        logger.info(f"Looking up URL for ID: {short_id}")
        original_url = redis_client.get(short_id)
        
        if original_url is None:
            logger.warning(f"URL not found for ID: {short_id}")
            return 'URL not found', 404
            
        original_url = original_url.decode('utf-8')
        logger.info(f"Found URL: {original_url}")
        return redirect(original_url, code=302)

    except Exception as e:
        logger.error(f"Redirect error: {str(e)}")
        logger.error(traceback.format_exc())
        return 'Error processing redirect', 500

if __name__ == '__main__':
    app.run(debug=True, port=5003)
