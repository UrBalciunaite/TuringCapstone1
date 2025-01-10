# My Unwrapped Music

In 2024 Spotify Wrapped received a lot of negative feedback about user data being inaccurate and analysis being bland. 

My Unwrapped Music app was created with the intention to provide an alternative to Spotify Wrapped functionality. The app allows 1 user to register to the app and connect their Spotify account. Once a Spotify account is authorised, a background job performs hourly checks if new tracks were played and saves them in Redis database. After some listening, the user can run the app once again and send themselves an analysis on their listened tracks. If the user requests the first analysis, all gathered data will be analysed. For the following analysis, data gathered past last analysis will be analysed.

Spotify endpoints used in a project:
- Users > Get User's Profile > https://developer.spotify.com/documentation/web-api/reference/get-users-profile; 
- Player > Get Recently Played Tracks > https://developer.spotify.com/documentation/web-api/reference/get-recently-played

