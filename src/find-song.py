import concurrent.futures
import os
import time
import traceback
import config
import misc
from acr_ratehandler import Ratehandler
import string
import errs


REC_LENGTH = 10
WAIT_FOR_DEL_NOT_FOUND = 1800  # 30 min


class Bot:
    def __init__(self, account, reddit_auth, ratehandler):
        self.auth = reddit_auth
        self.acc_info = account
        self.rh = ratehandler
        self.autoreplies = 0
        self.files_to_del = []
        self.last_autoreplied = None
        self.ignore_subs = ["thegoodplace", "fingmemes", "ukrainerussiareport", "familyguy", "hollowknight", "zoomies",
                            "publicfreakout", "namethatsong", "anime", "interestingasfuck", "crazyfuckingvideos",
                            "blackmagicfuckery", "russiaukrainewar2022", "bi_irl", "peoplefuckingdying"]
                            # list of subreddits I know don't allow bots
                            # (u/find-songs will still be responded to through a private message)

    def is_supported(self, word):
        if ("youtu" in word and "https://" in word) or "sndup.net" in word or "streamable.com" in word or "drive.google.com" in word or "twitch.tv" in word or "v.redd.it" in word or "tiktok.com" in word or "vocaroo.com" in word or "voca.ro" in word or "reddit.com" in word or "cdn.discordapp.com" in word:
            return True
        else:
            return False

    def handle_context(self, msg):
        ctx, video_url = None, None
        if msg.was_comment and ("u/" + self.acc_info.user in str(msg.body).lower() or misc.is_single_timestamp(msg)):
            # the bot should only reply to username mentions, or responses to his own comments that are ONLY timestamps
            try:
                if "https://" in str(msg.parent().body) and "https://" not in str(msg.body):
                    # if there's no parent comment it will error out into the except statement
                    # and the message doesn't have a link (links in msg.body should override parent comments)
                    words = str(msg.parent().body).replace("\n", " ").replace(",", " ").split(" ")
                    for word in words:
                        if self.is_supported(word):  # make sure the parent has a compatible link
                            return "link_parent", word
                else:
                    raise AttributeError  # if there's no link in parent comment, go to except statement on line 63
            except AttributeError:  # 'Submission' object has no attribute 'body'
                print(str(msg.body))
                if "https://" in str(msg.body):  # if the original message has a link
                    words = str(msg.body).replace("\n", " ").replace(",", " ").split(" ")
                    for word in words:
                        if "https://" in word and self.is_supported(word):
                            return "link_comment", word
                elif "https://" in str(msg.submission.selftext):
                    # else, assume they want the submission audio, or video from submission text
                    words = str(msg.submission.selftext).replace("\n", " ").replace(",", " ").split(" ")
                    for word in words:
                        if "https://" in word:
                            return "selftxt_link", word
                else:
                    # else, assume they want the submission's video audio
                    video_url = str(msg.submission.url)
                    ctx = "video_submission"
        elif not msg.was_comment:
            try:
                words = str(msg.body).replace("\n", " ").replace(",", " ").split(" ")
                for word in words:
                    if self.is_supported(word):  # make sure the parent has a compatible link
                        return "link_comment", word
                if ctx is None:
                    parent_pm = self.auth.inbox.message(msg.parent_id[3:])  # this gets the first pm in the thread
                    if parent_pm.author == self.acc_info.user:  # check that the bot sent the first message in the pm thread
                        words = str(parent_pm.body).replace("\n", " ").replace(",", " ").split(" ")
                        for word in words:
                            if self.is_supported(word):  # make sure the parent has a compatible link
                                return "link_comment", word
            except TypeError:
                # if an error is raised when trying to retrieve the first PM in the thread (line 77), we know it's a new PM
                if msg.author is not None:
                    # is it sent by a user?
                    words = str(msg.body).replace("\n", " ").replace(",", " ").split(" ")
                    for word in words:
                        if self.is_supported(word):  # make sure the parent has a compatible link
                            return "link_comment", word
                else:
                    # if it's a subreddit message ignore it
                    msg.mark_read()
        if ctx is None or video_url is None:
            try:
                msg.mark_read()
            except:
                pass
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
            print(msg.body, "> check timestamp",  "> no context, skipping")
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
            try:
                for msg in self.auth.inbox.unread():
                    sttime = time.time()
                    try:
                        try:
                            ctx, video_url = self.handle_context(msg)
                            start, to, video_url = self.find_timestamps(msg, video_url)
                        except misc.NoContext:
                            msg.mark_read()
                            continue
                        try:
                            # list of supported link types the bot can process
                            if "reddit.com" in video_url:
                                try:
                                    video_url = misc.convert_reddit_url(video_url)
                                except misc.TooManyReqs:
                                    print("reddit download ratelimit")
                                    reqs.append([video_url, msg, time.time(), start, to, ctx, 0, msg.author,
                                                 msg.subreddit])
                                    msg.mark_read()
                                    continue
                                output_file = misc.download_reddit(video_url)
                            elif "v.redd.it" in video_url:
                                output_file = misc.download_reddit(video_url)
                            elif "twitch.tv" in video_url:
                                output_file = misc.download_twitchclip(video_url)
                            elif "tiktok" in video_url:
                                output_file = misc.download_tiktok(video_url)
                            elif "vocaroo" in video_url or "voca.ro" in video_url:
                                try:
                                    output_file = misc.download_vocaroo(video_url)
                                except misc.LinkTimeout:
                                    raise misc.InvalidLink
                            elif "streamable.com" in video_url:
                                output_file = misc.download_streamable(video_url)
                            elif "cdn.discordapp.com" in video_url:
                                output_file = misc.download_discord(video_url)
                            elif "drive.google.com" in video_url:
                                try:
                                    output_file = misc.download_google(video_url)
                                except misc.LinkTimeout:
                                    raise misc.InvalidLink
                            elif "sndup.net" in video_url:
                                output_file = misc.download_sndup(video_url)
                            elif "youtu" in video_url and "https://" in video_url:
                                try:
                                    output_file = misc.download_yt(video_url)
                                except misc.TooManyReqs:
                                    reqs.append([video_url, msg, time.time(), start, to, ctx, 0, msg.author, msg.subreddit])   # if youtube gives too many reqs error, store videos and context for future reply
                                    msg.mark_read()
                                    continue
                                except misc.VidTooLong:
                                    misc.create_response({"msg": "error", "score": 0}, ctx, video_url, start, to, reply_to=msg)
                                    msg.mark_read()
                                    continue
                            else:
                                msg.mark_read()
                                continue
                            self.queue_del_file(output_file, 600)
                        except misc.InvalidLink:
                            misc.create_response({"msg": "error", "score": 0}, ctx, video_url, start, to, reply_to=msg)
                            msg.mark_read()
                            continue

                        try:
                            data = misc.identify_audio(file=output_file, start_sec=start, end_sec=to, ratehandler=self.rh)
                        except misc.NoValidKey:
                            # if the API keys are exhausted for today, the bot doesn't reply for the rest of the day
                            msg.mark_read()
                            continue
                        print(data)
                        if msg.was_comment:
                            # msg was a comment
                            try:
                                r = misc.create_response(data, ctx, video_url, start, to, reply_to=msg)
                            except:
                                try:
                                    if msg.author != "AutoModerator":
                                        # if automod mentions the bot in a comment and the bot can't reply, don't PM
                                        self.auth.redditor(str(msg.author)).message("I couldn't reply to your comment, here's a PM instead", f"{misc.create_response(data, ctx, video_url, start, to)}\n\n^(This is a response to your ) ^[comment](https://reddit.com/r/{msg.subreddit}/comments/{msg.submission}/comment/{msg.id}) ^(in r/" + str(msg.subreddit) + ")")

                                except:
                                    print(traceback.format_exc())
                        else:
                            # msg was a private message
                            if msg.author != "AutoModerator":
                                msg.reply(misc.create_response(data, ctx, video_url, start, to) + "\n\n^(This is a response to your PM \"" + msg.body + "\")")
                            else:
                                # the message was from reddit automod
                                # the automod never wants to identify a song
                                pass
                        print(time.time() - sttime)
                    except Exception as e:
                        pass
                    msg.mark_read()
            except:
                pass
            try:
                for context in reqs:
                    sttime = time.time()
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
                        except misc.VidTooLong:
                            misc.create_response({"msg": "error", "score": 0}, ctx, video_url, start, to, reply_to=msg)
                            msg.mark_read()
                            continue

                        try:
                            data = misc.identify_audio(file=output_file, start_sec=start, end_sec=to, ratehandler=self.rh)
                        except misc.NoValidKey:
                            # if the API keys are exhausted for today, the bot doesn't reply for the rest of the day
                            msg.mark_read()
                            continue
                        self.queue_del_file(output_file, 600)
                        if msg.was_comment:
                            # msg was a comment
                            try:
                                if msg.subreddit.display_name.lower() not in self.ignore_subs:
                                    r = misc.create_response(data, ctx, video_url, start, to, reply_to=msg)
                                else:
                                    # I chose to explicitly have the bot not comment in certain subreddits that I know don't allow bots
                                    raise errs.Banned  # pm instead
                            except:
                                try:
                                    self.auth.redditor(str(msg.author)).message("I couldn't reply to your comment, here's a PM instead", f"{misc.create_response(data, ctx, video_url, start, to)}\n\n^(This is a response to your ) ^[comment](https://reddit.com/r/{msg.subreddit}/comments/{msg.submission}/comment/{msg.id}) ^(in r/" + str(msg.subreddit) + ")")
                                except:
                                    pass
                        else:
                            # msg was a PM
                            if msg.author != "AutoModerator":
                                msg.reply(misc.create_response(data, ctx, video_url, start, to) + "\n\n^(This is a response to your PM \"" + msg.body + "\")")
                            else:
                                # the message was from reddit automod
                                # the automod never wants to identify a song
                                pass
            except:
                pass  # so graceful

    def auto_reply(self):  # auto-reply to comments in r/all
        clist = []
        while True:
            try:
                s = self.auth.subreddit('all').comments()
                for c in s:
                    if c.id == self.last_autoreplied or c.author == self.acc_info.user:
                        continue
                    clist.append(c)
                for c in clist:
                    clist.remove(c)
                    body_lower = str(c.body).lower()
                    reply_bool = False
                    for i in range(len(self.acc_info.activators)):
                        # does this comment contain "what's this song" etc.
                        if self.acc_info.activators[i] in body_lower:
                            reply_bool = True
                            break
                    if reply_bool:
                        surl = c.submission.url
                        invalid = False
                        try:
                            supported, output_file = misc.download_video(surl)
                            self.queue_del_file(output_file, 600)
                        except (misc.InvalidLink, misc.VidTooLong):
                            invalid = True
                            supported, output_file = 0, None
                        try:
                            start_sec = misc.get_yt_link_time(surl)
                            end = start_sec + REC_LENGTH
                        except:
                            try:
                                start_sec, end, _ = self.find_timestamps(c.body, "")
                                print("start_sec, end:", start_sec, end)
                            except:
                                start_sec, end = 0, REC_LENGTH
                        if invalid:
                            if body_lower == "u/findsong" or body_lower == "u/find song" or c.body == "U/find-song":
                                # did the user explicitly call the bot in a format that isn't a "mention"?
                                misc.create_response({"msg": "error", "score": 0}, "autoreply", surl, start_sec, end, reply_to=c)
                            continue  # skip identifing the audio no matter what
                        if supported == 1:
                            # choose which acr key to use
                            try:
                                data = misc.identify_audio(file=output_file, start_sec=start_sec, end_sec=end, ratehandler=self.rh)
                            except misc.NoValidKey:
                                # if all provided API keys are exhausted for today
                                continue
                            print(c.subreddit, ">", c.author, ">", c.body)
                            print(data)
                            self.autoreplies += 1
                            if data['score'] >= 90 or c.body.lower() == "u/findsong" or c.body.lower() == "u/find song" or c.body == "U/find-song":
                                # any variation of u/findsong (and any capitalization of it) will override needing specific score
                                # this if will only check the case where the 'U/' is uppercase since that does not trigger a "mention"
                                if c.subreddit.display_name.lower() not in self.ignore_subs:
                                    re = misc.create_response(data, "autoreply", surl, start_sec, start_sec + REC_LENGTH, reply_to=c)
                                elif c.body.lower() == "u/findsong" or c.body.lower() == "u/find song" or c.body == "U/find-song":
                                    re = misc.create_response(data, "autoreply", surl, start_sec, start_sec + REC_LENGTH)
                                    print("pming", c.author, "on", c.submission)
                                    self.auth.redditor(str(c.author)).message(
                                        "I couldn't reply to your comment, here's a PM instead",
                                        f"{re}\n\n^(This is a response to your ) ^[comment](https://reddit.com/r/{c.subreddit}/comments/{c.submission}/comment/{c.id}) ^(in r/" + str(
                                            c.subreddit) + ")")
                                self.last_autoreplied = c.id
                            else:
                                continue  # the confidence score was too low to reply automatically
                        else:
                            continue  # if video type isn't supported, don't reply
            except:
                print(traceback.format_exc())
                pass

    @staticmethod
    def queue_del_file(self, filepath, how_long_to_wait):
        print(f"\nadded {filepath} to be deleted")
        with open("delfiles.txt", 'a') as f:
            f.write(str(filepath) + "\n")


def main():
    # Ratehandler keeps track of all the different keys used for the song fingerprint API
    # (each key allows 100 requests per day)
    rate = Ratehandler(100, "ratehandler.txt").load_key_reqs("saved_reqs.txt")
    print(rate.KEYS)
    bot = Bot(account=misc.cf, reddit_auth=misc.authenticate(), ratehandler=rate)
    with concurrent.futures.ProcessPoolExecutor() as proc:
        mentions_proc = proc.submit(bot.mentions_reply)
        auto_proc = proc.submit(bot.auto_reply)


if __name__ == '__main__':
    main()
