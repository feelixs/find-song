import concurrent.futures
import time
import traceback
import config
import misc

r = misc.authenticate()


def mentions_reply():
    while True:
        for msg in r.inbox.unread():
            print(msg.body)
            timer = time.time()
            ctx, comment = None, None
            if ("u/" + config.Reddit.user) in msg.body:  # if it's a mention
                comment = msg.reply("*One sec, I'm sampling the audio...*\n\nRefresh in a few seconds to see the result")
                print("did quick comment after ", time.time() - timer)
            try:
                try:  # check if the parent comment (if there is any) contains a youtube link
                    if str(msg.parent().author) != config.Reddit.user and "https://" in str(msg.parent().body):  # if there's no parent comment it will error out into the except statement
                        words = str(msg.parent().body).split(" ")
                        for word in words:
                            if "https://youtu" in word or "https://twitch.tv" in word or "https://v.redd.it" in word:  # make sure the parent has a compatible link
                                ctx, video_url = "link_parent", word
                                break
                    else:
                        raise Exception("no link")  # if one exists but doesn't have a link, or it was left by the bot, jump to except statement
                except:
                    if "https://" in str(msg.body):  # if the original message has youtube link
                        words = str(msg.body).split(" ")
                        for word in words:
                            if "https://" in word:
                                ctx, video_url = "link_comment", word
                                break
                    else:  # else, assume they want the submission audio, or video from submission text
                        if "https://" in str(msg.submission.selftext) and (("u/" + config.Reddit.user) in msg.body or ":" in msg.body):
                            words = str(msg.submission.selftext).split(" ")
                            for word in words:
                                if "https://" in word:
                                    ctx, video_url = "selftxt_link", word
                                    break
                        elif ("u/" + config.Reddit.user) in msg.body or ":" in msg.body:  # else, assume they want the submission's video audio
                            video_url = str(msg.submission.url)
                            ctx = "video_submission"
                        else:
                            continue

                start = -1
                to = -1
                msg_words = str(msg.body).split(" ")  # get timestamp from original msg
                for word in msg_words:
                    if "-" in word:  # if given start and end (0:30-0:50 or 30-50 formats)
                        word_split = word.split("-")
                        try:
                            if ":" in word_split[0]:  # 0:30 format
                                start = misc.timestamptoSec(word_split[0])
                            else:  # 30 format (just plain seconds)
                                start = int(word_split[0])
                        except:
                            pass
                        try:
                            if ":" in word_split[-1]:  # 0:30 format
                                to = misc.timestamptoSec(word_split[-1])
                            else:  # 30 format (just plain seconds)
                                to = int(word_split[-1])
                        except:
                            pass
                    else:  # else, assume they gave just the starting point
                        try:
                            if ":" in word:  # 0:30 format
                                start = misc.timestamptoSec(word)
                            else:  # 30 format (just plain seconds)
                                start = int(word)
                        except:
                            pass

                video_url = misc.clear_formatting(video_url)
                if start == -1:
                    if "https://youtu" in video_url:
                        start = misc.get_yt_link_time(video_url)
                    else:
                        start = 0
                if to == -1:
                    to = start + 30
                start, to = misc.sectoMin(start), misc.sectoMin(to)
                if comment is None:
                    msg.reply("*One sec, I'm sampling the audio...*\n\nRefresh in a few seconds to see the result\n\n^(You gave me~" + ctx + "~)\n\n^(Your url~" + video_url + "~)\n\n^(I'm searching from~" + start + "~" + to + "~)" + config.Reddit.footer)
                else:
                    comment.edit("*One sec, I'm sampling the audio...*\n\nRefresh in a few seconds to see the result\n\n^(You gave me~" + ctx + "~)\n\n^(Your url~" + video_url + "~)\n\n^(I'm searching from~" + start + "~" + to + "~)" + config.Reddit.footer)
                    print(time.time() - timer)
            except Exception as e:
                print(traceback.format_exc())
                print(type(e).__name__)
            msg.mark_read()


def edit_comments():
    while True:
        for comment in r.redditor(config.Reddit.user).comments.new():
            with open('edited.txt', 'r') as f:
                edited = f.read()
            try:
                if str(comment.id) not in edited and "You gave me" in comment.body:
                    c_attrs = str(comment.body).split("~")
                    ctx, ctx_url, start, to = c_attrs[1], c_attrs[3], misc.timestamptoSec(c_attrs[5]), misc.timestamptoSec(c_attrs[6])
                    print(ctx, ctx_url, start, to)
                    if "https://v.redd.it" in ctx_url:
                        output_file = misc.download_reddit(ctx_url + "/DASH_audio.mp4")
                    elif "https://twitch.tv" in ctx_url:
                        output_file = misc.download_twitchclip(ctx_url)
                    elif "https://youtu" in ctx_url:
                        output_file = misc.download_yt(ctx_url)
                    else:
                        output_file = ""
                    data = misc.identify_audio(output_file, start, to)
                    print(data)
                    comment.edit(misc.create_response(data, ctx, ctx_url, start, to))
                    with open('edited.txt', 'a') as f:  # don't edit this comment again
                        f.write(comment.id + "\n")
            except Exception as e:
                print(traceback.format_exc())
                comment.edit("Something went wrong, got error **" + type(e).__name__ + "**" + config.Reddit.footer)
                with open('edited.txt', 'a') as f:  # don't edit this comment again
                    f.write(comment.id + "\n")


if __name__ == '__main__':
    with concurrent.futures.ProcessPoolExecutor() as proc:
        mentions_proc = proc.submit(mentions_reply)
        edit_proc = proc.submit(edit_comments)
