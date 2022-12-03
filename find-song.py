import concurrent.futures
import os
import time
import config
import misc
from acr_ratehandler import Ratehandler


class Bot:
    def __init__(self, account, reddit_auth, ratehandler):
        self.auth = reddit_auth
        self.acc_info = account
        self.rh = ratehandler
        self.files_to_del = []

    def mentions_reply(self):
        reqs = []
        while True:
            for file in self.files_to_del:
                # self.files_to_del format: [[filename, time_when_to_del], ...]
                try:
                    if time.time() > file[1]:
                        os.remove(file[0])
                        print(f"deleted file {file[0]}")
                        self.files_to_del.remove(file)
                except:
                    pass
            try:
                for msg in self.auth.inbox.unread():
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
                                if str(msg.parent().author) != self.acc_info.user and "https://" in str(msg.parent().body):  # if there's no parent comment it will error out into the except statement
                                    words = str(msg.body).replace("\n", " ").replace(",", " ").split(" ")
                                    for word in words:
                                        if ("youtu" in video_url and "https://" in video_url) or "twitch.tv" in word or "v.redd.it" in word:  # make sure the parent has a compatible link
                                            ctx, video_url = "link_parent", word
                                            break
                                else:
                                    raise Exception("no link")
                                    # if parent comment exists but doesn't have a link,
                                    # or it was left by the bot, jump to except statement

                            except:
                                # if the try statement fails
                                # assume they want the submission audio, or video from submission text
                                if "https://" in str(msg.submission.selftext) and "u/" + self.acc_info.user in msg.body:
                                    # is there a link in submission selftext?
                                    words = str(msg.submission.selftext).split(" ")
                                    for word in words:
                                        if "https://" in word:
                                            ctx, video_url = "selftxt_link", word
                                            break
                                elif "u/" + self.acc_info.user in str(msg.body).lower():
                                    # use submission's audio
                                    video_url = str(msg.submission.url)
                                    ctx = "video_submission"
                                else:
                                    # bot wasn't mentioned in the comment, or no link/video found
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
                                    if "u/" + self.acc_info.user not in str(msg.body).lower():
                                        # bot wasn't mentioned in the comment
                                        skip = True
                                        break
                                except:
                                    pass
                                try:
                                    if ":" in word_split[-1]:  # 0:30 format
                                        to = misc.timestamptoSec(word_split[-1])
                                    else:  # 30 format (just plain seconds)
                                        to = int(word_split[-1])
                                except (misc.NoTimeStamp, ValueError):
                                    # the current word is not a timestamp, or it has ":" but no numbers
                                    if "u/" + self.acc_info.user not in str(msg.body).lower():
                                        # bot wasn't mentioned in the comment
                                        skip = True
                                        break
                            else:  # else, assume they gave just the starting point
                                try:
                                    if ":" in word:  # 0:30 format
                                        start = misc.timestamptoSec(word)
                                    else:  # 30 format (just plain seconds)
                                        start = int(word)
                                except misc.NoTimeStamp:
                                    skip = True
                                    break
                                except:
                                    pass
                        if skip and "u/" + self.acc_info.user not in str(msg.body).lower() and "https://" not in str(msg.body).lower():
                            # this comment isn't for the bot to reply to
                            msg.mark_read()
                            continue
                        video_url = misc.clear_formatting(video_url)
                        if start == -1:
                            if "youtu" in video_url and "https://" in video_url:
                                start = misc.get_yt_link_time(video_url)
                                # does the youtube link have &t=
                            else:
                                start = 0
                        if to == -1:
                            to = start + 30

                        if "v.redd.it" in video_url:
                            output_file = misc.download_reddit(video_url + "/DASH_audio.mp4")
                        elif "twitch.tv" in video_url:
                            output_file = misc.download_twitchclip(video_url)
                        elif "youtu" in video_url and "https://" in video_url:
                            try:
                                output_file = misc.download_yt(video_url)
                            except misc.TooManyReqs:
                                reqs.append([video_url, msg, time.time(), start, to, ctx, 0])
                                # youtube ratelimited us, lets come back to this comment later
                                msg.mark_read()
                                continue
                            except:
                                # other exceptions, skip the comment for good
                                msg.mark_read()
                                continue
                        else:
                            try:
                                output_file = misc.download_reddit(video_url)
                                # we've checked for supported video websites
                                # for other websites lets try brute forcing downloading the video
                                # to see if it works
                            except:
                                raise misc.NoVideo

                        try:
                            data = misc.identify_audio(file=output_file, start_sec=start, end_sec=to, ratehandler=self.rh)
                        except misc.NoValidKey:
                            print("no valid keys left!")
                            msg.mark_read()
                            continue
                        self.queue_del_file(output_file, 600)
                        if msg.was_comment:
                            if data['msg'] == "error":
                                # don't comment "no song found", private message the OP
                                self.auth.redditor(str(msg.author)).message("No song found", misc.create_response(data, ctx, video_url, start, to) + "\n\n^(This is a response to your comment \"" + msg.body + "\" in r/" + str(msg.subreddit) + ")")
                            else:
                                try:
                                    # if song found, reply to the comment
                                    msg.reply(misc.create_response(data, ctx, video_url, start, to))
                                except:
                                    try:
                                        # if can't comment, private message the OP
                                        self.auth.redditor(str(msg.author)).message("I couldn't reply to your comment, here's a PM instead", misc.create_response(data, ctx, video_url, start, to) + "\n\n^(This is a response to your comment \"" + msg.body + "\" in r/" + str(msg.subreddit) + ")")
                                    except:
                                        pass
                        else:
                            # if received a private message, respond to the sender
                            self.auth.redditor(str(msg.author)).message(str(misc.sectoMin(start)) + "-" + str(misc.sectoMin(to)), misc.create_response(data, ctx, video_url, start, to) + "\n\n^(This is a response to your PM \"" + msg.body + "\")")
                    except:
                        pass
                    msg.mark_read()
            except:
                pass

            try:
                # handle the comments we marked as "respond to later"
                for context in reqs:
                    if time.time() - context[2] > 1800:
                        video_url = context[0]
                        msg = context[1]
                        start, to, ctx = context[3], context[4], context[5]
                        try:
                            output_file = misc.download_part_yt(video_url, start, to)
                        except misc.RateLimit:
                            context[6] += 1
                            context[2] = time.time()
                            continue

                        try:
                            data = misc.identify_audio(file=output_file, start_sec=start, end_sec=to, ratehandler=self.rh)
                        except misc.NoValidKey:
                            print("no valid keys left!")
                            msg.mark_read()
                            continue
                        self.queue_del_file(output_file, 600)
                        if msg.was_comment:
                            if data['msg'] == "error":
                                self.auth.redditor(str(msg.author)).message("No song found", misc.create_response(data, ctx, video_url, start, to) + "\n\n^(This is a response to your comment \"" + msg.body + "\" in r/" + str(msg.subreddit) + ")")
                            else:
                                try:
                                    msg.reply(misc.create_response(data, ctx, video_url, start, to))
                                except:
                                    try:
                                        self.auth.redditor(str(msg.author)).message("I couldn't reply to your comment, here's a PM instead", misc.create_response(data, ctx, video_url, start, to) + "\n\n^(This is a response to your comment \"" + msg.body + "\" in r/" + str(msg.subreddit) + ")")
                                    except:
                                        pass
                        else:
                            self.auth.redditor(str(msg.author)).message(str(misc.sectoMin(start)) + "-" + str(misc.sectoMin(to)), misc.create_response(data, ctx, video_url, start, to) + "\n\n^(This is a response to your PM \"" + msg.body + "\")")
            except:
                pass

    def auto_reply(self):  # auto-reply to comments in r/all
        replied = []
        while True:
            try:
                s = self.auth.subreddit('all').comments()
                for c in s:
                    if c.id in replied or c.subreddit == "NameThatSong":
                        continue
                    replied.append(c.id)
                    if len(replied) > 10:
                        # keep a list of 10 comments already responded to just in case it goes over the same comment
                        # twice (very unlikely with the amount of comments being left on r/all)
                        replied.pop(0)
                    b_txt = str(c.body).lower()
                    if "u/find-song" in b_txt:
                        # if a comment has capitalized the U in u/find-song the bot won't be notified in its inbox
                        # so this manually checks r/all
                        # (this used to be for checking for "what's this song" comments and replying to them but the bot doesn't do that anymore)
                        surl = c.submission.url
                        supported, output_file = misc.download_video(surl)
                        try:
                            start_sec = misc.get_yt_link_time(surl)
                        except:
                            start_sec = 0
                        if supported == 1:
                            try:
                                data = misc.identify_audio(file=output_file, start_sec=start_sec, ratehandler=self.rh)
                            except misc.NoValidKey:
                                print("no valid keys left!")
                                continue
                            self.queue_del_file(output_file, 600)
                            re = misc.create_response(data, "autoreply", surl, start_sec, start_sec + 30)
                        else:
                            continue  # if video type isn't supported, don't reply

                        if data['msg'] == "error":
                            self.auth.redditor(str(c.author)).message("No song found", re + "\n\n^(This is a response to your comment \"" + c.body + "\" in r/" + str(c.subreddit) + ")")
                        else:
                            try:
                                c.reply(re)
                            except:
                                try:
                                    self.auth.redditor(str(c.author)).message("I couldn't reply to your comment, here's a PM instead", re + "\n\n^(This is a response to your comment \"" + c.body + "\" in r/" + str(c.subreddit) + ")")
                                except:
                                    pass
            except:
                pass

    def queue_del_file(self, filepath: str, how_long_to_wait: int):
        self.files_to_del.append([filepath, time.time() + how_long_to_wait])


if __name__ == '__main__':
    rate = Ratehandler(100, "ratehandler.txt").load_key_reqs("saved_reqs.txt")
    bot = Bot(account=misc.cf, reddit_auth=misc.authenticate(), ratehandler=rate)
    with concurrent.futures.ProcessPoolExecutor() as proc:
        mentions_proc = proc.submit(bot.mentions_reply)
        auto_proc = proc.submit(bot.auto_reply)
