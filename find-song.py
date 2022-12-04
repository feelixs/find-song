import concurrent.futures
import os
import time
import config
import misc
from acr_ratehandler import Ratehandler


REC_LENGTH = 10  # how much secs to sample from each video by default


class Bot:
    def __init__(self, account, reddit_auth, ratehandler):
        self.auth = reddit_auth
        self.acc_info = account
        self.rh = ratehandler
        self.files_to_del = []

    def handle_context(self, msg):
        ctx, video_url = None, None
        if msg.was_comment and ("u/" + self.acc_info.user in str(msg.body).lower() or misc.is_single_timestamp(msg)):
            # the bot should only reply to username mentions, or responses to his own comments that are ONLY timestamps
            try:
                # check for parent comment, if it has a link it'll override the submission audio
                if "https://" in str(msg.parent().body) and "https://" not in str(msg.body):
                    # if there's no parent comment this will error out of the try statement
                    # and the message doesn't have a link (links in msg.body should override parent comments)
                    words = str(msg.parent().body).replace("\n", " ").replace(",", " ").split(" ")
                    for word in words:
                        if ("youtu" in word and "https://" in word) or "twitch.tv" in word or "v.redd.it" in word or "tiktok.com" in word:  # make sure the parent has a compatible link
                            ctx, video_url = "link_parent", word
                            break
            except AttributeError:  # if the comment has no parent
                # it raises AttributeError: 'Submission' object has no attribute 'body'
                if "https://" in str(msg.body):  # if the original message has a link
                    words = str(msg.body).replace("\n", " ").replace(",", " ").split(" ")
                    for word in words:
                        if "https://" in word:
                            ctx, video_url = "link_comment", word
                            break
                elif "https://" in str(msg.submission.selftext):
                    # else, assume they want the submission audio, or video from submission text
                    words = str(msg.submission.selftext).split(" ")
                    for word in words:
                        if "https://" in word:
                            ctx, video_url = "selftxt_link", word
                            break
                else:
                    # else, assume they want the submission's video audio
                    video_url = str(msg.submission.url)
                    ctx = "video_submission"
        elif not msg.was_comment:
            # for replies to PMs made by the bot
            try:
                parent_pm = self.auth.inbox.message(msg.parent_id[3:])  # this gets the first pm in the thread
                if parent_pm.author == self.acc_info.user:  # check that the bot sent the first message in the pm thread
                    words = str(parent_pm.body).replace("\n", " ").replace(",", " ").split(" ")
                    for word in words:
                        if ("youtu" in word and "https://" in word) or "twitch.tv" in word or "v.redd.it" in word or "tiktok.com" in word:  # make sure the parent has a compatible link
                            ctx, video_url = "link_comment", word
                            break
            except TypeError:  # line 58 throws TypeError when there's no parent PM
                # so it's a new PM
                if msg.author is not None:
                    # it was sent by a user
                    words = str(msg.body).replace("\n", " ").replace(",", " ").split(" ")
                    for word in words:
                        if ("youtu" in word and "https://" in word) or "twitch.tv" in word or "v.redd.it" in word or "tiktok.com" in word:  # make sure the parent has a compatible link
                            ctx, video_url = "link_comment", word
                            break
                else:
                    # it's a subreddit message, ignore it
                    pass
        if ctx is None or video_url is None:
            msg.mark_read()
            raise misc.NoContext
        return ctx, video_url

    def find_timestamps(self, msg, video_url):
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
                    if "u/" + self.acc_info.user not in str(msg.body).lower():
                        skip = True
                        break
            else:  # else, assume they gave just the starting point
                try:
                    if ":" in word:  # 0:30 format
                        start = misc.timestamptoSec(word)
                    else:  # 30 format (just plain seconds)
                        start = int(word)
                except:
                    pass
        if skip and "u/" + self.acc_info.user not in str(msg.body).lower() and "https://" not in str(msg.body).lower():
            # bot shouldn't reply to this message
            msg.mark_read()
            raise misc.NoContext
        video_url = misc.clear_formatting(video_url)
        if start == -1:
            if "youtu" in video_url and "https://" in video_url:
                start = misc.get_yt_link_time(video_url)
            else:
                start = 0
        if to == -1:
            to = start + REC_LENGTH
        return start, to, video_url

    def mentions_reply(self):
        reqs = []
        while True:
            for file in self.files_to_del:
                # each file downloaded to check audio will be deleted in this for loop
                # if 10 minutes have passed since they were downloaded
                if file[1] < time.time():
                    try:
                        os.remove(file[0])
                    except:
                        pass
                    self.files_to_del.remove(file)
            try:
                for msg in self.auth.inbox.unread():
                    try:
                        try:
                            ctx, video_url = self.handle_context(msg)
                            start, to, video_url = self.find_timestamps(msg, video_url)
                        except misc.NoContext:
                            continue
                        if "v.redd.it" in video_url:
                            output_file = misc.download_reddit(video_url)
                        elif "twitch.tv" in video_url:
                            output_file = misc.download_twitchclip(video_url)
                        elif "tiktok" in video_url:
                            output_file = misc.download_tiktok(video_url)
                        elif "youtu" in video_url and "https://" in video_url:
                            try:
                                output_file = misc.download_yt(video_url)
                            except misc.TooManyReqs:
                                # ratelimited by youtube, come back to this request later
                                reqs.append([video_url, msg, time.time(), start, to, ctx, 0])   # if youtube gives too many reqs error, store videos and context for future reply
                                msg.mark_read()
                                continue
                            except:
                                msg.mark_read()
                                continue
                        else:
                            try:
                                output_file = misc.download_reddit(video_url)
                            except:
                                raise misc.NoVideo
                        try:
                            data = misc.identify_audio(file=output_file, start_sec=start, end_sec=to, ratehandler=self.rh)
                        except misc.NoValidKey:
                            msg.mark_read()
                            continue
                        self.queue_del_file(output_file, 600)
                        if msg.was_comment:
                            if data['msg'] == "error" and msg.subreddit != "NameThatSong" and msg.subreddit != "WhatsThisSong":
                                # by default don't reply on error, pm instead
                                self.auth.redditor(str(msg.author)).message("No song found", f"{misc.create_response(data, ctx, video_url, start, to)}\n\n^(This is a response to your comment) ^\"^[{msg.body}](https://reddit.com/r/{msg.subreddit}/comments/{msg.submission}/comment/{msg.id})\" ^(in r/" + str(msg.subreddit) + ")")

                            else:
                                try:
                                    msg.reply(misc.create_response(data, ctx, video_url, start, to))
                                except:
                                    try:
                                        self.auth.redditor(str(msg.author)).message("I couldn't reply to your comment, here's a PM instead", f"{misc.create_response(data, ctx, video_url, start, to)}\n\n^(This is a response to your comment) ^\"^[{msg.body}](https://reddit.com/r/{msg.subreddit}/comments/{msg.submission}/comment/{msg.id})\" ^(in r/" + str(msg.subreddit) + ")")
                                    except:
                                        pass
                        else:
                            self.auth.redditor(str(msg.author)).message(str(misc.sectoMin(start)) + "-" + str(misc.sectoMin(to)), misc.create_response(data, ctx, video_url, start, to) + "\n\n^(This is a response to your PM \"" + msg.body + "\")")
                    except:
                        pass
                    msg.mark_read()
            except:
                pass

            try:
                for context in reqs:
                    # retry requests that were ratelimited by youtube
                    if time.time() - context[2] > 1800:  # for youtube ratelimits retry 30 minutes
                        video_url = context[0]
                        msg = context[1]
                        start, to, ctx = context[3], context[4], context[5]
                        try:
                            output_file = misc.download_yt(video_url)
                        except misc.TooManyReqs:
                            context[6] += 1
                            context[2] = time.time()
                            continue
                        try:
                            data = misc.identify_audio(file=output_file, start_sec=start, end_sec=to, ratehandler=self.rh)
                        except misc.NoValidKey:
                            msg.mark_read()
                            continue
                        self.queue_del_file(output_file, 600)
                        if msg.was_comment:
                            if data['msg'] == "error" and msg.subreddit != "NameThatSong" and msg.subreddit != "WhatsThisSong":
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

    def queue_del_file(self, filepath, how_long_to_wait):
        self.files_to_del.append([filepath, time.time() + how_long_to_wait])


if __name__ == '__main__':
    rate = Ratehandler(100, "ratehandler.txt").load_key_reqs("saved_reqs.txt")
    bot = Bot(account=misc.cf, reddit_auth=misc.authenticate(), ratehandler=rate)
    with concurrent.futures.ProcessPoolExecutor() as proc:
        mentions_proc = proc.submit(bot.mentions_reply)
