**find-song**

A Reddit bot that auto-replies to comments mentioning u/find-song, as well as comments in r/all that ask "what's the name of the song?" or "what's this song?"


*****

>**How to use find-song**

When mentioned in a comment, find-song will reply if the comment is:

- in a post with a v.redd.it, youtube, or twitch.tv video link
- is a reply to a comment that has a compatible link

Also, if you reply to one of find-song's comments with a link, it will try to find the song.

>**Timestamps**

If a timestamp is included in a comment mentioning find-song, it will search at the provided time. Otherwise it samples from 0:00-0:30. Supported timestamps include:
- 0:30-1:20 (a start and an end in minutes)
- 0:25 (a single minute value, this is the same as 0:25-0:55 since find-song does a 30-second-long search if not given an endpoint)
- 25-120 (a start and an end in seconds. This would be the same as 0:25-2:00)
- 40 (just a single seconds value, this is the same as 0:40-1:10)

You can also reply to one of find-song's comments with a timestamp to make it start a search at the given time. This will make the bot default to any videos/links in the submission itself, not parent comments. 
******
>>**FAQ**

>**Where does find-song get audio fingerprints?**

find-song uses the [ACRCloud API](https://www.acrcloud.com/) to identify audio. There's another bot, u/RecognizeSong, that came after u/find-song that works similarly but uses a different service, [Audd.io](https://audd.io/). Sometimes both bots will reply to u/find-song comments so there's a better chance of recognizing audio.

>**How does it work?**

When find-song replies to your comment, it will first give some information about the search, including the link you provided it and the timestamps it's searching from. After it does an ACRCloud request it will edit this comment to include the song name and the artists it's by. If ACRCloud returns an error, it edits the comment to "No song was found".

>**Where does find-song get its links?**

Before editing the song information into one of its comments, find-song will do a quick google search using [selenium](https://selenium-python.readthedocs.io/installation.html)  and the song title & artists. If it finds a youtube video, it does an ACRCloud request on that video to see if its audio matches that of the first request - if it does, it includes the video in its reply.

If the youtube search didn't yield any results or didn't match, it searches the Spotify API to find *exact matches* of the song name & artists from the ACRCloud request.

If none of those work, find-song defualts to constructing a link using ACRCloud's database website, [aha-music.com](https://www.aha-music.com/7427816c27a56f58692975dcb6e5c0fe/Rick_Astley-Never_Gonna_Give_You_Up-7427816c27a56f58692975dcb6e5c0fe?utm_source=chrome&utm_medium=extension).

>**Other questions, comments, critiques, etc etc**

I'm by no means a master coder, so if you want to tell me about one of the mistakes or possible improvements please contact me via [GitHub](https://github.com/mike-fmh/find-song) or via my [Reddit](https://www.reddit.com/message/compose?to=Fhyke&subject=contact%20about%20find-song).
