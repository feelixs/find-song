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
from pytube import YouTube
from acrcloud.recognizer import ACRCloudRecognizer
from selenium import webdriver

driver = webdriver.Chrome(config.selenium_driver_path)

r = praw.Reddit(username='find-song', password=config.Reddit.psw, user_agent="songsearchv1", client_id=config.Reddit.client_id, client_secret=config.Reddit.client_secret)
COMMENTFILE = 'comments.txt'  # comments already replied to
PMFILE = 'rmPms.txt'  # removed comments whose author have already been pmd
MP4FILE = 'output.mp4'  # file holding audio pulled from reddit post (replaced with each request)
ERRORFILE = 'errors.txt'  # log errors to file

with open(ERRORFILE, 'w') as f:  # clear errorfile on each run
    f.close()


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
        print('no ' + str(MP4FILE))

    try:
        mp4.streams.filter(file_extension="mp4")
        of = mp4.streams.get_by_itag(18).download()
        os.rename(of, 'output.mp4')
    except:
        with open(ERRORFILE, 'a') as ef:
            ef.write(str(datetime.datetime.now()) + ": Error in downloadyt:\n" + str(traceback.format_exc()) + "\n\n")


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

def is_removed(comment):
    driver.get("https://reddit.com" + str(comment.permalink))
    time.sleep(2)
    li = (driver.find_elements_by_link_text('View all comments'))
    if len(li) == 2:
        return True
    else:
        return False
# As it's not possible to see if a comment was removed as spam with praw, the bot looks at its
# comments with selenium, and lists the number of times a link with text 'View all comments' appears.
# If there are two links with the text, it was linked to a removed comment


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


start_epoch = time.time()


def main():
    for c in r.redditor('find-song').comments.new():  # have any of my new comments been removed?
        global start_epoch
        if c.created_utc <= start_epoch:  # don't continue if the comment was from before start_epoch
            break
        start_epoch = c.created_utc
        if is_removed(c):
            with open(PMFILE, 'r+') as f:
                txt = f.read()
                if str(c.id) not in txt:
                    try:
                        if c.parent().author is not None:
                            r.redditor(str(c.parent().author)).message("My reply was removed, here's a PM instead", str(c.body))
                        f.write(str(c.id) + ";")
                    except:
                        with open(ERRORFILE, 'a') as ef:
                            ef.write(str(datetime.datetime.now()) + ": Error PMing:\n" + str(traceback.format_exc()) + "\n\n")

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
                print(download_twitchclip(url))
            else:  # for other links (vimeo, etc)
                supported = 0

            with open(COMMENTFILE, 'r+') as cf:
                contents = cf.read()
                if str(msg.id) in contents:  # have I already seen this comment?
                    spl = contents.split(';')
                    for i in range(len(spl)):
                        if str(spl[i]) == str(msg.id):
                            data = ast.literal_eval(spl[i + 1])  # ast.literal_eval = convert str to dict
                else:  # nope, I need to look up the audio
                    data = get_song(MP4FILE, get_sec(start_sec))
                    cf.write(str(msg.id) + ";" + str(data) + ";")
            try:
                if supported == 1:
                    msg.reply(parse_response(data, start_sec))
                else:
                    msg.reply(parse_response("I don't currently support this video link type. Please check back later!"))
                msg.mark_read()

            except:
                with open(ERRORFILE, 'a') as ef:
                    ef.write(str(datetime.datetime.now()) + ": Error replying:\n" + str(traceback.format_exc()) + "\n\n")

        else:
            msg.mark_read()


if __name__ == '__main__':
    """Run main() once each minute forever"""
    while True:
        try:
            main()
        except:
            with open(ERRORFILE, 'a') as ef:
                ef.write(str(datetime.datetime.now()) + ": Error in main:\n" + str(traceback.format_exc()) + "\n\n")
        time.sleep(60)
