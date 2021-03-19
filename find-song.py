import time
import traceback
import bot, config
import multiprocessing


r = bot.authenticate()


def ctx_reply(ctx, response, dm_on_fail=True):
    try:
        ctx.reply(response)
    except Exception as e:
        print("couldn't reply in", ctx.subreddit, ": error", type(e).__name__)
        if dm_on_fail:

            # r.redditor(str(ctx.author)).message("I couldn't reply to your comment, here's a PM instead", "This is a response to [this comment](" + ctx.+ ").\n\n" + str(response))
            r.redditor(str(ctx.author)).message("I couldn't reply to your comment, here's a PM instead", response)
            print("dmd", ctx.author)
            print(ctx.submission.url)
            print(ctx.url)


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
                            re = bot.parse_response(data, 0, "autoreply")
                        else:  # if couldn't recognize or confidence < 50, don't reply
                            continue
                    else:
                        continue  # if video type isn't supported, don't reply
                    ctx_reply(c, re, False)
        except:
            pass
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
                            try:
                                checkint = int(word)
                                checkint = True
                            except:
                                checkint = False
                            if "youtu.be" in word or "youtube" in word:
                                url = word
                                bot.download_yt(url)
                                start_sec, time_str = bot.get_youtube_link_time(url)
                            elif ":" in word or checkint:
                                try:
                                    start_sec = bot.timestamp_to_sec(word)
                                    time_str = bot.sectoMin(start_sec)
                                except:
                                    pass
                        data = bot.recognize_audio(bot.output_file, start_sec)
                        re = bot.parse_response(data, time_str, url)
                    except Exception as e:
                        print(traceback.format_exc())
                        re = bot.parse_response('error', type(e).__name__, 'youtube')
                    ctx_reply(msg, re)

                elif "u/find-song" in txt:
                    url = ""
                    time_str = "00:00:00"
                    try:
                        if str(msg.parent().author) != "find-song":
                            parent_txt = str(msg.parent().body)
                            parent_txt = parent_txt.split(" ")
                            for word in parent_txt:
                                if "youtu.be" in word or "youtube" in word:
                                    url = word
                                    bot.download_yt(url)
                                    start_sec, time_str = bot.get_youtube_link_time(url)
                            txt = txt.split(" ")
                            for word in txt:
                                try:
                                    checkint = int(word)
                                    checkint = True
                                except:
                                    checkint = False
                                if ":" in word or checkint:
                                    try:
                                        start_sec = bot.timestamp_to_sec(word)
                                        time_str = bot.sectoMin(start_sec)
                                    except:
                                        pass
                    except:
                        pass
                    if url != "":
                        data = bot.recognize_audio(bot.output_file, start_sec)
                        re = bot.parse_response(data, time_str, url)
                        ctx_reply(msg, re)
                    else:
                        for word in words:
                            try:
                                start_sec = bot.timestamp_to_sec(word)
                                break
                            except:
                                pass
                        supported = bot.download_video(msg.submission.url)
                        if supported == 1:
                            data = bot.recognize_audio(bot.output_file, start_sec)
                            ctx_reply(msg, bot.parse_response(data, bot.sectoMin(start_sec)))
                        else:
                            ctx_reply(msg, "I couldn't find the audio.\n\nMake sure it's a v.reddit, youtube, or twitch link, and try again" + config.Reddit.footer)

                else:  # if theres a timestamp in a reply
                    import re
                    checkint = ""
                    for word in words:
                        word = re.sub(r'[^a-zA-Z0-9]', '', word)  # exclude all chars except alphanumerals
                        try:
                            checkint = int(word)
                            start_sec = bot.timestamp_to_sec(word)
                            break
                        except:
                            pass
                    if checkint != "" and ("seconds" in words or "secs" in words or ":" in words):
                        supported = bot.download_video(msg.submission.url)
                        if supported == 1:
                            data = bot.recognize_audio(bot.output_file, start_sec)
                            re = bot.parse_response(data, bot.sectoMin(start_sec))
                            ctx_reply(msg, re)

        except:
            print(traceback.format_exc())
        time.sleep(1)


if __name__ == '__main__':
    autoreply_process = multiprocessing.Process(target=autoreply)  # auto-reply multiprocess
    mentions_process = multiprocessing.Process(target=mentions)  # mention reply multiprocess
    autoreply_process.start()
    mentions_process.start()

