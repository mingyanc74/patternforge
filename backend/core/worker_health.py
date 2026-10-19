import redis
from celery.signals import heartbeat_sent, worker_ready
from django.conf import settings


@worker_ready.connect
@heartbeat_sent.connect
def report_worker_heartbeat(**kwargs):
    try:
        redis.Redis.from_url(settings.CACHE_URL, socket_connect_timeout=0.3, socket_timeout=0.3).setex(
            "patternforge:worker-heartbeat", 20, "online"
        )
    except redis.RedisError:
        pass
