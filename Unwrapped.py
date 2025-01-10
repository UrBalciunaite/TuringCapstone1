import re
import requests
import redis
import smtplib
from urllib.parse import urlencode
from flask import Flask, request, redirect
from threading import Thread
from datetime import datetime
from email.message import EmailMessage

class RedisClient:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = redis.StrictRedis.from_url("redis://default:YGAcin5XIKZzzv9UIR3yw7p3rbeGEE5Y@redis-11155.c328.europe-west3-1.gce.redns.redis-cloud.com:11155")
        return cls._instance
        
class User:
    def __init__(self, email, username, access_token, refresh_token):
        self.email = email
        self.username = username
        self.is_authenticated = "N"
        self.access_token = access_token
        self.refresh_token = refresh_token
    
    def __str__(self):
        return f"Username - {self.username}, email - {self.email}"

    redis_client = RedisClient.get_instance()
    _redis_key = "SingleUser"

    def save_user_to_redis(self):
        User.redis_client.hset(User._redis_key, mapping ={
            "email": self.email,
            "username": self.username,
            "is_authenticated": self.is_authenticated,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token
        })
    
    @classmethod
    def load_user_from_redis(cls):
        user_data = cls.redis_client.hgetall(cls._redis_key)
        if user_data:
            return cls(
                email=user_data[b'email'].decode('utf-8'),
                username=user_data[b'username'].decode('utf-8'),
                access_token=user_data[b'access_token'].decode('utf-8'),
                refresh_token=user_data[b'refresh_token'].decode('utf-8')
            )
        print("No user found in Redis.")
        return None
    
    @classmethod
    def user_exists(cls):
        exists = cls.redis_client.exists(cls._redis_key)
        return exists == 1
    
    @classmethod
    def delete_user(cls):
        if not cls.user_exists():
            return False
        
        result = cls.redis_client.delete(cls._redis_key)
        if result == 1:
            return True
        else:
            return False

class SpotifyAPI:
    def __init__(self, client_id="9b1bd87cabb34437a30aa68102ba5e04", client_secret="082722c42b4e49eb9eb9184aa5053423", redirect_uri="https://1fbe-78-61-236-173.ngrok-free.app/callback"):
        self.client_id = client_id 
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None
        self.refresh_token = None
    
    def direct_user_for_authentication(self):
        auth_url = "https://accounts.spotify.com/authorize"
        auth_params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": "user-read-recently-played"
        }
        print("Go to the following URL to authorize:")
        print(f"{auth_url}?{urlencode(auth_params)}")
        print("---------------------")
        return

    def exchange_auth_code_to_access_refresh_tokens(self, auth_code):
        token_url = "https://accounts.spotify.com/api/token"
        token_params = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret
            }
        response = requests.post(token_url, data=token_params)
        token_info = response.json()
        self.access_token = token_info.get("access_token")
        self.refresh_token = token_info.get("refresh_token")
        return (self.access_token, self.refresh_token)
    
    def refresh_access_token(self):
        user = User.load_user_from_redis()
        token_url = "https://accounts.spotify.com/api/token"
        token_params = {
            "grant_type": "refresh_token",
            "refresh_token": user.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        response = requests.post(token_url, data=token_params)
        token_info = response.json()
        user.access_token = token_info.get("access_token")
        user.save_user_to_redis()
        return 

    def get_recently_played_tracks(self, after_timestamp, limit=50):
        user = User.load_user_from_redis()
        access_token = user.access_token

        if after_timestamp is None:
            raise ValueError("Missing 'after_timestamp' value.")
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        params = {
            "after": after_timestamp,
            "limit": limit
        }
        response = requests.get('https://api.spotify.com/v1/me/player/recently-played', headers=headers, params=params)
        
        if response.status_code not in [200, 401]:
            print("Failed to fetch recently played tracks:", response.json())
            return []
        elif response.status_code == 401:
            SpotifyAPI.refresh_access_token(self)

        tracks_data = response.json().get('items', [])
        return tracks_data

class SpotifyCallback:
    def __init__(self):
        # Initialize the Flask app instance
        self.app = Flask(__name__)
        # Setup routes
        self.authorization_code = None
        self.setup_routes()

    def setup_routes(self):
        # Define the home route
        @self.app.route("/")
        def home():
            return

        # Define the callback route
        @self.app.route("/callback")
        def callback():
            self.authorization_code = request.args.get("code")
            if self.authorization_code:
                return "Access token received! Please enter CTRL + C in command line to quit "
            else:
                return 'No authentication token received'
            
    def run(self, port=8080):
        def start_flask():
            self.app.run(port=port, use_reloader=False)

        thread = Thread(target=(self.app.run(port=port, use_reloader=False)))
        thread.start()
        
        while self.authorization_code is None:
            pass
        return self.authorization_code

class Track:
    def __init__(self, name, artist, album, duration, played_at):
        self.name = name
        self.artist = artist
        self.album = album
        self.duration = duration
        self.played_at = played_at

    def __str__(self):
        return f"Song \"{self.name}\" by {self.artist} from \"{self.album}\" album."
    
    @staticmethod
    def from_response_extract_tracks_and_save_to_redis(response, redis_client=RedisClient.get_instance()):
        for item in response:
            # Access "track" dictionary within each "item"
            track_info = item.get("track",{})

            # Extract data for object creation
            track_name = track_info.get("name")
            album_info = track_info.get("album", {})
            album_name = album_info.get("name")
            artist_list = track_info.get("artists", [])
            artist = artist_list[0].get("name") if artist_list else "Unknown"
            duration_ms = track_info.get("duration_ms")
            played_at = item.get("played_at") ################

            # Generate unique ID
            track_id = redis_client.incr("Spotify:track:global_id")

            # Create track
            track = Track(name=track_name, artist=artist, album=album_name, duration=duration_ms, played_at=played_at)
            
            # Save each Track to Redis as a hash
            redis_key = f"Spotify:track:{track_id}"
            redis_client.hset(redis_key, mapping={
                "name": track.name,
                "artist": track.artist,
                "album_name": track.album,
                "duration": track.duration,
                "played_at": track.played_at ###############
            })
        return
    
    @staticmethod
    def delete_tracks(redis_client=RedisClient.get_instance()):
        pattern = "Spotify:track:*"
        keys_to_delete = redis_client.keys(pattern)

        if keys_to_delete:
            redis_client.delete(*keys_to_delete)
            return True
        else:
            return False

    @staticmethod
    def load_tracks_from_redis(redis_client=RedisClient.get_instance()):
        pattern = "Spotify:track:*"
        keys_to_load = redis_client.keys(pattern)
        if not keys_to_load:
            print("No track data to analyse.")
            return []
        loaded_tracks = []
        for key in keys_to_load:
            if key == b"Spotify:track:global_id":
                continue
            try:
                track_data = redis_client.hgetall(key)
                if not track_data:
                    print(f"No data found for key: {key}")
                    continue

                track = Track(
                    name = track_data.get(b"name").decode("utf-8"),
                    artist = track_data.get(b"artist").decode("utf-8"),
                    album = track_data.get(b"album_name").decode("utf-8"),
                    duration = int(track_data.get(b"duration")),
                    played_at = track_data.get(b"played_at").decode("utf-8")
                )
                loaded_tracks.append(track)
            except Exception as e:
                print(f"Error occured when loading track data from Redis: {e}")
        return loaded_tracks

class ListeningHabitsAnalyzer:
    def __init__(self, tracks, redis_client=RedisClient.get_instance()):
        self.tracks = tracks
        self.redis_client = redis_client
        self.last_analysed_key = "Spotify:last_analysed"

    def get_last_analysed(self):
        last_analysed_str = self.redis_client.get(self.last_analysed_key)
        if last_analysed_str:
            last_analysed = datetime.fromisoformat(last_analysed_str.decode('utf-8'))
            return last_analysed
        return None
    
    def update_last_analysed(self):
        now = datetime.now().isoformat()
        self.redis_client.set(self.last_analysed_key, now)

    def filter_tracks_by_last_analysed(self):
        last_analysed = self.get_last_analysed()
        if last_analysed is None:
            return self.tracks # If no previous analysis, use all tracks
        filtered_tracks = [
            track for track in self.tracks
            if datetime.fromisoformat(track.played_at).replace(tzinfo=None) > last_analysed.replace(tzinfo=None)
        ]
        return filtered_tracks

    
    def total_listening_time(self, filtered_tracks):
        total_time_ms = sum(track.duration for track in filtered_tracks)
        total_time_seconds = total_time_ms // 1000
        hours, remainder = divmod(total_time_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            total_time = f"{hours} hours {minutes} minutes and {seconds} seconds"
        elif minutes > 0:
            total_time = f"{minutes} minutes and {seconds} seconds"
        else:
            total_time = f"{seconds} seconds"
        return total_time

    def most_listened_artist(self, filtered_tracks):
            artist_count = {}
            for track in filtered_tracks:
                if track.artist in artist_count:
                    artist_count[track.artist] += 1
                else:
                    artist_count[track.artist] = 1
            most_listened_artist = max(artist_count, key=artist_count.get, default="N/A")
            return most_listened_artist

    def most_listened_album(self, filtered_tracks):
        album_count = {}
        album_artist = {}
        for track in filtered_tracks:
            if track.album in album_count:
                    album_count[track.album] += 1
            else:
                album_count[track.album] = 1
                album_artist[track.album] = track.artist
        most_listened_album = max(album_count, key=album_count.get, default="N/A")
        most_listened_album_artist = album_artist.get(most_listened_album, "N/A")
        return most_listened_album, most_listened_album_artist

    def most_listened_track(self, filtered_tracks):
        track_count = {}
        track_artis = {}
        for track in filtered_tracks:
            if track.name in track_count:
                track_count[track.name] +=1
            else:
                track_count[track.name] = 1
                track_artis[track.name] = track.artist
        most_listened_track = max(track_count, key=track_count.get, default="N/A")
        most_listened_track_artist = track_artis.get(most_listened_track, "N/A")
        return most_listened_track, most_listened_track_artist

    def summary(self):
        filtered_tracks = self.filter_tracks_by_last_analysed()
        if not filtered_tracks:
            summary_output = "There are no mew records to analyse. Play more Spotify tracks and come back for a summary later!"
            return summary_output
        
        total_listening_time = self.total_listening_time(filtered_tracks)
        most_listened_artist = self.most_listened_artist(filtered_tracks)
        most_listened_album, album_artist = self.most_listened_album(filtered_tracks)
        most_listened_track, track_artist = self.most_listened_track(filtered_tracks)
        summary_output = (
            f"Total listening time: {total_listening_time}.\n"
            f"Most listened artist: {most_listened_artist}.\n"
            f"Most listened album: {most_listened_album} by {album_artist}.\n"
            f"Most listened track: {most_listened_track} by {track_artist}.\n"
        )
        self.update_last_analysed()
        return summary_output

class EmailService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = "uba3672@gmail.com"
        self.sender_password = "sawt chnp gtyi ftpu"

    def send_email(self, message):
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(message)
        except Exception as e:
            return e
        else:
            print("Check your inbox for an update on your listening habits!")
        finally:
            server.quit()

def is_valid_email(email):
    email_format = re.compile(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")
    return bool(email_format.match(email))

def menu():
    print("---------------------")
    print("MENU")
    print("---------------------")
    print("What would you like to do?")
    print("1 - add new Spotify account")
    print("2 - retry Spotify account authorisation")
    print("3 - delete your Spotify account")
    print("4 - send an email with summary about listening habits")
    print("5 - exit the program")
    print("---------------------")
    select_mode = int(input("Mode: "))

    if select_mode == 1:
        print("---------------------")
        m1_add_account()
        menu()
    elif select_mode == 2:
        print("---------------------")
        m2_authorize_account()
        menu()
    elif select_mode == 3:
        print("---------------------")
        m3_delete_account()
        menu()
    elif select_mode == 4:
        print("---------------------")
        m4_create_summary_send_email()
        menu()
    elif select_mode == 5:
        print("---------------------")
        print("You selected to exit the program.")
        print("Bye!")
        exit(0)
    else:
        print("Invalid mode selected. Please try again")
        menu()

def m1_add_account():
    user1 = User(email="None", username="None", access_token="None", refresh_token="None")
    if not user1.user_exists():
        print("---------------------")
        print("Let's add a Spotify account!")
        print("")

        username = input("What is your spotify username? ")
        print("")
        while True:
            email = input("To which email you want to receive emails? ")
            print("---------------------")
            if is_valid_email(email):
                break
            else:
                print("The email address is invalid. Please try again.")
            print("")

        user = User(email=email, username=username, access_token="None", refresh_token="None")
        user.save_user_to_redis()
        print("Your Spotify account is now in our database.")
        print("---------------------")
        print("And do not forget to authorise your account through Spotify API (mode 2).")
        return
    else:
        print("User already exists")
        print("---------------------")
        print("This app is still in MVP stage, therefore only 1 account can be registered at the time.")
        print("If you wish to add another account, please delete the current one (mode 3)")

def m2_authorize_account():
    spotify_api = SpotifyAPI()
    spotify_callback = SpotifyCallback()

    try:
        spotify_api.direct_user_for_authentication()
        auth_code = spotify_callback.run(port=8080)
        tokens = spotify_api.exchange_auth_code_to_access_refresh_tokens(auth_code)
    except Exception as e:
        print("---------------------")
        print(f"Unexpected error during authorization: {e}")
        return
    else:
        try:
            user = User.load_user_from_redis()
            user.access_token = tokens[0]
            user.refresh_token = tokens[1]
            user.is_authenticated = "Y"
            user.save_user_to_redis()
        except Exception as e:
            print(e)
            print("---------------------")
            print(f"Unexpected error when saving tokens: {e}")
            return
        else:
            print("\n---------------------")
            print("Your account was authorised!")
            print("Keep listening music through Spotify and on a weekly basis you will receive our emails.")
            return
   
def m3_delete_account():
    deleted_user_successfully = User.delete_user()
    if deleted_user_successfully:
        print("User was deleted successfully!")

        deleted_tracks_successfully = Track.delete_tracks()
        if deleted_tracks_successfully:
            print("---------------------")
            print("Tracks were deleted successfully!")
            return
        else:
            print("---------------------")
            print("Tracks were not deleted, a problem occured.")
            return
    else:
        print("User was not deleted, a problem occured.")
        return
        
def m4_create_summary_send_email():
    redis_client = RedisClient.get_instance()
    loaded_tracks = Track.load_tracks_from_redis(redis_client)
    if loaded_tracks:
        try:    
            analyzer = ListeningHabitsAnalyzer(loaded_tracks, redis_client)
            summary = analyzer.summary()
        except Exception as e:
            print(f"Failed to analyse listening data: {e}")
            return

        try:
            user = User.load_user_from_redis()
            email_message = (
                f"Hello {user.username}!\n\n"
                f"Thanks for using 'My Wrapped Music' application!\n"
                f"Please be informed, that this email analyses what you listened after your previous analysis.\n"
                f"If this is your first analysis email, in this case, analysis contains all data that was gathered since Spotify account authorisation :).\n\n"
                f"Here is your listening habits summary: \n"
                f"{summary}\n"
                f"Keep on listening and keep receiving insights on your listening habits!\n\n"
                f"Never Gonna let you down, Never Gonna Give You Up,\n"
                f"'My Unwrapped Music' team (Urte)"
            )
            email_service = EmailService()
            email_content = EmailMessage()
            email_content["Subject"] = "My Unwrapped Music"
            email_content["From"] = email_service.sender_email
            email_content["To"] = user.email
            email_content.set_content(email_message)
        except Exception as e:
            print(f"Failed to create an email: {e}")
            return

        try:
            email_service.send_email(email_content)
        except Exception as e:
            print(f"Failed to send the email: {e}")
            return
    else:
        print("No listened tracks to analyse.")

def main():
    print("---------------------")
    print("WELCOME to the My Unwrapped Music app!")
    print("- You can connect your Spotify account to this app so we can collect data about your recently played tracks.")
    print("- Once your account is connected and we gathered some data about your tracks, feel free to send out yourself an email with your listening habits analysis.")
    menu()

if __name__ == "__main__":
    main()
