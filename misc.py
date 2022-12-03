from httpx import HTTPError
from selenium import webdriver
from selenium.webdriver.common.by import By
import config
import praw
import traceback
import time
import youtube_dl
import subprocess
from acrcloud.recognizer import ACRCloudRecognizer
import json
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from pytube import YouTube
import math
import requests
import urllib.request


output_file = "output.mp4"
cf = config.Reddit.main


class NoValidKey(Exception):
    pass


class TooManyACRReqs(Exception):
    pass


class NoKeyProvided(Exception):
    pass


class NoRateHandler(Exception):
    pass


class NoVideo(Exception):
    pass


class NoTimeStamp(Exception):
    pass


class TooManyReqs(Exception):
    pass


class Spotify:
    def __init__(self):
        self.scope = "user-library-read"
        self.client = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id= config.Spotify.id, client_secret=config.Spotify.sec))


class Chrome:
    def __int__(self):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument("--mute-audio")
        # self.options.add_argument("--no-startup-window")
        self.driver = webdriver.Chrome(config.webdriver,
                                       chrome_options=self.options)

    def start_driver(self):
        pass

    def click_on_location(self, x, y):
        from selenium.webdriver.common.action_chains import ActionChains
        elem = self.driver.find_element(By.XPATH, '/html')
        AC = ActionChains(self.driver)
        AC.move_to_element(elem).move_by_offset(x, y).click().perform()

    def search_download_recognize_youtube_video(self, song, artist, input_time):
        try:
            self.start_driver()
            self.driver.get('https://google.com/search?q=' + str(song) + ' by ' + str(artist) + ' youtube')
            i = 0
            while i == 20 or i == -1:
                try:
                    self.driver.find_element(By.XPATH, '/html/body/div[8]/div/div[8]/div/div[2]/div[3]/div[1]').click()
                    i = -1
                except:
                    pass
                i += 1
            try:
                elem = self.driver.find_element(By.LINK_TEXT, "Search for English results only")
                self.click_on_location(-200, -215)
            except:
                self.click_on_location(-200, -250)
            url = self.driver.current_url
            yt_file = download_yt(url)
            self.driver.quit()
            return identify_audio(yt_file, input_time), url
        except Exception as e:
            self.driver.quit()
            raise e


def authenticate():
    login = praw.Reddit(username=cf.user, password=cf.psw, user_agent=cf.agent, client_id=cf.client_id, client_secret=cf.client_secret)
    print(f"Logged in as {cf.user}")
    return login


def is_key_allowed(acr_keyname, ratehandler):
    if ratehandler.has_day_passed(time.time()):
        ratehandler.reset_key_reqs()
    if ratehandler.add_req_to_key(acr_keyname, 0) > 100:
        raise TooManyACRReqs
    return 1


def identify_audio(file=None, start_sec=0, end_sec=None, acr=None, delfile=False, ratehandler=None):
    """Requests data from ACRCloud and re-formats for manageability"""
    if ratehandler is None:
        raise NoRateHandler
    if end_sec is None:
        end_sec = start_sec + 30
    usedkey = None
    for key in ratehandler.KEYS:
        if is_key_allowed(key["key"], ratehandler):
            usedkey = key
            acr_key = key["key"]
            acr_secret = key["secret"]
            acr_host = key["host"]
            break
    if usedkey is None:
        raise NoValidKey
    login = {
        "access_key": acr_key,
        "access_secret": acr_secret,
        "host": acr_host
    }
    acr = ACRCloudRecognizer(login)
    try:
        sample_length = end_sec - start_sec
    except TypeError:
        sample_length = timestamptoSec(end_sec) - timestamptoSec(start_sec)

    try:
        data = json.loads(acr.recognize_by_file(file, start_sec, sample_length))
        if delfile:
            os.remove(file)  # delete the file since we don't need it anymore
    except:
        pass
    try:
        title, artists, score, duration, play_offset, acr_id = data["metadata"]["music"][0]["title"], data['metadata']['music'][0]['artists'][0]['name'], \
                                                               data['metadata']['music'][0]['score'], data["metadata"]["music"][0]["duration_ms"], \
                                                               data["metadata"]["music"][0]["play_offset_ms"], data["metadata"]["music"][0]["acrid"]
        ratehandler.add_req_to_key(acr_key)
        return {"msg": "success", "title": title, "artists": artists, "score": score, "play_offset": play_offset, "duration": duration, "acr_id": acr_id}
    except:
        return {"msg": "error", "score": 0}


def acr_create_link(title, artists, acrid):
    """Parse title, artists, acrid into link to song"""
    url = "https://aha-music.com/"
    spl = []
    word = ""
    for i in range(len(str(artists))):  # put each word in the 'artists' into a list, and take out parentheses and brackets
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


def find_link_youtube_spotify(acr_data, input_time):
    """Search spotify for song,
     if that fails then google the youtube video.
     Output link if either is successful"""
    correct_url = None
    input_song = str(acr_data["title"]).lower()
    input_artists = str(acr_data["artists"]).lower()
    chrome = Chrome()
    data, url = chrome.search_download_recognize_youtube_video(input_song, input_artists, input_time)
    if data['msg'] == "success" and str(data['title']).lower() == input_song and str(
            data['artists']).lower() == input_artists:
        # correct_url = url + "&t=" + str(math.floor(int(acr_data['play_offset']) / 1000) - input_time)  # add timestamp into youtube link, minus the amount of time the bot searched for
        correct_url = url + "&t=" + str(math.floor(int(acr_data['play_offset']) / 1000))
    if correct_url is None:
        spotify = Spotify()
        results = spotify.client.search(q='track:' + str(input_song))['tracks']['items']
        for r in results:
            name = str(r['name'])
            artist = str(r['artists'][0]['name'])
            url = str(r['external_urls']['spotify'])
            if name.lower() == input_song and artist.lower() == input_artists:
                correct_url = url
                break
    if correct_url is None:
        correct_url = acr_create_link(str(acr_data["title"]), str(acr_data["artists"]), str(acr_data['acr_id']))
    return correct_url


def find_link_spotify(acr_data, input_time):
    """Search spotify for song"""
    correct_url = None
    input_song = str(acr_data["title"]).lower()
    input_artists = str(acr_data["artists"]).lower()
    spotify = Spotify()
    results = spotify.client.search(q='track:' + str(input_song))['tracks']['items']
    for r in results:
        name = str(r['name'])
        artist = str(r['artists'][0]['name'])
        url = str(r['external_urls']['spotify'])
        if name.lower() == input_song and artist.lower() == input_artists:
            correct_url = url
            break
    if correct_url is None:
        correct_url = acr_create_link(str(acr_data["title"]), str(acr_data["artists"]), str(acr_data['acr_id']))
    return correct_url


def create_response(acr_data, context, user_url, start_sec, end_sec) -> str:
    if "https://youtu" in user_url and start_sec > 0:
        user_url += "&t=" + str(start_sec)
    if acr_data["msg"] == "success":
        title, artists, score, duration, play_offset = take_off_extra_chars(str(acr_data["title"])), take_off_extra_chars(str(acr_data["artists"])),\
                                                   str(acr_data['score']), str(mstoMin(int(acr_data['duration']))), str(mstoMin(int(acr_data['play_offset'])))
        if context == "autoreply":
            url = find_link_spotify(acr_data, start_sec)
        else:
            try:
                url = find_link_youtube_spotify(acr_data, start_sec)
            except:
                url = find_link_spotify(acr_data, start_sec)
        if int(score) == 100:
            response = "[" + title + " by " + artists + "](" + url + ") (" + play_offset + " / " + duration + ")"
        elif int(score) > 70:
            response = "I think it's:\n\n[" + title + " by " + artists + "](" + url + ") (" + play_offset + " / " + duration + ", confidence " + score + "%)"
        else:
            response = "I'm not sure, but it might be:\n\n[" + title + " by " + artists + "](" + url + ") (" + play_offset + " / " + duration + ", confidence " + score + "%)"
    else:
        response = "No song was found"
    start_sec, end_sec = sectoMin(start_sec), sectoMin(end_sec)
    if context == "link_parent":
        response += "\n\n*Looks like you wanted the song from your parent comment's [link](" + user_url + "). I searched from " + str(start_sec) + "-" + str(end_sec) + "*.\n\n*You can provide a timestamp to search somewhere else.*"
    elif context == "link_comment":
        response += "\n\n*Looks like you gave me a [a link](" + user_url + ") to watch. I searched from " + str(start_sec) + "-" + str(end_sec) + "*.\n\n*You can provide a timestamp to search somewhere else.*"
    elif context == "selftxt_link":
        response += "\n\n*Looks like you wanted the song from [a link](" + user_url + ") in the submission. I searched from " + str(start_sec) + "-" + str(end_sec) + "*.\n\n*You can provide a timestamp to search somewhere else.*"
    elif context == "video_submission":
        response += "\n\n*Looks like you wanted the song from [here](" + user_url + "). I searched from " + str(start_sec) + "-" + str(end_sec) + "*.\n\n*You can provide a timestamp to search somewhere else.*"
    else:
        response += "\n\n*I am a bot, and this action was performed automatically*"

    return response + cf.footer


def sectoMin(secs) -> str:
    """Convert seconds to 0:00 format"""
    secs = int(secs)
    if secs >= 3600:
        return time.strftime("%H:%M:%S", time.gmtime(secs))
    else:
        return time.strftime("%M:%S", time.gmtime(secs))


def mstoMin(ms) -> str:
    """Convert milliseconds to 0:00 format"""
    if ms >= 3600000:
        return time.strftime("%H:%M:%S", time.gmtime(ms / 1000))
    else:
        return time.strftime("%M:%S", time.gmtime(ms / 1000))


def timestamptoSec(time_str) -> int:
    """Get Seconds from time."""
    time_str = str(time_str)
    list = time_str.split(':')
    for item in list:
        try:
            inttest = int(item)
        except:
            raise NoTimeStamp
    if len(list) == 3:
        h, m, s = list
    elif len(list) == 2:
        m, s = list
        h = 0
    elif len(list) == 1:
        s = list[0]
        h, m = 0, 0
    else:
        h, m, s = 0, 0, 0
    return int(h) * 3600 + int(m) * 60 + int(s)


def get_yt_link_time(url) -> int:
    """Get the seconds from youtube link's &t=hms format. Returns seconds"""
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
    return hours * 3600 + minuts * 60 + secs


def clear_formatting(string) -> str:
    word = ""
    if "]" in string:
        skip_text = False
    else:
        skip_text = True
    for letter in string:
        if letter == "]":
            skip_text = True
        if letter != "[" and letter != "]" and letter != "(" and letter != ")" and skip_text:
            word += letter
    return word


def take_off_extra_chars(string):
    """Takes brackets, parentheses, stars out of strings"""
    word = ""
    for i in range(len(string)):
        if string[i] != "[" and string[i] != "]" and string[i] != "(" and string[i] != ")" and string[i] != "*":
            word += string[i]
    return word


def download_reddit(link, file=output_file):
    """Pulls & downloads audio from reddit post"""
    mp4 = requests.get(link)
    with open(file, 'wb') as f:
        for chunk in mp4.iter_content(chunk_size=255):
            if chunk:
                f.write(chunk)
    return file


def download_yt(link):
    """Downloads video from youtube links"""
    try:
        of = YouTube(link).streams.filter(file_extension="mp4").first().download()
    except HTTPError:
        raise TooManyReqs
    return of


def download_part_yt(link, start, to):
    """:param start 00:00:15
    :param to 00:00:25"""
    if start is None:
        start = "00:00:00"
    if to is None:
        to = "00:00:30"
    URL = link
    FROM = start
    TO = to
    TARGET = "demo.mp4"

    with youtube_dl.YoutubeDL({'format': 'best'}) as ydl:
        result = ydl.extract_info(URL, download=False)
        video = result['entries'][0] if 'entries' in result else result

    url = video['url']
    subprocess.call('ffmpeg -i "%s" -ss %s -t %s -c:v copy -c:a copy -y "%s"' % (url, FROM, TO, TARGET))
    return TARGET


def download_twitchclip(url, output_path=output_file):
    """Download twitch clips"""
    aut_params = {'client_id': config.Twitch.client_id, 'client_secret': config.Twitch.client_secret, 'grant_type': 'client_credentials'}
    data = requests.post(url='https://id.twitch.tv/oauth2/token', params=aut_params).json()
    token = data["access_token"]
    h = {"Client-ID": config.Twitch.client_id, 'client_secret': config.Twitch.client_secret, 'Authorization': "Bearer " + token}
    slug = str(url).split('/')[-1]
    if "medium=redt" in slug:
        slug = slug.split('?')[0]
    clip_info = requests.get("https://api.twitch.tv/helix/clips?id=" + slug, headers=h).json()
    thumb_url = clip_info['data'][0]['thumbnail_url']
    mp4_url = thumb_url.split("-preview", 1)[0] + ".mp4"
    urllib.request.urlretrieve(mp4_url, output_path)
    return output_path


def download_video(video_url, start=None, to=None):
    video_url = str(video_url)
    supported = 1
    if 'v.redd.it' in video_url:  # for videos uploaded to reddit
        url = video_url + "/DASH_audio.mp4"
        of = download_reddit(url)
    elif 'youtu.be' in video_url or 'youtube' in video_url:  # for youtube links
        url = video_url
        of = download_part_yt(url, start, to)
    elif 'twitch.tv' in video_url:  # for twitch links
        url = video_url
        of = download_twitchclip(url)
    else:  # for other links
        supported = 0
        of = 0
    return supported, of
