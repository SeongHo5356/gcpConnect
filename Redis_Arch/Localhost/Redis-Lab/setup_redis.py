# setup_redis.py
import redis

r = redis.Redis(host='localhost', port=6379, db=0)

# 초기 상태에서 두 서버 모두 사용 가능하다고 가정
r.lpush('available_servers', 'http://localhost:8001', 'http://localhost:8002')

print("Redis initialized with available servers.")