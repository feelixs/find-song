import config
import praw
import traceback

output_file = "output.mp4"


class Spotify:
    def __init__(self):
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials
        self.scope = "user-library-read"
        self.client = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())


class Chrome:
    def start_driver(self):
        from selenium import webdriver
        self.options = webdriver.ChromeOptions()
        self.options.add_argument("--mute-audio")
        # self.options.add_argument("--no-startup-window")
        self.driver = webdriver.Chrome("C:\\Users\mmh\Downloads\chromedriver_win32\chromedriver.exe", chrome_options=self.options)

    def click_on_location(self, x, y):
        from selenium.webdriver.common.action_chains import ActionChains
        elem = self.driver.find_element_by_xpath('/html')
        AC = ActionChains(self.driver)
        AC.move_to_element(elem).move_by_offset(x, y).click().perform()

    def search_download_recognize_youtube_video(self, song, artist, input_time):
        import time
        try:
            self.start_driver()
            self.driver.get('https://google.com/search?q=' + str(song) + ' by ' + str(artist) + ' youtube')
            i = 0
            while i == 20 or i == -1:
                try:
                    self.driver.find_element_by_xpath('/html/body/div[8]/div/div[8]/div/div[2]/div[3]/div[1]').click()
                    i = -1
                except:
                    pass
                i += 1
            try:
                elem = self.driver.find_element_by_link_text("Search for English results only")
                self.click_on_location(-200, -215)
            except:
                self.click_on_location(-200, -250)
            url = self.driver.current_url
            yt_file = download_yt(url)
            self.driver.quit()
            return identify_audio(yt_file, input_time), url
        except Exception as e:
            self.driver.quit()
            print(traceback.format_exc())
            raise e


def authenticate():
    login = praw.Reddit(username=config.Reddit.user, password=config.Reddit.psw, user_agent=config.Reddit.agent, client_id=config.Reddit.client_id, client_secret=config.Reddit.client_secret)
    return login


def identify_audio(file=None, start_sec=0, end_sec=None):
    """Requests data from ACRCloud and re-formats for manageability"""
    from acrcloud.recognizer import ACRCloudRecognizer
    import json
    import os
    if end_sec is None:
        end_sec = start_sec + 30
    login = {
        "access_key": config.ACR.key,
        "access_secret": config.ACR.secret,
        "host": "identify-us-west-2.acrcloud.com"
    }
    acr = ACRCloudRecognizer(login)
    sample_length = end_sec - start_sec
    try:
        data = json.loads(acr.recognize_by_file(file, start_sec, sample_length))
        os.remove(file)  # delete the file since we don't need it anymore
    except:
        pass
    try:
        title, artists, score, duration, play_offset, acr_id = data["metadata"]["music"][0]["title"], data['metadata']['music'][0]['artists'][0]['name'], \
                                                               data['metadata']['music'][0]['score'], data["metadata"]["music"][0]["duration_ms"], \
                                                               data["metadata"]["music"][0]["play_offset_ms"], data["metadata"]["music"][0]["acrid"]

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


def find_link(acr_data, input_time):
    """Search spotify for song,
     if that fails then google the youtube video.
     Output link if either is successful"""
    import math
    correct_url = None
    input_song = str(acr_data["title"]).lower()
    input_artists = str(acr_data["artists"]).lower()
    chrome = Chrome()
    try:
        data, url = chrome.search_download_recognize_youtube_video(input_song, input_artists, input_time)
    except Exception as e:
        data, url = {'msg': "error", 'type': type(e).__name__}, ""
    if data['msg'] == "success" and str(data['title']).lower() == input_song and str(
            data['artists']).lower() == input_artists:
        correct_url = url + "&t=" + str(math.floor(int(acr_data['play_offset']) / 1000))
        print(correct_url)
        print("youtube match")
    if correct_url is None:
        spotify = Spotify()
        results = spotify.client.search(q='track:' + str(input_song))['tracks']['items']
        for r in results:
            name = str(r['name'])
            artist = str(r['artists'][0]['name'])
            url = str(r['external_urls']['spotify'])
            if name.lower() == input_song and artist.lower() == input_artists:
                correct_url = url
                print("spotify match")
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
        url = find_link(acr_data, start_sec)
        if int(score) == 100:
            response = "[" + title + " by " + artists + "](" + url + ") (" + play_offset + " / " + duration + ")"
        elif int(score) > 70:
            response = "I think it's:\n\n[" + title + " by " + artists + "](" + url + ") (" + play_offset + " / " + duration + ", confidence " + score + ")"
        else:
            response = "I'm not sure, but it might be:\n\n[" + title + " by " + artists + "](" + url + ") (" + play_offset + " / " + duration + ", confidence " + score + ")"
    else:
        response = "No song was found"
    start_sec, end_sec = sectoMin(start_sec), sectoMin(end_sec)
    if context == "link_parent":
        response += "\n\n*Looks like you wanted the song from your parent comment's [link](" + user_url + "). I searched from " + str(start_sec) + "-" + str(end_sec) + "*"
    elif context == "link_comment":
        response += "\n\n*Looks like you gave me a [a link](" + user_url + ") to watch. I searched from " + str(start_sec) + "-" + str(end_sec) + "*"
    elif context == "selftxt_link":
        response += "\n\n*Looks like you wanted the song from [a link](" + user_url + ") in the submission. I searched from " + str(start_sec) + "-" + str(end_sec) + "*"
    elif context == "video_submission":
        response += "\n\n*Looks like you wanted the song from [here](" + user_url + "). I searched from " + str(start_sec) + "-" + str(end_sec) + "*"
    else:
        response += "\n\n*I am a bot, and this action was performed automatically*"

    return response + config.Reddit.footer


def sectoMin(secs) -> str:
    """Convert seconds to 0:00 format"""
    import time
    secs = int(secs)
    if secs >= 3600:
        return time.strftime("%H:%M:%S", time.gmtime(secs))
    else:
        return time.strftime("%M:%S", time.gmtime(secs))


def mstoMin(ms) -> str:
    """Convert milliseconds to 0:00 format"""
    import time
    if ms >= 3600000:
        return time.strftime("%H:%M:%S", time.gmtime(ms / 1000))
    else:
        return time.strftime("%M:%S", time.gmtime(ms / 1000))


def timestamptoSec(time_str) -> int:
    """Get Seconds from time."""
    time_str = str(time_str)
    list = time_str.split(':')
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
    print(string)
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
    print(word)
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
    import requests
    mp4 = requests.get(link)
    with open(file, 'wb') as f:
        for chunk in mp4.iter_content(chunk_size=255):
            if chunk:
                f.write(chunk)
    return file


def download_yt(link):
    """Downloads video from youtube links"""
    import os
    from pytube import YouTube
    mp4 = YouTube(link)
    mp4.streams.filter(file_extension="mp4")
    of = mp4.streams.get_by_itag(18).download()
    return of


def download_twitchclip(url, output_path=output_file):
    """Download twitch clips"""
    import requests
    import urllib.request
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


