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
import bot
import multiprocessing
from pytube import YouTube
from acrcloud.recognizer import ACRCloudRecognizer

r = bot.authenticate()


def autoreply():  # auto-reply to comments in r/all
    while True:
        try:
            s = r.subreddit('all').comments()
            for c in s:
                if "what song is this" in str(c.body).lower() or "what's the song" in str(c.body).lower() or "what's this song" in str(c.body).lower() or "what is this song" in str(c.body).lower() or "what song is playing" in str(c.body).lower():
                    supported = bot.download_video(c.submission.url)
                    if supported == 1:
                        data = bot.recognize_audio(bot.output_file)
                        confidence = int(data['score'])
                        if str(data["msg"]) == "success" and confidence >= 50:
                            re = bot.parse_response(data, 0)
                        else:  # if couldn't recognize or confidence < 50, don't reply
                            continue
                    else:
                        continue  # if video type isn't supported, don't reply
                    c.reply(re + config.Reddit.footer)
        except:
            print(traceback.format_exc())
            time.sleep(1)


def mentions():
    while True:
        try:
            for msg in r.inbox.unread():
                msg.mark_read()
                txt = str(msg.body)
                words = txt.split(" ")
                start_sec = 0
                if "youtu.be" in txt or "youtube" in txt:
                    url = ""
                    time_str = "00:00:00"
                    try:
                        for word in words:
                            if "youtu.be" in word or "youtube" in word:
                                url = word
                                bot.download_yt(url)
                                start_sec, time_str = bot.get_youtube_link_time(url)
                            elif url != "" and start_sec == 0 and ":" in word:
                                try:
                                    start_sec = bot.timestamp_to_sec(word)
                                    time_str = word
                                except:
                                    pass
                        data = bot.recognize_audio(bot.output_file, start_sec)
                        re = bot.parse_response(data, time_str, 'youtube')
                    except:
                        re = bot.parse_response('error', time_str, 'youtube')
                    msg.reply(re)

                elif "u/find-song" in txt:
                    for word in words:
                        try:
                            start_sec = bot.timestamp_to_sec(word)
                            break
                        except:
                            pass
                    supported = bot.download_video(msg.submission.url)
                    if supported == 1:
                        start_sec = "0:0:0"
                        data = bot.recognize_audio(bot.output_file, bot.timestamp_to_sec(start_sec))
                        msg.reply(bot.parse_response(data, start_sec))
                    else:
                        msg.reply(bot.parse_response("I don't currently support this video link type. Please check back later!"))

                elif ":" in txt:  # if a reply is just a timestamp
                    for word in words:
                        try:
                            start_sec = bot.timestamp_to_sec(word)
                            break
                        except:
                            pass
                    supported = bot.download_video(msg.submission.url)
                    if supported == 1:
                        data = bot.recognize_audio(bot.output_file, start_sec)
                        re = bot.parse_response(data, start_sec)
                        msg.reply(re)

        except:
            print(traceback.format_exc())
        time.sleep(1)


if __name__ == '__main__':
    autoreply_process = multiprocessing.Process(target=autoreply)  # auto-reply multiprocess
    mentions_process = multiprocessing.Process(target=mentions)  # mention reply multiprocess
    autoreply_process.start()
    mentions_process.start()
