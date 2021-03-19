import config
import praw
import traceback

output_file = 'output.mp4'


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

    def search_download_recognize_youtube_video(self, song, artist):
        import time
        try:
            self.start_driver()
            self.driver.get('https://google.com/search?q=' + str(song) + ' by ' + str(artist) + ' youtube')
            time.sleep(2)
            try:
                self.driver.find_element_by_xpath('/html/body/div[8]/div/div[8]/div/div[2]/div[3]/div[1]').click()
            except:
                pass
            try:
                elem = self.driver.find_element_by_link_text("Search for English results only")
                self.click_on_location(-200, -215)
            except:
                self.click_on_location(-200, -250)
            time.sleep(1)
            url = self.driver.current_url
            download_yt(url, 'scraper_output.mp4')
            self.driver.quit()
            return recognize_audio('scraper_output.mp4'), url
        except Exception as e:
            self.driver.quit()
            print(traceback.format_exc())
            raise e


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
    data = json.loads(acr.recognize_by_file(file, start_sec, 30))  # try to recognize to the song using 30 seconds of the file's audio
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
        # for m in data['metadata']['music']:
        #     print(m)
        # print("\n")
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
    import time
    if ms >= 3600000:
        return time.strftime("%H:%M:%S", time.gmtime(ms / 1000))
    else:
        return time.strftime("%M:%S", time.gmtime(ms / 1000))


def sectoMin(secs):
    """Convert seconds to 0:00 format"""
    import time
    if secs >= 3600:
        return time.strftime("%H:%M:%S", time.gmtime(secs))
    else:
        return time.strftime("%M:%S", time.gmtime(secs))


def timestamp_to_sec(time_str):
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
    if "medium=redt" in slug:
        slug = slug.split('?')[0]
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


def find_link(input_song, input_artists):
    """Search spotify for song,
     if that fails then google the youtube video.
     Output link if either is successful"""
    spotify = Spotify()
    chrome = Chrome()
    correct_url = None
    input_song = str(input_song).lower()
    input_artists = str(input_artists).lower()
    results = spotify.client.search(q='track:' + str(input_song))['tracks']['items']
    found = False
    for r in results:
        name = str(r['name'])
        artist = str(r['artists'][0]['name'])
        url = str(r['external_urls']['spotify'])
        if name.lower() == input_song and artist.lower() == input_artists:
            correct_url = url
            found = True
            break
    if not found:
        try:
            data, url = chrome.search_download_recognize_youtube_video(input_song, input_artists)
        except Exception as e:
            data, url = {'msg': "error", 'type': type(e).__name__}, ""

        if data['msg'] == "success" and str(data['title']).lower() == input_song and str(data['artists']).lower() == input_artists:
            correct_url = url
            print("youtube match")
    return correct_url


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
    try:
        song_url = find_link(data["title"], data['artists'])
    except:
        song_url = None
    try:
        if "youtube" in content or "youtu.be" in content:
            if "(" in content and ")" in content:
                content = content.split("(")[-1]
                content = content.split(")")[0]
            if start_sec != 0 and not ("t=" in content or "time_continue=" in content or "start=" in content):
                content += "?t=" + str(start_sec)
    except:
        pass
    try:
        start_sec = timestamp_to_sec(start_sec)
        time_str = sectoMin(start_sec)
    except:
        time_str = "0:0:00"
    if data == "error":
        re = "I couldn't get the audio from that video, got error **" + start_sec + "**"
    else:
        confidence = str(data['score'])
        if str(data["msg"]) == "success":
            if song_url is not None:  # if I have the spotify link
                print(song_url)

                if "youtube" in song_url or "youtu.be" in song_url:
                    song_url += "&t=" + str(round(int(data['play_offset']) / 1000))

                if int(confidence) == 100:
                    re = "[" + clear_formatting(str(data["title"])) + " by " + \
                         clear_formatting(str((data["artists"]))) + "](" + str(song_url) + ") (" + \
                     str(mstoMin(int(data['play_offset']))) + "/" + str(
                    mstoMin(int(data['duration']))) + ")\n\n"
                elif int(confidence) > 70:
                    re = "I think it's:\n\n[" + clear_formatting(str(data["title"])) + " by " + \
                         clear_formatting(str((data["artists"]))) + "](" + str(song_url) + ") (" + \
                         str(mstoMin(int(data['play_offset']))) + "/" + str(mstoMin(int(data['duration']))) + ", confidence " \
                                    + confidence + "%)\n\n"
                else:
                    re = "I'm not sure, but this might be it:\n\n[" + clear_formatting(str(data["title"])) + " by " + \
                         clear_formatting(str((data["artists"]))) + "](" + str(song_url) + ") (" + \
                         str(mstoMin(int(data['play_offset']))) + "/" + str(mstoMin(int(data['duration']))) + ", confidence " \
                                    + confidence + "%)\n\n"

            else:  # otherwise give an acrcloud link
                if int(confidence) == 100:
                    re = "[" + clear_formatting(str(data["title"])) + " by " + \
                         clear_formatting(str((data["artists"]))) + "](https://www.aha-music.com/" \
                         + acr_create_link(str(data["title"]), str(data["artists"]), str(data['acrID'])) + ") (" + \
                         str(mstoMin(int(data['play_offset']))) + "/" + str(mstoMin(int(data['duration']))) + ")\n\n"
                elif int(confidence) > 70:
                    re = "I think it's:\n\n[" + clear_formatting(str(data["title"])) + " by " + \
                         clear_formatting(str((data["artists"]))) + "](https://www.aha-music.com/" \
                         + acr_create_link(str(data["title"]), str(data["artists"]), str(data['acrID'])) + ") (" + \
                         str(mstoMin(int(data['play_offset']))) + "/" + str(mstoMin(int(data['duration']))) + ", confidence " \
                                    + confidence + "%)\n\n"
                else:
                    re = "I'm not sure, but this might be it:\n\n[" + clear_formatting(str(data["title"])) + " by " + \
                         clear_formatting(str((data["artists"]))) + "](https://www.aha-music.com/" \
                         + acr_create_link(str(data["title"]), str(data["artists"]), str(data['acrID'])) + ") (" + \
                         str(mstoMin(int(data['play_offset']))) + "/" + str(mstoMin(int(data['duration']))) + ", confidence " \
                                    + confidence + "%)\n\n"
        else:
            re = "No song was found"
        if "youtu.be" in content or "youtube" in content:
            if start_sec != 0:
                # re += "\n\n*Looks like you wanted the song playing [@" + time_str + "](" + content + ").*"
                re += "\n\n*Looks like you wanted the song playing in a youtube video @" + time_str + ".*"
            else:
                # re += "\n\n*Looks like you wanted the song from [this video](" + content + ").*"
                re += "\n\n*Looks like you wanted the song from a youtube video.*"
        elif content == "autoreply":
            re += "\n\n*I am a bot, and this action was performed automatically.*"
        else:
            to = sectoMin(start_sec + 30)
            re += "\n\n*I searched from " + time_str + "-" + to + ".*\n\n*Reply with a timestamp to start somewhere else.*"

        if "No song was found" not in re:
            try:
                with open('stats.txt', 'ab') as fb:
                    fb.write(str(str(data["title"]) + ";;" + str(data["artists"]) + "\n").encode('utf8'))
            except:
                print(data)
                print(traceback.format_exc())
    return re + config.Reddit.footer



