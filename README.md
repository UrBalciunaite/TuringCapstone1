# My Unwrapped Music

In 2024 Spotify Wrapped received a lot of negative feedback about user data being inaccurate and analysis being bland. 

My Unwrapped Music app was created with the intention to provide an alternative to Spotify Wrapped functionality. The app allows 1 user to register to the app and connect their Spotify account. Once a Spotify account is authorised, a background job performs hourly checks if new tracks were played and saves them in Redis database. After some listening, the user can run the app once again and send themselves an analysis on their listened tracks. If the user requests the first analysis, all gathered data will be analysed. For the following analysis, data gathered past last analysis will be analysed.

The applincation is still in MVP mode, meaning that some of the functionalities are at early stage of developement. For example, the app can only be used by one account at the time. Application is created based on OOP principles.

# Spotify endpoints used in a project

- Users > Get User's Profile > https://developer.spotify.com/documentation/web-api/reference/get-users-profile; 
- Player > Get Recently Played Tracks > https://developer.spotify.com/documentation/web-api/reference/get-recently-played

# Classes and their uses

In the project, 7 classes were created:

1. RedisClient
- The main purpose for this class is to store an URL needed to connect to Redis, so that connections would be handled gracefully. Redis is used to store data in hash format about the user and their played tracks.
2. User
- The class is used to create an instance of a user and save it to Redis database. Additional methods connected to User class and used throughout the code are load_user_from_redis, check if user_exists and delete_user.
3. SpotifyAPI
- The class is used to manage the Spotify account authentication, getting data about recently played tracks and interaction with the Spotify API in general. During account authorisation, SpotifyAPI class is used to direct_user_for_authentication and exchange_auth_code_to_access_refresh_tokens, when the callback is handled by SpotifyCallbacks class.
4. SpotifyCallbacks
- The class is used to handle a callback during Spotify account authorisation.
- For callbacks I chose to use Flask framework and ngrok tool for tunneling. Currently, I am running ngrok tunnel on one of my terminal in order to ensure successful authorisation callbacks. Current redirest URI is "https://1fbe-78-61-236-173.ngrok-free.app/callback".
5. Track
- The class was created to store data about listened tracks. Track class has these static methods:
- from_response_extract_tracks_and_save_to_redis - the method is used in a background job to fetch newly played Spotify tracks and save them to Redis. Background job is performed hourly.
- delete_tracks - when account is deleted to delete all tracks as well
- load_tracks_from_redis - to load tracks from Redis for analysis
6. ListeningHabitsAnalyzer
- The class is created to store methods used to analyze the collected data about user's listening habits.
- Analysis is performed on tracks that have played_at date later than the last_analysed. This way, it is ensured that every summary contains only tracks played only after the last summary was generated. For the first summary, all tracks are used for analysis.
7. EmailService
- The class is created to handle email sending once the summary is created.
- To implement this, I used smtplib and email.message modules

# Additional comments on the project code

The main program (Unwrapped.py) should be run:
- To register the account
- To authorise the Spotify account
- To request email summary about your listening habits

The background job (background_task.py) should be run for fetching recently played tracks. It is done using Celery (a task queue implementation for Python) and Redis. To run this successful, redis server should be running, as well as a scheduler (beat) and a worker should be run at the same time in different terminal. 
celery -A background_task worker --loglevel=info
celery -A background_task beat --loglevel=info

