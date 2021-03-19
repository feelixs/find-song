**find-song**

A Reddit bot that auto-replies to comments in r/all that ask "what song is this?" or "what's this song?"

It's also possible to request the bot look through a video by mentioning u/find-song in its comments. 
If there are multiple songs in the video you can tell the bot where to look via a timestamp in hour:min:sec format (5 seconds would be 0:0:05, 5 min 0:5:0, etc). 

For example the comment 
>[u/find-song](https://www.reddit.com/user/find-song) 0:0:10

would tell the bot to find the song playing 10 seconds into the video.

This project uses the ACRCloud API for it's audio recognition. Note that the API may not necessarily have every song in existence, and that the longer the video, the more accurate the API. Video segments that are less than ~15s in length may return a 'no song found', but it depends on the song.

The API is fairly accurate even when background noise is present, but it will not work if the music is completely drowned out. For best results, try to find a clip that has a decent stretch of uninterrupted music.

If a mention doesn't have a timestamp, find-song will start at the beginning of the video.

******

If you want to know what song is playing in a YouTube video, you can comment 
>u/find-song (youtube link)

and the bot will reply to you. Most youtube timestamp quicklinks will work (&t=, &start=, &time_continue=, etc)

******

**Contact**

If you there's a bug, an optimization, or suggestion you'd like to point out or suggest I'm all ears.

I'm by no means a master Python coder, so if you notice something amiss don't hesitate to reach out!
