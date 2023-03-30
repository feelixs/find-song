import subprocess
import pytube.exceptions
from httpx import HTTPError
from selenium import webdriver
from selenium.webdriver.common.by import By
import config
import praw
import traceback
import time
from bs4 import BeautifulSoup
import autoit
import os
from acrcloud.recognizer import ACRCloudRecognizer
import json
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from pytube import YouTube
import math
import re
from TikTokAPI import TikTokAPI
import unicodedata
import requests
import urllib.request


output_file = "output.mp4"
cf = config.Reddit.main
DL_FOLDER = config.DL_PATH  # path to downloads folder, used to retrieve downloads from google drive etc.


class Spotify:
    def __init__(self):
        self.scope = "user-library-read"
        self.client = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=config.Spotify.id,
                                                                                          client_secret=config.Spotify.sec))


def queue_del_file(filepath, how_long_to_wait):
    with open("delfiles.txt", 'a') as f:
        f.write(str(filepath) + "\n")


class Chrome:
    def __int__(self):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument("--mute-audio")
        self.driver = webdriver.Chrome(config.webdriver,
                                       chrome_options=self.options)

    def open_url(self, url):
        self.driver.get(url)

    def current_url(self):
        return self.driver.current_url

    def quit(self):
        self.driver.quit()

    def start_driver(self):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument("--mute-audio")
        self.driver = webdriver.Chrome(config.webdriver,
                                       chrome_options=self.options)

    def click_on_location(self, x, y):
        from selenium.webdriver.common.action_chains import ActionChains
        elem = self.driver.find_element(By.XPATH, '/html')
        AC = ActionChains(self.driver)
        AC.move_to_element(elem).move_by_offset(x, y).click().perform()

    def search_download_recognize_youtube_video(self, song, artist, input_time):
        try:
            self.start_driver()
            self.driver.get('https://google.com/search?q=' + str(song) + ' by ' + str(artist) + ' youtube')
            self.click_on_location(-200, -215)
            self.click_on_location(200, -100)
            time.sleep(1)
            url = self.driver.current_url
            self.driver.quit()
            return url
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
        return False
    return True


def identify_audio(file=None, start_sec=0, end_sec=None, acr=None, delfile=False, ratehandler=None):
    """Requests data from ACRCloud and re-formats for manageability"""
    if ratehandler is None:
        raise errs.NoRateHandler
    if end_sec is None:
        end_sec = start_sec + 10
    usedkey = None
    for key in ratehandler.KEYS:
        if is_key_allowed(key["key"], ratehandler):
            usedkey = key
            acr_key = key["key"]
            acr_secret = key["secret"]
            acr_host = key["host"]
            break
    if usedkey is None:
        raise errs.NoValidKey
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
        if data['status']['code'] == 3003:  # api says limit reached
            ratehandler.add_req_to_key(usedkey['key'], 100)  # locally invalidate key
            return identify_audio(file, start_sec, end_sec, acr, delfile, ratehandler)  # recall
        if data['status']['code'] == 2004:  # decode audio error
            return {"msg": "error", "score": 0}
        if delfile:
            os.remove(file)  # delete the file since we don't need it anymore
    except:
        pass
    try:
        title, artists, score, duration, play_offset, acr_id = data["metadata"]["music"][0]["title"], \
            data['metadata']['music'][0]['artists'][0]['name'], \
            data['metadata']['music'][0]['score'], data["metadata"]["music"][0]["duration_ms"], \
            data["metadata"]["music"][0]["play_offset_ms"], data["metadata"]["music"][0]["acrid"]
        ratehandler.add_req_to_key(acr_key)
        return {"msg": "success", "title": title, "artists": artists, "score": score, "play_offset": play_offset,
                "duration": duration, "acr_id": acr_id, "etc": data}
    except:
        return {"msg": "error", "score": 0}


def acr_create_link(title, artists, acrid):
    """Parse title, artists, acrid into link to song"""
    url = "https://aha-music.com/"
    spl = []
    word = ""
    for i in range(
            len(str(artists))):  # put each word in the 'artists' into a list, and take out parentheses and brackets
        if str(artists)[i] != "[" and str(artists)[i] != "]" and str(artists)[i] != "(" and str(artists)[i] != ")" and \
                str(artists)[i] != "*":
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
    spotify = Spotify()
    results = spotify.client.search(q='track:' + str(input_song))['tracks']['items']
    if not results:  # no results on spotify, search on google
        url = chrome.search_download_recognize_youtube_video(input_song, input_artists, input_time)
        if "google.com" not in url:
            return url + "&t=" + str(math.floor(int(acr_data['play_offset']) / 1000))
        else:
            return acr_create_link(str(acr_data["title"]), str(acr_data["artists"]), str(acr_data['acr_id']))

    return find_link_spotify_acr(acr_data)


def find_link_spotify_acr(acr_data):
    """Search spotify for song"""

    try:
        spotify = Spotify()
        try:
            isrc = acr_data['etc']['metadata']['music'][0]['external_ids']['isrc']
        except:
            isrc = None
        try:
            upc = acr_data['etc']['metadata']['music'][0]['external_ids']['upc']
        except:
            upc = None
        if isrc is not None:
            results = spotify.client.search(q=f"isrc: {isrc}")
        elif upc is not None:
            results = spotify.client.search(q=f"upc: {upc}")
        else:
            results = spotify.client.search(q=f"artists: {acr_data['artists']} track: {acr_data['title']}")
        try:
            r = results['tracks']['items'][0]
        except:
            r = []
    except:
        r = []
    if r:
        return results['tracks']['items'][0]['external_urls']['spotify']
    else:
        return acr_create_link(str(acr_data["title"]), str(acr_data["artists"]), str(acr_data['acr_id']))


def spotify_isrc2url(search):
    """Search spotify for song"""
    spotify = Spotify()
    try:
        results = spotify.client.search(q=f"isrc: {search}")['tracks']['items']
    except:
        results = []
    if results:
        return results[0]['external_urls']['spotify']
    else:
        raise errs.NoResults


def spotify_isrc2img(search):
    """Search spotify for song"""
    spotify = Spotify()
    try:
        results = spotify.client.search(q=f"isrc: {search}")['tracks']['items']
    except:
        results = []
    if results:
        r = results[0]
    else:
        raise errs.NoResults
    for i in r['album']['images']:
        if i['height'] < 640:
            return i['url']


def is_single_timestamp(msg: praw.Reddit.comment):
    """Returns true if the comment contains ONLY a timestamp and no other text
    valid timestamps:
        0:01
        0:0:01
        0:01-0:11
        0:0:01-0:0:11
    this is used for checking if the bot should reply to a comment that doesn't contain its username"""
    if not msg.was_comment:
        return False
    else:
        b = msg.body
        if "-" in b:
            b = b.replace(" ", "-").split("-")
            if len(b) != 2:
                return False
        else:
            b = b.split(" ")
            if len(b) > 1:
                return False
        isint = False
        for word in b:
            isint = False
            if ":" in word:
                try:
                    min, sec = word.split(":")
                    min, sec = int(min), int(sec)
                    isint = True
                except:
                    try:
                        hour, min, sec = word.split(":")
                        hour, min, sec = int(hour), int(min), int(sec)
                        isint = True
                    except:
                        continue
            else:
                return False
        if isint:
            return True
        else:
            return False


def acr_get_shareable_links(acr_url: str, timeout: int = 60, spotify: bool = False) -> dict:
    c = Chrome()
    c.start_driver()
    c.open_url(acr_url)
    i = 0
    loaded = None
    while loaded is None and i < timeout:
        i += 1
        try:
            loaded = c.driver.find_element(By.TAG_NAME, "img")
        except:
            time.sleep(1)
    if loaded is None:
        raise errs.LinkTimeout
    # don't try getting apple or spotify links because if they existed we're assuming we would have already found them
    # and images on this site are inconsistent, so we're not getting one of those either
    try:
        youtubvid = c.driver.find_element(By.XPATH, "//a[contains(@href, 'https://youtu')]").get_attribute("href")
    except:
        try:
            youtubvid = c.driver.find_element(By.XPATH, "//a[contains(@href, 'https://www.youtu')]").get_attribute(
                "href")
        except:
            youtubvid = None
    try:
        ymuisc = c.driver.find_element(By.XPATH, "//a[contains(@href, 'https://music.youtu')]").get_attribute("href")
    except:
        ymuisc = None
    try:
        soundcl = c.driver.find_element(By.XPATH, "//a[contains(@href, 'soundcloud.com')]").get_attribute("href")
    except:
        soundcl = None
    try:
        deez = c.driver.find_element(By.XPATH, "//a[contains(@href, 'deezer.com')]").get_attribute("href")
    except:
        deez = None
    try:
        audiomacj = c.driver.find_element(By.XPATH, "//a[contains(@href, 'audiomack.com')]").get_attribute("href")
    except:
        audiomacj = None
    try:
        tide = c.driver.find_element(By.XPATH, "//a[contains(@href, 'tidal.com')]").get_attribute("href")
    except:
        tide = None
    try:
        gna = c.driver.find_element(By.XPATH, "//a[contains(@href, 'gaana.com')]").get_attribute("href")
    except:
        gna = None
    try:
        brainz = c.driver.find_element(By.XPATH, "//a[contains(@href, 'musicbrainz.org')]").get_attribute("href")
    except:
        brainz = None
    try:
        if spotify:
            applem = c.driver.find_element(By.XPATH, "//a[contains(@href, 'music.apple')]").get_attribute("href")
        else:
            applem = None
    except:
        applem = None
    try:
        if spotify:
            spotify_link = c.driver.find_element(By.XPATH, "//a[contains(@href, 'open.spotify.com/track')]").get_attribute("href")
        else:
            spotify_link = None
    except:
        spotify_link = None
    return {"img": None, "apple": applem, "spotify": spotify_link, "youtube": youtubvid, "soundcloud": soundcl,
            "deezer": deez,
            "audiomack": audiomacj, "youtube_music": ymuisc, "tidal": tide, "gaana": gna, "musicbrainz": brainz}


def songwhip_get_shareable_links(url: str, timeout: int = 60) -> dict:
    c = Chrome()
    c.start_driver()
    uuu = f"https://songwhip.com/convert?url={url}&sourceAction=pasteUrl"
    c.open_url(uuu)
    i = 0
    img = None
    while img is None and i < timeout:
        i += 1
        try:
            img = c.driver.find_element(By.XPATH, "//img[contains(@src, 'songwhip.com/cdn-cgi/image')]").get_attribute(
                "src")
        except:
            time.sleep(1)
    if img is None:
        raise errs.LinkTimeout
    try:
        applem = c.driver.find_element(By.XPATH, "//a[contains(@href, 'music.apple')]").get_attribute("href")
    except:
        applem = None
    try:
        spotify = c.driver.find_element(By.XPATH, "//a[contains(@href, 'open.spotify.com/track')]").get_attribute(
            "href")
    except:
        spotify = None
    try:
        youtubvid = c.driver.find_element(By.XPATH, "//a[contains(@href, 'https://youtu')]").get_attribute("href")
    except:
        try:
            youtubvid = c.driver.find_element(By.XPATH, "//a[contains(@href, 'https://www.youtu')]").get_attribute(
                "href")
        except:
            youtubvid = None
    try:
        ymuisc = c.driver.find_element(By.XPATH, "//a[contains(@href, 'https://music.youtu')]").get_attribute("href")
    except:
        ymuisc = None
    try:
        soundcl = c.driver.find_element(By.XPATH, "//a[contains(@href, 'soundcloud.com')]").get_attribute("href")
    except:
        soundcl = None
    try:
        deez = c.driver.find_element(By.XPATH, "//a[contains(@href, 'deezer.com')]").get_attribute("href")
    except:
        deez = None
    try:
        audiomacj = c.driver.find_element(By.XPATH, "//a[contains(@href, 'audiomack.com')]").get_attribute("href")
    except:
        audiomacj = None
    try:
        tide = c.driver.find_element(By.XPATH, "//a[contains(@href, 'tidal.com')]").get_attribute("href")
    except:
        tide = None
    try:
        gna = c.driver.find_element(By.XPATH, "//a[contains(@href, 'gaana.com')]").get_attribute("href")
    except:
        gna = None
    try:
        brainz = c.driver.find_element(By.XPATH, "//a[contains(@href, 'musicbrainz.org')]").get_attribute("href")
    except:
        brainz = None
    return {"img": img, "apple": applem, "spotify": spotify, "youtube": youtubvid, "soundcloud": soundcl,
            "deezer": deez,
            "audiomack": audiomacj, "youtube_music": ymuisc, "tidal": tide, "gaana": gna, "musicbrainz": brainz}


def create_response(acr_data, context, user_url, start_sec, end_sec, reply_to=None) -> praw.Reddit.comment:  # or str
    media_url = None
    if "https://youtu" in user_url and start_sec > 0:
        user_url += "&t=" + str(start_sec)
    if acr_data["msg"] == "success":
        title, artists, score, duration, play_offset = take_off_extra_chars(
            str(acr_data["title"])), take_off_extra_chars(str(acr_data["artists"])), \
            str(acr_data['score']), str(mstoMin(int(acr_data['duration']))), str(mstoMin(int(acr_data['play_offset'])))

        media_url = find_link_spotify_acr(acr_data)
        if media_url is not None:
            if "open.spotify" in media_url:  # this would also work with other platforms aka "music.apple"
                url = f"https://songwhip.com/convert?url={media_url}&sourceAction=pasteUrl"
            elif "aha-music.com" in media_url:
                url = media_url
        if int(score) == 100:
            response = "[" + title + " by " + artists + "](" + url + ") (" + play_offset + " / " + duration + ")"
        elif int(score) > 70:
            response = "I think it's:\n\n[" + title + " by " + artists + "](" + url + ") (" + play_offset + " / " + duration + ", confidence " + score + "%)"
        else:
            response = "I'm not sure, but it might be:\n\n[" + title + " by " + artists + "](" + url + ") (" + play_offset + " / " + duration + ", confidence " + score + "%)"
    elif acr_data['msg'] == "decode-err":
        response = f"I couldn't read the audio from [this link]({user_url})"
    elif acr_data['msg'] == "invalid":
        response = "There was an error with the provided link."
    elif acr_data['msg'] == "toolong":
        response = "The provided YouTube video was too long for me to download."
    else:
        response = "No song was found"
    start_sec, end_sec = sectoMin(start_sec), sectoMin(end_sec)
    if context == "link_parent":
        response += "\n\n*Looks like you wanted the song from your parent comment's [link](" + user_url + "). I searched from " + str(
            start_sec) + "-" + str(end_sec) + "*.\n\n*You can provide a timestamp to search somewhere else.*"
    elif context == "link_comment":
        response += "\n\n*Looks like you gave me a [link](" + user_url + ") to watch. I searched from " + str(start_sec) + "-" + str(
            end_sec) + "*.\n\n*You can provide a [timestamp](https://song-find.web.app/index.html#timestamps) to search somewhere else.*"
    elif context == "selftxt_link":
        response += "\n\n*Looks like you wanted the song from a [link](" + user_url + ") in the submission. I searched from " + str(
            start_sec) + "-" + str(
            end_sec) + "*.\n\n*You can provide a [timestamp](https://song-find.web.app/index.html#timestamps) to search somewhere else.*"
    elif context == "video_submission":
        response += "\n\n*Looks like you wanted the song from [here](" + user_url + "). I searched from " + str(start_sec) + "-" + str(
            end_sec) + "*.\n\n*You can provide a [timestamp](https://song-find.web.app/index.html#timestamps) to search somewhere else.*"
    else:
        response += "\n\n*I am a bot, and this action was performed automatically*"

    if reply_to is not None:
        re = reply_to.reply(response + cf.footer)
    else:
        # for pms
        re = response + cf.footer
    return re


def save_request(jsn):
    try:
        with open("identified.txt", "a") as f:
            f.write(json.dumps(jsn) + "\n")
    except:
        pass


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
    time_str = str(time_str).replace(".", "").replace(",", "").replace(")", "").replace("(", "")
    list = time_str.split(':')
    for item in list:
        try:
            inttest = int(item)
        except:
            raise errs.NoTimeStamp
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
    string = string.replace("*", "")
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
    while word[-1] == ".":
        # remove any trailing periods
        word = word[:-1]
    return word


def take_off_extra_chars(string):
    """Takes brackets, parentheses, stars out of strings"""
    word = ""
    for i in range(len(string)):
        if string[i] != "[" and string[i] != "]" and string[i] != "(" and string[i] != ")" and string[i] != "*":
            word += string[i]
    return word


def download_streamable(url):
    try:
        toolpath = config.STREAMABLE_DL_PATH  # path to the folder containing streamable_dl tool
        files_in = []
        if "/amp_player" in url:
            url = url.replace("/amp_player", "")
        for file in os.listdir(os.path.curdir):
            files_in.append(file)
        p = subprocess.Popen(f"python \"{toolpath}\" \"{url}\"")
        p.communicate()
        fname = url.split("/")[-1] + ".mp4"  # if the file alr exists if won't be detected
        if os.path.isfile(fname):
            return fname
        time.sleep(3)
        for file in os.listdir(os.path.curdir):
            if file not in files_in:
                return file
        return fname
    except:
        raise InvalidLink


def download_twitter(url):
    pass


def download_discord(url):
    try:
        fname = os.path.join(DL_FOLDER, url.split('/')[-1])
        if os.path.isfile(fname):
            return fname
        c = Chrome()
        c.start_driver()
        c.open_url(url)
        time.sleep(3)
        if fname.split('.')[-1] == "mov":
            queue_del_file(fname, 600)
            return convert_mov(fname, "FFmeg_output.mp4")
        return fname
    except:
        raise InvalidLink


def convert_mov(fname, outpath, ffmpeg_path=None):
    if ffmpeg_path is None:
        ffmpeg_path = config.FFMPEG_PATH
    cmd = f"{ffmpeg_path} -i \"{fname}\" -qscale 0 \"{outpath}\""
    p = subprocess.Popen(cmd)
    p.communicate()
    return fname


def download_sndup(link, timeout=10):
    import selenium.webdriver.common.action_chains as ac
    try:
        files_in_downloads = []
        for file in os.listdir(DL_FOLDER):
            files_in_downloads.append(file)
        dr = webdriver.Chrome(config.webdriver)
        dr.get(link)
        clikable = False
        tries = 0
        MAX_TRIES = 10
        while not clikable and tries < MAX_TRIES:
            tries += 1
            try:
                d = dr.find_element(By.PARTIAL_LINK_TEXT, "Download audio")
                clikable = True
            except:
                time.sleep(1)
        if tries == MAX_TRIES:
            raise errs.LinkTimeout
        actions = ac.ActionChains(dr)
        actions.move_to_element(d).perform()
        actions.click().perform()
        time.sleep(1)
        actions.click().perform()
        clikable = False
        tries = 0
        MAX_TRIES = 10
        while not clikable and tries < MAX_TRIES:
            tries += 1
            try:
                d = dr.find_element(By.XPATH, "//video")
                clikable = True
            except:
                time.sleep(1)
        if tries == MAX_TRIES:
            raise errs.LinkTimeout
        time.sleep(0.5)
        autoit.run(os.path.join(os.path.curdir, "cntrl-s.exe"))
        time.sleep(1)
        autoit.run(os.path.join(os.path.curdir, "enter.exe"))
        i = 0
        while i < timeout:
            for file in os.listdir(DL_FOLDER):
                if file not in files_in_downloads and file.split(".")[-1] != "tmp" and file.split(".")[-1] != "crdownload":
                    if file.split('.')[-1] == "mov":
                        queue_del_file(os.path.join(DL_FOLDER, file), 600)
                        return convert_mov(os.path.join(DL_FOLDER, file), "FFmeg_output.mp4")
                    time.sleep(1)
                    return os.path.join(DL_FOLDER, file)
            time.sleep(1)
            i += 1
        raise errs.LinkTimeout
    except:
        raise InvalidLink


def download_google(url, timeout=10):
    try:
        file_id = url.split("/")[-2]
        download_link = f"https://drive.google.com/uc?export=download&id={file_id}"
        # find filename
        files_in_downloads = []
        for file in os.listdir(DL_FOLDER):
            files_in_downloads.append(file)
        c = Chrome()
        c.start_driver()
        c.open_url(download_link)
        i = 0
        while i < timeout:
            for file in os.listdir(DL_FOLDER):
                if file not in files_in_downloads and file.split(".")[-1] != "tmp" and file.split(".")[-1] != "crdownload":
                    if file.split('.')[-1] == "mov":
                        queue_del_file(os.path.join(DL_FOLDER, file), 600)
                        return convert_mov(os.path.join(DL_FOLDER, file), "FFmeg_output.mp4")
                    time.sleep(1)
                    return os.path.join(DL_FOLDER, file)
            time.sleep(1)
            i += 1
        raise errs.LinkTimeout
    except:
        raise InvalidLink


def download_reddit(link, file=output_file):
    """Pulls & downloads audio from reddit post"""
    try:
        if "/DASH_audio.mp4" not in link:
            link = link + "/DASH_audio.mp4"
        mp4 = requests.get(link)
        file = slugify(link) + ".mp4"
        with open(file, 'wb') as f:
            for chunk in mp4.iter_content(chunk_size=255):
                if chunk:
                    f.write(chunk)
        return file
    except:
        raise InvalidLink


def download_yt(link):
    """Downloads video from youtube links"""
    link = link.replace("\\", "")
    try:
        # overwrites files with same name
        of = YouTube(link)
        try:
            vidlen = of.length
        except:
            vidlen = 0
        if vidlen / 3600 < 4:  # 4 hours
            of = of.streams.filter(file_extension="mp4").first().download(filename=slugify(link) + ".mp4")
        else:
            raise errs.VidTooLong
    except HTTPError:
        raise errs.TooManyReqs
    except:
        raise InvalidLink
    return of


def click_pull_git():
    # click refresh and pull
    try:
        autoit.win_activate("GitHub Desktop")
    except:
        pass
    time.sleep(1)
    autoit.mouse_click(x=652, y=145)
    time.sleep(5)
    autoit.mouse_click(x=652, y=145)


def get_voc_id(link) -> str:
    id = None
    try:
        i = link.split("/")
        id = i[-1]
        if id == "":
            id = i[-2]
    except:
        raise InvalidLink
    return id


def download_vocaroo(link):
    try:
        ID = get_voc_id(link)
        file = os.path.join(DL_FOLDER, f"Vocaroo {ID}.mp3")
        if os.path.isfile(file):
            return file
        dr = webdriver.Chrome(config.webdriver)
        dr.get(link)
        clikable = False
        tries = 0
        MAX_TRIES = 10
        while not clikable and tries < MAX_TRIES:
            tries += 1
            try:
                d = dr.find_element(By.XPATH, "/html/body/div/div[2]/div[2]/div[2]/div/div[2]/div[3]/a/div[1]")
                clikable = True
            except:
                time.sleep(1)
        if tries == MAX_TRIES:
            raise errs.LinkTimeout
        d.click()
        time.sleep(2)
        return file
    except:
        raise InvalidLink


def download_soundcloud(link=None, save_as="output"):
    pass


def parse_tiktok_link(link: str) -> int:
    """when given a tiktok link, returns its ID"""
    vidid = None
    try:
        if "/t/" in link:
            vidid = link.split("/")[4]
        elif "vm.tiktok" in link:
            C = Chrome()
            C.start_driver()
            C.open_url(link)
            i = 0
            while C.current_url() == link or i == 10:  # 10 sec = timeout
                time.sleep(1)
                i += 1
            vidid = C.current_url().split("/")[5]
        else:
            vidid = link.split("/")[5]
    except:
        raise InvalidLink
    try:
        # if there's a ? after the id
        vidid = vidid.split("?")[0]
    except:
        pass
    return int(vidid)


def ord_str(string):
    out = ""
    for l in string:
        out += str(ord(l))
    return '{:x}'.format(int(out))


def slugify(inp, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(inp)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    r = re.sub(r'[-\s]+', '-', value).strip('-_')
    if r == "":
        r = ord_str(inp)
    return r


def create_valid_file(filaname):
    fileexists = True
    fname, ext = filaname.split(".")[0], "." + filaname.split(".")[1]
    use_fname = fname
    e = 0
    while fileexists:
        e += 1
        use_fname = fname + f"-{e}"
        use_fname = slugify(use_fname)
        fileexists = os.path.isfile(f"{use_fname}{ext}")
    return use_fname + ext


def download_tiktok(link):
    try:
        videoid = parse_tiktok_link(link)
        save_as = str(videoid)
        return TikTokAPI().downloadVideoById(videoid, f"{save_as}.mp4")
        # you need to edit TikTokAPI's downloadVid.py to return save_path for this to work
    except:
        raise InvalidLink


def download_twitchclip(url, output_path=output_file):
    """Download twitch clips"""
    if "m.twitch.tv" in url:
        # convert mobile link to pc link
        url = url.replace("https://m.", "https://clips.").replace("/clip/", "/").split("?")[0]
    aut_params = {'client_id': config.Twitch.client_id, 'client_secret': config.Twitch.client_secret,
                  'grant_type': 'client_credentials'}
    data = requests.post(url='https://id.twitch.tv/oauth2/token', params=aut_params).json()
    token = data["access_token"]
    h = {"Client-ID": config.Twitch.client_id, 'client_secret': config.Twitch.client_secret,
         'Authorization': "Bearer " + token}
    slug = str(url).split('/')[-1]
    if "medium=redt" in slug:
        slug = slug.split('?')[0]
    clip_info = requests.get("https://api.twitch.tv/helix/clips?id=" + slug, headers=h).json()
    thumb_url = clip_info['data'][0]['thumbnail_url']
    mp4_url = thumb_url.split("-preview", 1)[0] + ".mp4"
    output_path = url.split("/")[-1] + ".mp4"
    urllib.request.urlretrieve(mp4_url, output_path)
    return output_path


def convert_reddit_url(video_url):
    r = authenticate()
    vid = r.submission(url=video_url)
    return vid.url


def download_video(video_url, start=None, to=None):
    video_url = str(video_url)
    supported = 1
    if "reddit.com" in video_url:
        try:
            video_url = convert_reddit_url(video_url)
        except errs.TooManyReqs:
            raise
        except:
            return 0, 0
        of = download_reddit(video_url)
    elif "v.redd.it" in video_url:
        of = download_reddit(video_url)
    elif "twitch.tv" in video_url:
        of = download_twitchclip(video_url)
    elif "tiktok" in video_url:
        of = download_tiktok(video_url)
    elif "vocaroo" in video_url:
        of = download_vocaroo(video_url)
    elif "streamable.com" in video_url:
        of = download_streamable(video_url)
    elif "cdn.discordapp.com" in video_url:
        of = download_discord(video_url)
    elif "drive.google.com" in video_url:
        of = download_google(video_url)
    elif "sndup.net" in video_url:
        of = download_sndup(video_url)
    elif "youtu" in video_url and "https://" in video_url:
        try:
            of = download_yt(video_url)
        except errs.TooManyReqs:
            supported = 0
            of = 0
    else:  # for unsupported links
        supported = 0
        of = 0
    return supported, of
