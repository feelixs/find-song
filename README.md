**songsearchbot**

Find the song that's playing in a Reddit post by mentioning u/songsearchbot in its comments. If there are multiple songs in the video you should tell the bot where to look via a timestamp in hour:min:sec format (5 seconds would be 0:0:05, 5 min 0:5:0, etc). 

For example the comment 
>[u/songsearchbot](https://www.reddit.com/user/songsearchbot) 0:0:10

would tell the bot to find the song playing 10 seconds into the video.

Note that the API may not necessarily have every song in existence, and that the longer the video, the more accurate the API. Video segments that are less than ~15s in length may return a 'no song found', but it depends on the song.

The API is fairly accurate even when background noise is present, but it will not work if the music is completely drowned out. For best results, try to find a clip that has a decent stretch of uninterrupted music.

If a mention doesn't have a timestamp, find-song will start at the beginning of the video.

***
**Donations**

If you find this project helpful, please consider supporting it through a [donation](https://ko-fi.com/songsearch).

The ACRCloud sound fingerprint API is a premium service, so every donation is appreciated!
