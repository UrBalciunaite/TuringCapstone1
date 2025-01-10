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
- The class is used to handle a callback during Spotify account authorisation. For callbacks I chose to use Flask framework and ngrok tool for tunneling. Currently, I am running ngrok 

# Comments on the project code

When the main script is run (Unwrapped.py), the user should see menu with 5 modes.

1. "add new Spotify account"
When this mode is selected, first of all, the prgram checks if an account already exists in Redis database. If yes, the user is not allowed to register another account 

