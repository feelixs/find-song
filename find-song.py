import praw
import time
import datetime
import traceback
import ast
import json
import requests
import urllib.request
import math
import config
import os
import multiprocessing
from pytube import YouTube
from acrcloud.recognizer import ACRCloudRecognizer


r = praw.Reddit(username='find-song', password=config.Reddit.psw, user_agent="songsearchv1", client_id=config.Reddit.client_id, client_secret=config.Reddit.client_secret)
COMMENTFILE = 'comments.txt'  # comments already replied to
PMFILE = 'rmPms.txt'  # removed comments whose author have already been pmd
MP4FILE = 'output.mp4'  # file holding audio pulled from reddit post (replaced with each request)


def mstoMin(ms):
    """Convert milliseconds to 0:00 format"""
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


def get_sec(time_str):
    """Get Seconds from time."""
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)


def download_reddit(link, file=MP4FILE):
    """Pulls & downloads audio from reddit post"""
    mp4 = requests.get(link)
    with open(file, 'wb') as f:
        for chunk in mp4.iter_content(chunk_size=255):
            if chunk:
                f.write(chunk)


def download_yt(link, file=MP4FILE):
    """Downloads audio from youtube links"""
    mp4 = YouTube(link)
    try:
        os.remove(MP4FILE)
    except:
        pass

    try:
        mp4.streams.filter(file_extension="mp4")
        of = mp4.streams.get_by_itag(18).download()
        os.rename(of, 'output.mp4')
    except:
        print(traceback.format_exc())


def download_twitchclip(url, output_path=MP4FILE):
    """Download twitch clips"""
    # first, we need a twitch oauth token to access clips
    aut_params = {'client_id': config.Twitch.client_id, 'client_secret': config.Twitch.client_secret,
                  'grant_type': 'client_credentials'}
    data = requests.post(url='https://id.twitch.tv/oauth2/token', params=aut_params).json()
    i = 0
    token = "error"
    while (token == "error") and (i < 5):
        i += 1
        try:
            token = data["access_token"]
        except:
            pass
    if i == 5:
        return "error"

    # now that we got an oauth for the twitch API, use it in the headers for the clip download request
    h = {"Client-ID": config.Twitch.client_id, 'client_secret': config.Twitch.client_secret, 'Authorization': "Bearer " + token}
    slug = str(url).split('/')[-1]
    clip_info = requests.get("https://api.twitch.tv/helix/clips?id=" + slug, headers=h).json()
    thumb_url = clip_info['data'][0]['thumbnail_url']
    mp4_url = thumb_url.split("-preview", 1)[0] + ".mp4"

    urllib.request.urlretrieve(mp4_url, output_path)
    return "success"


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
    for i in range(len(str(artists))): # put each word in the 'artists' into a list, and take out parentheses and brackets
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


def get_song(file, start_sec):
    """Requests data from ACRCloud and re-formats for manageability"""
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
    return {"msg": "success", "title": title, "artists": artists, "album": album, "label": label, "genres": genres,
            "release date": releasedate, "duration": duration, "play_offset": play_offset,
            "ms_until_over": ms_until_over, "acrID": acrID}


def parse_response(data, start_sec=""):
    if start_sec != "":
        if str(data["title"]) != "":
            re = "[" + clear_formatting(str(data["title"])) + " by " + \
                 clear_formatting(str((data["artists"]))) + "](https://www.aha-music.com/" \
                 + acr_create_link(str(data["title"]), str(data["artists"]), str(data['acrID'])) + ") (" + \
                 str(mstoMin(int(data['play_offset']))) + "/" + str(mstoMin(int(data['duration']))) + ")\n\n"
        else:
            re = "No song was found"

        re += "\n\n*I started the search at {}, you can provide a timestamp in hour:min:sec to tell me where to search.*".format(start_sec)
        # append to bottom of response, above footer
    else:
        re = data
    return re + config.Reddit.footer


def autoreply():  # auto-reply to comments in r/all
    while True:
        try:
            s = r.subreddit('all').comments()
            for c in s:
                if "what song is this" in str(c.body).lower() or "what's the song" in str(c.body).lower() or "what's this song" in str(c.body).lower() or "what is this song" in str(c.body).lower() or "what song is playing" in str(c.body).lower():
                    # positives include "what song is this", "what's the song", "what is this song", etc
                    supported = 1
                    if 'v.redd.it' in str(c.submission.url):  # for videos uploaded to reddit
                        url = str(c.submission.url) + "/DASH_audio.mp4"
                        download_reddit(url)
                    elif 'youtu.be' in str(c.submission.url):  # for youtube links
                        url = str(c.submission.url)
                        download_yt(url)
                    elif 'twitch.tv' in str(c.submission.url):  # for twitch links
                        url = str(c.submission.url)
                        download_twitchclip(url)
                    else:  # for other links
                        supported = 0

                    data = get_song(MP4FILE, get_sec('00:00:00'))

                    if supported == 1:
                        if str(data["title"]) != "":
                            re = "[**" + clear_formatting(str(data["title"])) + " by " + clear_formatting(
                                str(data["artists"])) + "**](https://www.aha-music.com/" + acr_create_link(
                                str(data["title"]), str(data["artists"]), str(data['acrID'])) + ") (" + str(
                                mstoMin(int(data['play_offset']))) + "/" + str(mstoMin(int(data['duration']))) + ")\n\n"

                        else:  # if I couldn't recognize the song, don't reply
                            re = "NORESULTS"
                        re += "\n\n*I am a bot, and this action was performed automatically.*"
                    else:
                        re = "NORESULTS"  # if video type isn't supported, don't reply

                    if "NORESULTS" not in str(re):
                        try:
                            c.reply(re + config.Reddit.footer)
                        except:
                            pass
        except:
            print(traceback.format_exc())


def mentions():
    while True:
        try:
            for msg in r.inbox.unread():
                if "u/find-song" in str(msg.body):
                    try:
                        start_sec = str(msg.body).split(" ")[1]
                    except:
                        start_sec = '00:00:00'

                    supported = 1
                    if 'v.redd.it' in str(msg.submission.url):  # for videos uploaded to reddit
                        url = str(msg.submission.url) + "/DASH_audio.mp4"
                        download_reddit(url)
                    elif 'youtu.be' in str(msg.submission.url):  # for youtube links
                        url = str(msg.submission.url)
                        download_yt(url)
                    elif 'twitch.tv' in str(msg.submission.url):  # for twitch links
                        url = str(msg.submission.url)
                        download_twitchclip(url)
                    else:  # for other links (vimeo, etc)
                        supported = 0

                    with open(COMMENTFILE, 'r+') as cf:
                        contents = cf.read()
                        if str(msg.id) in contents:  # have I already seen this comment?
                            spl = contents.split(';')
                            for i in range(len(spl)):
                                if str(spl[i]) == str(msg.id):
                                    data = ast.literal_eval(spl[i + 1])
                        else:                        # nope, I need to look up the audio
                            data = get_song(MP4FILE, get_sec(start_sec))
                            cf.write(str(msg.id) + ";" + str(data) + ";")
                    try:
                        if supported == 1:
                            msg.reply(parse_response(data, start_sec))
                        else:
                            msg.reply(parse_response("I don't currently support this video link type. Please check back later!"))
                        msg.mark_read()

                    except:
                       print(traceback.format_exc())

                else:
                    msg.mark_read()
        except:
            print(traceback.format_exc())

        time.sleep(60)


if __name__ == '__main__':
    autoreply_process = multiprocessing.Process(target=autoreply)  # auto-reply multiprocess
    mentions_process = multiprocessing.Process(target=mentions)  # mention reply multiprocess
    autoreply_process.start()
    mentions_process.start()
