from flask import Flask, request, jsonify, render_template, redirect, url_for
import hashlib
import redis
import os
import logging
import traceback
import json
from flask_cors import CORS
import time
from urllib.parse import urlparse
from threading import Lock

app = Flask(__name__, 
    static_url_path='/static',
    static_folder='static',
    template_folder='templates'
)
CORS(app)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 内存存储作为后备
class MemoryStorage:
    def __init__(self):
        self._storage = {}
        self._lock = Lock()
    
    def set(self, key, value, ex=None):
        with self._lock:
            self._storage[key] = {
                'value': value,
                'expiry': time.time() + ex if ex else None
            }
            return True
    
    def get(self, key):
        with self._lock:
            if key not in self._storage:
                return None
            data = self._storage[key]
            if data['expiry'] and time.time() > data['expiry']:
                del self._storage[key]
                return None
            return data['value']
    
    def delete(self, key):
        with self._lock:
            if key in self._storage:
                del self._storage[key]
                return True
            return False

# 全局变量
redis_client = None
memory_storage = MemoryStorage()

def get_storage():
    """Get the appropriate storage backend"""
    global redis_client, memory_storage
    
    # 尝试获取 Redis 客户端
    if redis_client is None:
        try:
            redis_client = create_redis_client()
            if redis_client is not None:
                logger.info("Successfully initialized Redis client")
                return redis_client
        except Exception as e:
            logger.warning(f"Failed to initialize Redis, falling back to memory storage: {str(e)}")
    
    # 如果 Redis 不可用，使用内存存储
    logger.info("Using memory storage as fallback")
    return memory_storage

def create_redis_client():
    """Create a new Redis client"""
    try:
        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            logger.error("REDIS_URL environment variable is not set")
            return None

        # 创建 Redis 客户端
        client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            socket_keepalive=True,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
        # 测试连接
        client.ping()
        return client
        
    except Exception as e:
        logger.error(f"Failed to create Redis client: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shorten', methods=['POST'])
def shorten_url():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL field is required'}), 400

        original_url = data['url'].strip()
        if not original_url:
            return jsonify({'error': 'URL cannot be empty'}), 400

        # 获取存储后端
        storage = get_storage()
        if storage is None:
            return jsonify({'error': 'Storage backend not available'}), 500

        # 生成短 URL
        hash_object = hashlib.md5(original_url.encode())
        short_id = hash_object.hexdigest()[:6]
        
        try:
            # 存储 URL（30天过期）
            storage.set(short_id, original_url, 30 * 24 * 60 * 60)
            
            base_url = "https://url-shorten-beryl.vercel.app"
            short_url = f"{base_url}/{short_id}"
            
            # 记录使用的存储后端
            storage_type = "Redis" if isinstance(storage, redis.Redis) else "Memory"
            logger.info(f"URL shortened using {storage_type} storage: {short_url}")
            
            return jsonify({
                'short_url': short_url,
                'storage_type': storage_type.lower()
            })
            
        except Exception as e:
            logger.error(f"Storage operation failed: {str(e)}")
            return jsonify({'error': 'Failed to create short URL'}), 500

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/<short_id>')
def redirect_to_url(short_id):
    try:
        storage = get_storage()
        if storage is None:
            return 'Storage backend not available', 500
            
        original_url = storage.get(short_id)
        if not original_url:
            return 'URL not found', 404
            
        return redirect(original_url, code=302)

    except Exception as e:
        logger.error(f"Redirect error: {str(e)}")
        return 'Error processing redirect', 500

@app.route('/storage/status')
def storage_status():
    """Check storage backend status"""
    try:
        storage = get_storage()
        
        if isinstance(storage, redis.Redis):
            try:
                storage.ping()
                status = {
                    'type': 'redis',
                    'status': 'connected',
                    'message': 'Redis is working properly'
                }
            except Exception as e:
                status = {
                    'type': 'redis',
                    'status': 'error',
                    'message': f'Redis error: {str(e)}'
                }
        else:
            status = {
                'type': 'memory',
                'status': 'active',
                'message': 'Using in-memory storage as fallback'
            }
            
        return jsonify(status)
        
    except Exception as e:
        return jsonify({
            'type': 'unknown',
            'status': 'error',
            'message': f'Error checking storage status: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5003)
