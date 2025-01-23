from flask import Flask, request, jsonify, render_template, redirect
import hashlib
import redis
import os
import logging
import traceback
import json
from flask_cors import CORS
import time

app = Flask(__name__)
CORS(app)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_redis_client():
    # 获取并记录所有环境变量（注意不要记录敏感值）
    env_vars = {k: '***' if 'URL' in k or 'KEY' in k or 'SECRET' in k else v 
                for k, v in os.environ.items()}
    logger.info(f"Environment variables: {json.dumps(env_vars, indent=2)}")
    
    redis_url = os.getenv('REDIS_URL')
    if not redis_url:
        logger.error("REDIS_URL environment variable is missing")
        raise ValueError("REDIS_URL environment variable is required")
    
    # 记录 URL 的结构（隐藏敏感信息）
    parts = redis_url.split('@')
    if len(parts) == 2:
        auth_part = parts[0].split(':')
        if len(auth_part) == 3:  # protocol:username:password
            masked_url = f"{auth_part[0]}:{auth_part[1]}:***@{parts[1]}"
            logger.info(f"Redis URL structure: {masked_url}")
        else:
            logger.error("Unexpected Redis URL format (auth part)")
    else:
        logger.error("Unexpected Redis URL format (missing @)")
    
    try:
        # 在AWS Lambda环境中增加重试机制
        max_retries = 3
        retry_delay = 1  # 秒
        
        for attempt in range(max_retries):
            try:
                client = redis.from_url(
                    redis_url,
                    socket_timeout=5,  # 增加超时时间
                    socket_connect_timeout=5,
                    retry_on_timeout=True
                )
                # 测试连接
                client.ping()
                logger.info("Redis connection successful")
                return client
            except (redis.ConnectionError, redis.TimeoutError) as e:
                if attempt == max_retries - 1:  # 最后一次尝试
                    raise
                logger.warning(f"Redis connection attempt {attempt + 1} failed: {str(e)}")
                time.sleep(retry_delay)
                continue
            except Exception as e:
                logger.error(f"Unexpected Redis error: {str(e)}")
                raise
                
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error after {max_retries} attempts: {str(e)}")
        logger.error(traceback.format_exc())
        raise
    except Exception as e:
        logger.error(f"Unexpected Redis error: {str(e)}")
        logger.error(traceback.format_exc())
        raise

# 使用延迟初始化
redis_client = None

def get_redis():
    global redis_client
    if redis_client is None:
        try:
            redis_client = get_redis_client()
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {str(e)}")
            logger.error(traceback.format_exc())
    return redis_client

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
        
        client = get_redis()
        if client is None:
            return jsonify({
                'status': 'error',
                'message': 'Redis client not initialized',
                'environment': env_vars,
                'redis_url_exists': bool(os.getenv('REDIS_URL')),
                'redis_url_length': len(os.getenv('REDIS_URL', ''))
            }), 500
            
        # 测试Redis连接
        client.ping()
        
        return jsonify({
            'status': 'ok',
            'redis_connected': True,
            'environment': env_vars,
            'redis_url_exists': bool(os.getenv('REDIS_URL')),
            'redis_url_length': len(os.getenv('REDIS_URL', ''))
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc(),
            'environment': env_vars,
            'redis_url_exists': bool(os.getenv('REDIS_URL')),
            'redis_url_length': len(os.getenv('REDIS_URL', ''))
        }), 500

@app.route('/shorten', methods=['POST'])
def shorten_url():
    try:
        client = get_redis()
        if client is None:
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
        
        # Store in Redis
        try:
            client.set(short_id, original_url)
            logger.info(f"Successfully stored in Redis: {short_id} -> {original_url}")
            
            # Verify the storage
            stored_url = client.get(short_id)
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
        client = get_redis()
        if client is None:
            return 'Database not initialized', 500
            
        logger.info(f"Looking up URL for ID: {short_id}")
        original_url = client.get(short_id)
        
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
