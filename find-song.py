import concurrent.futures
import time
import traceback
import config
import misc

r = misc.authenticate()


def mentions_reply():
    while True:
        try:
            for msg in r.inbox.unread():
                ctx = None
                try:
                    if "https://" in str(msg.body):  # if the original message has a link
                        words = str(msg.body).replace("\n", " ").replace(",", " ").split(" ")
                        for word in words:
                            if "https://" in word:
                                ctx, video_url = "link_comment", word
                                break
                    else:
                        try:  # check if the parent comment (if there is any) contains a youtube link
                            if str(msg.parent().author) != config.Reddit.user and "https://" in str(msg.parent().body):  # if there's no parent comment it will error out into the except statement
                                words = str(msg.body).replace("\n", " ").replace(",", " ").split(" ")
                                for word in words:
                                    if "https://youtu" in word or "https://www.youtu" in word or "twitch.tv" in word or "v.redd.it" in word:  # make sure the parent has a compatible link
                                        ctx, video_url = "link_parent", word
                                        break
                            else:
                                raise Exception("no link")  # if one exists but doesn't have a link, or it was left by the bot, jump to except statement

                        except:  # else, assume they want the submission audio, or video from submission text
                            if "https://" in str(msg.submission.selftext) and (("u/" + config.Reddit.user) in msg.body or ":" in msg.body):
                                words = str(msg.submission.selftext).split(" ")
                                for word in words:
                                    if "https://" in word:
                                        ctx, video_url = "selftxt_link", word
                                        break
                            elif ("u/" + config.Reddit.user) in str(msg.body).lower() or ":" in msg.body:  # else, assume they want the submission's video audio
                                video_url = str(msg.submission.url)
                                ctx = "video_submission"
                            else:
                                print(msg.body, "> no context, skipping")
                                msg.mark_read()
                                continue

                    start = -1
                    to = -1
                    skip = False
                    msg_words = str(msg.body).split(" ")  # get timestamp from original msg
                    for word in msg_words:
                        if "-" in word:  # if given start and end (0:30-0:50 or 30-50 formats)
                            word_split = word.split("-")
                            try:
                                if ":" in word_split[0]:  # 0:30 format
                                    start = misc.timestamptoSec(word_split[0])
                                else:  # 30 format (just plain seconds)
                                    start = int(word_split[0])
                            except misc.NoTimeStamp:
                                if "u/" + config.Reddit.user not in str(msg.body).lower():
                                    skip = True
                                    break
                            except:
                                pass
                            try:
                                if ":" in word_split[-1]:  # 0:30 format
                                    to = misc.timestamptoSec(word_split[-1])
                                else:  # 30 format (just plain seconds)
                                    to = int(word_split[-1])
                            except misc.NoTimeStamp:
                                if "u/" + config.Reddit.user not in str(msg.body).lower():
                                    skip = True
                                    break
                            except:
                                pass
                        else:  # else, assume they gave just the starting point
                            try:
                                if ":" in word:  # 0:30 format
                                    start = misc.timestamptoSec(word)
                                else:  # 30 format (just plain seconds)
                                    start = int(word)
                            except misc.NoTimeStamp:
                                if "u/" + config.Reddit.user not in str(msg.body).lower():
                                    skip = True
                                    break
                            except:
                                pass
                    if skip:
                        print(msg.body, "> no timestamp, skipping")
                        msg.mark_read()
                        continue
                    video_url = misc.clear_formatting(video_url)
                    if start == -1:
                        if "https://youtu" in video_url or "https://www.youtu":
                            start = misc.get_yt_link_time(video_url)
                        else:
                            start = 0
                    if to == -1:
                        to = start + 30

                    if "v.redd.it" in video_url:
                        output_file = misc.download_reddit(video_url + "/DASH_audio.mp4")
                    elif "twitch.tv" in video_url:
                        output_file = misc.download_twitchclip(video_url)
                    elif "https://youtu" in video_url or "https://www.youtu" in video_url:
                        output_file = misc.download_yt(video_url)
                    else:
                        try:
                            output_file = misc.download_reddit(video_url)
                        except:
                            raise misc.NoVideo
                    data = misc.identify_audio(output_file, start, to)

                    if msg.was_comment:  # if it was a comment, reply
                        try:
                            print("replying to", msg.author, "on", msg.submission)
                            msg.reply(misc.create_response(data, ctx, video_url, start, to))
                        except:
                            try:
                                print("pming", msg.author, "on", msg.submission)
                                r.redditor(str(msg.author)).message("I couldn't reply to your comment, here's a PM instead", misc.create_response(data, ctx, video_url, start, to) + "\n\n^(This is a response to your comment \"" + msg.body + "\" in r/" + str(msg.subreddit) + ")")
                            except:
                                pass
                    else:  # if it was a DM, send a DM back to the author
                        r.redditor(str(msg.author)).message(str(misc.sectoMin(start)) + "-" + str(misc.sectoMin(to)), misc.create_response(data, ctx, video_url, start, to) + "\n\n^(This is a response to your PM \"" + msg.body + "\")")

                except Exception as e:
                    print("inner try statment:", traceback.format_exc())
                    print(type(e).__name__)
                    msg.reply("Something went wrong, got error **" + type(e).__name__ + "**" + config.Reddit.footer)
                    print("(error) replied to", msg.author)
                msg.mark_read()
        except:
            print("first try statment:", traceback.format_exc())


def auto_reply():  # auto-reply to comments in r/all
    replied = []
    while True:
        try:
            s = r.subreddit('all').comments()
            for c in s:
                if c.id in replied or c.subreddit == "NameThatSong":
                    continue
                replied.append(c.id)
                if len(replied) > 10:  # keep a list of 10 comments already responded to just in case it goes over the same comment twice (very unlikely with the amount of comments being left on r/all)
                    replied.pop(0)
                b_txt = str(c.body).lower()
                reply_bool = False
                for i in range(len(config.Reddit.activators)):
                    if config.Reddit.activators[i] in b_txt:
                        reply_bool = True
                        break
                if reply_bool:
                    surl = c.submission.url
                    supported, output_file = misc.download_video(surl)
                    try:
                        start_sec = misc.get_yt_link_time(surl)
                    except:
                        start_sec = 0
                    if supported == 1:
                        data = misc.identify_audio(output_file, start_sec)
                        confidence = int(data['score'])
                        if str(data["msg"]) == "success" and confidence >= 80:
                            re = misc.create_response(data, "autoreply", surl, start_sec, start_sec + 30)
                        else:  # if couldn't recognize or confidence < 50, don't reply
                            continue
                        print(c.subreddit, ">", c.author, ">", c.body)
                        print(data)
                    else:
                        continue  # if video type isn't supported, don't reply
                    c.reply(re)
        except:
            print(traceback.format_exc())


if __name__ == '__main__':
    with concurrent.futures.ProcessPoolExecutor() as proc:
        mentions_proc = proc.submit(mentions_reply)
        auto_proc = proc.submit(auto_reply)
