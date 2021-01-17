import praw
import time
import datetime
import traceback
import ast
import json
import requests
import math
import config
import os
from pytube import YouTube
from acrcloud.recognizer import ACRCloudRecognizer

r = praw.Reddit(username='songsearchbot', password=config.Reddit.psw, user_agent="songsearchv1", client_id=config.Reddit.client_id, client_secret=config.Reddit.client_secret)
COMMENTFILE = 'comments.txt'  # comments already replied to
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


def downloadmp4(link, file=MP4FILE):
    """Pulls & downloads audio from reddit post"""
    mp4 = requests.get(link)
    with open(file, 'wb') as f:
        for chunk in mp4.iter_content(chunk_size=255):
            if chunk:
                f.write(chunk)


def downloadytmp4(link, file=MP4FILE):
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


def acr_create_link(title, artists, acrid):
    """Parse title, artists, ACR-ID into link to song"""
    url = ""
    spl = str(artists).split(" ")
    for i in range(len(spl)):
        url += spl[i]
        if i != len(spl):
            url += "_"
    url += "-"
    spl = str(title).split(" ")
    for i in range(len(spl)):
        url += spl[i]
        if i != len(spl):
            url += "_"
    url += "-" + acrid
    return url


def get_song(file, start_sec):
    login = {
        "access_key": config.ACR.key,
        "access_secret": config.ACR.secret,
        "host": "identify-us-west-2.acrcloud.com"
    }

    acr = ACRCloudRecognizer(login)
    j = json.loads(acr.recognize_by_file(file, start_sec))
    try:
        try:
            artists = j['metadata']['music'][0]['artists'][0]['name']
        except:
            artists = ""
        try:
            genres = j["metadata"]["music"][0]["genres"][0]["name"]
        except:
            genres = ""
        try:
            album = j["metadata"]["music"][0]["album"]["name"]
        except:
            album = ""
        try:
            title = j["metadata"]["music"][0]["title"]
        except:
            title = ""
        try:
            releasedate = j["metadata"]["music"][0]["release_date"]
        except:
            releasedate = ""
        try:
            label = j["metadata"]["music"][0]["label"]
        except:
            label = ""
        try:
            duration = j["metadata"]["music"][0]["duration_ms"]
        except:
            duration = 0
        try:
            play_offset = j["metadata"]["music"][0]["play_offset_ms"]
        except:
            play_offset = 0
        try:
            acrID = j["metadata"]["music"][0]["acrid"]
        except:
            acrID = ""

        ms_until_over = int(duration) - int(play_offset)
        return {"msg": "success", "title": title, "artists": artists, "album": album, "label": label, "genres": genres,
                "release date": releasedate, "duration": duration, "play_offset": play_offset,
                "ms_until_over": ms_until_over, "acrID": acrID}
    except:
        return j["status"]


def main():
    for msg in r.inbox.unread():
        if "u/songsearchbot" in str(msg.body):
            try:
                start_sec = get_sec(str(msg.body).split(" ")[1])
            except:
                start_sec = 0

            if 'v.redd.it' in str(msg.submission.url):
                url = str(msg.submission.url) + "/DASH_audio.mp4"
                downloadmp4(url)
            else:
                url = str(msg.submission.url)
                downloadytmp4(url)

            with open(COMMENTFILE, 'r+') as cf:
                contents = cf.read()
                if str(msg.id) in contents:  # if it already saw this comment but errored out when trying to reply, get info from file
                    spl = contents.split(';')
                    for i in range(len(spl)):
                        if str(spl[i]) == str(msg.id):
                            data = ast.literal_eval(spl[i+1])
                else:   # if it never saw the comment before, lookup song
                    data = get_song(MP4FILE, start_sec)
                    cf.write(str(msg.id) + ";" + str(data) + ";")

            if str(data["title"]) != "":
                re = "[" + str(data["title"]) + " by " + str(data["artists"]) + "](https://www.aha-music.com/" + acr_create_link(str(data["title"]), str(data["artists"]), str(data['acrID'])) + ") (" + str(mstoMin(int(data['play_offset']))) + "/" + str(mstoMin(int(data['duration']))) + ")"
            else:
                re = "No song was found"

            try:
                msg.reply(re + config.Reddit.footer)
                msg.mark_read()

            except:
                with open(ERRORFILE, 'a') as ef:
                    ef.write(str(datetime.datetime.now()) + ": Error replying:\n" + str(traceback.format_exc())+ "\n\n")

        else:
            msg.mark_read()


if __name__ == '__main__':

    while True:
        try:
            main()
        except:
            with open(ERRORFILE, 'a') as ef:
                ef.write(str(datetime.datetime.now()) + ": Error in main:\n" + str(traceback.format_exc()) + "\n\n")
        time.sleep(60)
