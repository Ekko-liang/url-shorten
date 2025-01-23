from flask import Flask, request, jsonify, render_template, redirect
import hashlib
import redis
import os
import logging
import traceback
import json
from flask_cors import CORS
import time
from redis.connection import ConnectionPool

app = Flask(__name__)
CORS(app)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局连接池
redis_pool = None
redis_client = None

def init_redis_pool():
    global redis_pool
    if redis_pool is None:
        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            logger.error("REDIS_URL environment variable is missing")
            raise ValueError("REDIS_URL environment variable is required")
        
        logger.info("Initializing Redis connection pool...")
        redis_pool = ConnectionPool.from_url(
            redis_url,
            max_connections=10,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
        logger.info("Redis connection pool initialized")
    return redis_pool

def get_redis():
    global redis_client, redis_pool
    try:
        if redis_client is None:
            if redis_pool is None:
                redis_pool = init_redis_pool()
            redis_client = redis.Redis(
                connection_pool=redis_pool,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                decode_responses=True  # 自动解码响应
            )
            # 测试连接
            redis_client.ping()
            logger.info("Redis client initialized and connected")
        return redis_client
    except Exception as e:
        logger.error(f"Failed to initialize Redis client: {str(e)}")
        logger.error(traceback.format_exc())
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/debug')
def debug():
    """Debug endpoint to check Redis connection"""
    try:
        # 获取所有环境变量（隐藏敏感值）
        env_vars = {k: '***' if 'URL' in k or 'KEY' in k or 'SECRET' in k else v 
                   for k, v in os.environ.items()}
        
        redis_url = os.getenv('REDIS_URL', '')
        url_parts = redis_url.split('@')
        masked_url = f"{url_parts[0].split(':')[0]}:***@{url_parts[1]}" if len(url_parts) > 1 else "invalid_url"
        
        client = get_redis()
        if client is None:
            return jsonify({
                'status': 'error',
                'message': 'Redis client not initialized',
                'environment': env_vars,
                'redis_url_exists': bool(redis_url),
                'redis_url_length': len(redis_url),
                'redis_url_format': masked_url
            }), 500
            
        # 测试Redis连接
        client.ping()
        
        return jsonify({
            'status': 'ok',
            'redis_connected': True,
            'environment': env_vars,
            'redis_url_exists': bool(redis_url),
            'redis_url_length': len(redis_url),
            'redis_url_format': masked_url
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc(),
            'environment': env_vars,
            'redis_url_exists': bool(redis_url),
            'redis_url_length': len(redis_url),
            'redis_url_format': masked_url
        }), 500

@app.route('/shorten', methods=['POST'])
def shorten_url():
    try:
        client = get_redis()
        if client is None:
            return jsonify({'error': 'Redis not initialized'}), 500

        try:
            data = request.get_json()
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
        
        try:
            # Store in Redis with expiration (e.g., 30 days)
            client.setex(short_id, 30 * 24 * 60 * 60, original_url)
            logger.info(f"Stored URL in Redis: {short_id} -> {original_url}")
            
            # Verify storage
            stored_url = client.get(short_id)
            if not stored_url:
                raise Exception("Failed to verify URL storage")
                
        except Exception as e:
            logger.error(f"Redis storage error: {str(e)}")
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
        client = get_redis()
        if client is None:
            return 'Database not initialized', 500
            
        logger.info(f"Looking up URL for ID: {short_id}")
        original_url = client.get(short_id)
        
        if original_url is None:
            logger.warning(f"URL not found for ID: {short_id}")
            return 'URL not found', 404
            
        logger.info(f"Found URL: {original_url}")
        return redirect(original_url, code=302)

    except Exception as e:
        logger.error(f"Redirect error: {str(e)}")
        logger.error(traceback.format_exc())
        return 'Error processing redirect', 500

if __name__ == '__main__':
    app.run(debug=True, port=5003)
