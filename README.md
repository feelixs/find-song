**find-song: Music recognition for Reddit**


Mention u/find-song in the comments of a post to find the song playing in it.

![image](/images/findsong1.JPG)

******
<br />

<br />


**Optional parameters & Extra functionalities**

You can give find-song a timestamp if you want him to search at a specific point in the video.

![image](/images/findsong2.JPG)



<br />

It's also possible to directly supply find-song a link to sample - doing so will override the submission link:



![image](/images/findsong3.JPG)

<br />

This also works when replying to comments with links:

![image](/images/findsong4.JPG)

<br />

<br />

<br />

******

**More info**

>**Where does find-song get fingerprints?**

find-song uses the ACRCloud API to identify audio. The API is fairly accurate, even on videos where there's some background noise in addition to the song. In general the longer the clip the better, find-song usually has the most trouble with clips <15 seconds long.

There's also another bot that came after u/find-song which works similarly, u/RecognizeSong, but it uses a different service. Sometimes both bots will reply to u/find-song comments, but it depends on the subreddit and if u/RecognizeAudio identified the song as well.


>**Where does it get its links?**

Before replying with the song information, find-song will do a search on the Spotify API to find exact matches of the song name & artists from the ACRCloud request.

If the spotify search doesn't work, find-song defaults to constructing a link using ACRCloud's database website, aha-music.com.

<br />

<br />

******

If you have any suggestions, comments, or questions you can contact me via GitHub or [Reddit](https://www.reddit.com/message/compose?to=Fhyke&subject=contact%20about%20find-song)

Thanks for reading & have fun with the bot!

******

[Donate](https://ko-fi.com/findsong)
