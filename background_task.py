from celery import Celery, shared_task
from celery.schedules import crontab
import redis
import time
from Unwrapped import SpotifyAPI, Track

# celery -A background_task worker --loglevel=info
# celery -A background_task beat --loglevel=info

redis_conn = redis.StrictRedis.from_url("redis://default:YGAcin5XIKZzzv9UIR3yw7p3rbeGEE5Y@redis-11155.c328.europe-west3-1.gce.redns.redis-cloud.com:11155")
app = Celery("background_task", broker="redis://default:YGAcin5XIKZzzv9UIR3yw7p3rbeGEE5Y@redis-11155.c328.europe-west3-1.gce.redns.redis-cloud.com:11155")

app.conf.beat_schedule = {
    "fetching_methods": {
        "task": "background_task.fetching_methods",
        "schedule": crontab(minute=0, hour="*") # Every hour
    }
}
app.conf.timezone = "EET"

@app.task
def fetching_methods():
    spotify_api = SpotifyAPI()

    last_checked_timestamp = redis_conn.get("spotify_last_checked")
    if redis_conn.exists("spotify_last_checked"):
        last_checked_timestamp = redis_conn.get("spotify_last_checked")
        if last_checked_timestamp is not None:
            last_checked_timestamp = int(last_checked_timestamp)
    else:
        last_checked_timestamp = 0

    current_timestamp = int(time.time() * 1000) # Convert to miliseconds

    try:
        response = spotify_api.get_recently_played_tracks(after_timestamp=last_checked_timestamp, limit=50)
        if response:
            try:
                Track.from_response_extract_tracks_and_save_to_redis(response)
            except Exception as e:
                print(e)
            redis_conn.set("spotify_last_checked", current_timestamp)
    except Exception as e:
        print(f"An error occured: {e}")