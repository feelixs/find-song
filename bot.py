import config
import praw
import traceback

output_file = 'output.mp4'


def authenticate():
    login = praw.Reddit(username='find-song', password=config.Reddit.psw, user_agent="songsearchv1", client_id=config.Reddit.client_id, client_secret=config.Reddit.client_secret)
    return login


def recognize_audio(file, start_sec=0):
    """Requests data from ACRCloud and re-formats for manageability"""
    from acrcloud.recognizer import ACRCloudRecognizer
    import json
    login = {
        "access_key": config.ACR.key,
        "access_secret": config.ACR.secret,
        "host": "identify-us-west-2.acrcloud.com"
    }
    acr = ACRCloudRecognizer(login)
    data = json.loads(acr.recognize_by_file(file, start_sec))

    # use acrcloud recognize function on file provided in get_song args, and load the data into a json object

    # for each json value we want, try to get it from the API request's data.
    # If it throws an exception, an error probably occurred with the
    # API request, so set the value to nothing
    try:
        score = data['metadata']['music'][0]['score']
    except:
        score = 0
    try:
        artists = data['metadata']['music'][0]['artists'][0]['name']
    except:
        artists = ""
    try:
        genres = data["metadata"]["music"][0]["genres"][0]["name"]
    except:
        genres = ""
    try:
        album = data["metadata"]["music"][0]["album"]["name"]
    except:
        album = ""
    try:
        title = data["metadata"]["music"][0]["title"]
    except:
        title = ""
    try:
        releasedate = data["metadata"]["music"][0]["release_date"]
    except:
        releasedate = ""
    try:
        label = data["metadata"]["music"][0]["label"]
    except:
        label = ""
    try:
        duration = data["metadata"]["music"][0]["duration_ms"]
    except:
        duration = 0
    try:
        play_offset = data["metadata"]["music"][0]["play_offset_ms"]
    except:
        play_offset = 0
    try:
        acrID = data["metadata"]["music"][0]["acrid"]
    except:
        acrID = ""

    ms_until_over = int(duration) - int(play_offset)

    if title != "":
        return {"msg": "success", "score": score, "title": title, "artists": artists, "album": album, "label": label, "genres": genres,
                "release date": releasedate, "duration": duration, "play_offset": play_offset,
                "ms_until_over": ms_until_over, "acrID": acrID}
    else:
        return {"msg": "error", "score": 0}


def download_video(video_url):
    video_url = str(video_url)
    supported = 1
    if 'v.redd.it' in video_url:  # for videos uploaded to reddit
        url = video_url + "/DASH_audio.mp4"
        download_reddit(url)
    elif 'youtu.be' in video_url or 'youtube' in video_url:  # for youtube links
        url = video_url
        download_yt(url)
    elif 'twitch.tv' in video_url:  # for twitch links
        url = video_url
        download_twitchclip(url)
    else:  # for other links
        supported = 0
    return supported


def mstoMin(ms):
    """Convert milliseconds to 0:00 format"""
    import math
    d = float(int(ms) / 60000)
    ro = round(float((d - math.floor(d)) * 60))
    d = math.floor(d)
    if ro == 60:
        ro = str("00")
        d += 1
    if len(str(ro)) == 1:
        ro = "0" + str(ro)
    mn = str(d) + ":" + str(ro)
    return mn


def sectoMin(ms):
    """Convert seconds to 0:00 format"""
    import math
    d = float(int(ms) / 60)
    ro = round(float((d - math.floor(d)) * 60))
    d = math.floor(d)
    if ro == 60:
        ro = str("00")
        d += 1
    if len(str(ro)) == 1:
        ro = "0" + str(ro)
    mn = str(d) + ":" + str(ro)
    return mn


def timestamp_to_sec(time_str):
    """Get Seconds from time."""
    time_str = str(time_str)
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)


def download_reddit(link, file=output_file):
    """Pulls & downloads audio from reddit post"""
    import requests
    mp4 = requests.get(link)
    with open(file, 'wb') as f:
        for chunk in mp4.iter_content(chunk_size=255):
            if chunk:
                f.write(chunk)


def download_yt(link, file_name=output_file):
    """Downloads video from youtube links"""
    import os
    from pytube import YouTube
    mp4 = YouTube(link)
    try:
        os.remove(file_name)
    except:
        pass
    try:
        mp4.streams.filter(file_extension="mp4")
        of = mp4.streams.get_by_itag(18).download()
        os.rename(of, file_name)
    except:
        print(traceback.format_exc())


def download_twitchclip(url, output_path=output_file):
    """Download twitch clips"""
    import requests
    import urllib.request
    aut_params = {'client_id': config.Twitch.client_id, 'client_secret': config.Twitch.client_secret, 'grant_type': 'client_credentials'}
    data = requests.post(url='https://id.twitch.tv/oauth2/token', params=aut_params).json()
    token = data["access_token"]
    h = {"Client-ID": config.Twitch.client_id, 'client_secret': config.Twitch.client_secret, 'Authorization': "Bearer " + token}
    slug = str(url).split('/')[-1]
    clip_info = requests.get("https://api.twitch.tv/helix/clips?id=" + slug, headers=h).json()
    thumb_url = clip_info['data'][0]['thumbnail_url']
    mp4_url = thumb_url.split("-preview", 1)[0] + ".mp4"
    urllib.request.urlretrieve(mp4_url, output_path)


def clear_formatting(string):
    """Takes brackets, parentheses, stars out of strings"""
    word = ""
    for i in range(len(string)):
        if string[i] != "[" and string[i] != "]" and string[i] != "(" and string[i] != ")" and string[i] != "*":
            word += string[i]
    return word


def acr_create_link(title, artists, acrid):
    """Parse title, artists, acrid into link to song"""
    url = ""
    spl = []
    word = ""
    for i in range(
            len(str(artists))):  # put each word in the 'artists' into a list, and take out parentheses and brackets
        if str(artists)[i] != "[" and str(artists)[i] != "]" and str(artists)[i] != "(" and str(artists)[i] != ")" and str(artists)[i] != "*":
            if str(artists)[i] != " ":
                word += str(artists)[i]
            else:
                spl.append(word)
                word = ""
    for i in range(len(spl)):  # put underscores between words
        url += spl[i]
        if i != len(spl):
            url += "_"
    url += "-"

    spl = []
    word = ""
    for i in range(len(str(title))):  # do the same with 'title'
        if str(title)[i] != "[" and str(title)[i] != "]" and str(title)[i] != "(" and str(title)[i] != ")":
            if str(title)[i] != " ":
                word += str(title)[i]
            else:
                spl.append(word)
                word = ""

    for i in range(len(spl)):  # put underscores between words
        url += spl[i]
        if i != len(spl):
            url += "_"
    url += "-" + acrid
    return url


def get_youtube_link_time(url):
    """Get the seconds from youtube link's &t=hms format. Returns seconds and str formatted in h:m:s"""
    hours = ""
    minuts = ""
    secs = ""
    surl = str(url)
    if "t=" in surl or "time_continue=" in surl or "start=" in surl:
        at = 0
        i = len(surl)
        letter = ""
        while i > 0 and letter != "=":
            i -= 1
            letter = surl[i]
            if at == 's':
                try:
                    checkint = int(letter)
                    secs = surl[i] + secs
                except:
                    pass
            elif at == 'm':
                try:
                    checkint = int(letter)
                    minuts = surl[i] + minuts
                except:
                    pass
            elif at == 'h':
                try:
                    checkint = int(letter)
                    hours = surl[i] + hours
                except:
                    pass
            if i == len(surl) - 1:  # the second letter from the end == an int, meaning there isnt an 's'
                try:
                    checkint = int(letter)
                    at = 's'
                    secs = letter
                except:
                    pass
            if letter == 's':
                at = 's'
            elif letter == 'm':
                at = 'm'
            elif letter == 'h':
                at = 'h'
    if hours == "":
        hours = 0
    else:
        hours = int(hours)
    if minuts == "":
        minuts = 0
    else:
        minuts = int(minuts)
    if secs == "":
        secs = 0
    else:
        secs = int(secs)
    total_secs = hours * 3600 + minuts * 60 + secs
    time_str = sectoMin(total_secs)
    return total_secs, time_str


def parse_response(data, start_sec="", content=""):
    confidence = str(data['score'])
    if content == "youtube":
        if data == "error":
            re = "Looks like there's something wrong with the link you gave me."
        else:
            if str(data["msg"]) == "success":
                if int(confidence) == 100:
                    re = "[" + clear_formatting(str(data["title"])) + " by " + \
                         clear_formatting(str((data["artists"]))) + "](https://www.aha-music.com/" \
                         + acr_create_link(str(data["title"]), str(data["artists"]), str(data['acrID'])) + ") (" + \
                         str(mstoMin(int(data['play_offset']))) + "/" + str(mstoMin(int(data['duration']))) + ")\n\n"
                elif int(confidence) > 70:
                    re = "I think it's:\n[" + clear_formatting(str(data["title"])) + " by " + \
                         clear_formatting(str((data["artists"]))) + "](https://www.aha-music.com/" \
                         + acr_create_link(str(data["title"]), str(data["artists"]), str(data['acrID'])) + ") (" + \
                         str(mstoMin(int(data['play_offset']))) + "/" + str(mstoMin(int(data['duration']))) + ")\n\n"
                else:
                    re = "I'm not sure, but this might be it:\n[" + clear_formatting(str(data["title"])) + " by " + \
                         clear_formatting(str((data["artists"]))) + "](https://www.aha-music.com/" \
                         + acr_create_link(str(data["title"]), str(data["artists"]), str(data['acrID'])) + ") (" + \
                         str(mstoMin(int(data['play_offset']))) + "/" + str(mstoMin(int(data['duration']))) + ")\n\n"
            else:
                re = "No song was found"
            re += "\n\n*Looks like you gave me a youtube video to watch.\nI started this search at {}*".format(start_sec)
    elif start_sec == "":
        re = data
    else:
        if str(data["msg"]) == "success":
            if int(confidence) == 100:
                re = "[" + clear_formatting(str(data["title"])) + " by " + \
                     clear_formatting(str((data["artists"]))) + "](https://www.aha-music.com/" \
                     + acr_create_link(str(data["title"]), str(data["artists"]), str(data['acrID'])) + ") (" + \
                     str(mstoMin(int(data['play_offset']))) + "/" + str(mstoMin(int(data['duration']))) + ")\n\n"
            elif int(confidence) > 70:
                re = "I think it's:\n[" + clear_formatting(str(data["title"])) + " by " + \
                     clear_formatting(str((data["artists"]))) + "](https://www.aha-music.com/" \
                     + acr_create_link(str(data["title"]), str(data["artists"]), str(data['acrID'])) + ") (" + \
                     str(mstoMin(int(data['play_offset']))) + "/" + str(mstoMin(int(data['duration']))) + ")\n\n"
            else:
                re = "I'm not sure, but this might be it:\n[" + clear_formatting(str(data["title"])) + " by " + \
                     clear_formatting(str((data["artists"]))) + "](https://www.aha-music.com/" \
                     + acr_create_link(str(data["title"]), str(data["artists"]), str(data['acrID'])) + ") (" + \
                     str(mstoMin(int(data['play_offset']))) + "/" + str(mstoMin(int(data['duration']))) + ")\n\n"
        else:
            re = "No song was found"
        re += "\n\n*I started the search at {}, ".format(start_sec) + "you can provide a timestamp in hour:min:sec to tell me where to search.*"

    return re + config.Reddit.footer



