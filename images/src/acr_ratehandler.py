from datetime import datetime
import time
import json


class KeynameNotFound(Exception):
    pass


class Ratehandler:
    """Provides a cap for the amount of API requests the bot can make to the audio fingerprint API"""
    def __init__(self, max_req: int, reset_file: str):
        """:param keys [{"name": str, "key": str, "secret": str, "host": str}, ...]
        :param max_req how many requests are allowed per day
        :param reset_file the file storing the datetime value when the rate was last reset"""
        self.DATETIME_RESET = None
        self.KEYS = None
        self.save_reqs_here = None
        self.MAX_REQUESTS = max_req
        self.RATE_FILE = reset_file

    def reset_time(self) -> float:
        """Write the current date into self.RATE_FILE"""
        t = time.time()
        with open(self.RATE_FILE, "w") as rf:
            rf.write(str(t))
        self.DATETIME_RESET = self.DATETIME_RESET = datetime.fromtimestamp(t)
        print("ACR Ratehandler: Time Reset!")
        self.reset_key_reqs()
        return t

    def load_time(self) -> 'Ratehandler':
        """Try to load self.DATETIME_RESET from self.RATE_FILE, if it exists"""
        with open(self.RATE_FILE, "r") as rf:
            self.DATETIME_RESET = datetime.fromtimestamp(float(rf.read()))
        return self

    def load_key_reqs(self, filepath):
        """Load key req values from file (different file than where time is stored)"""
        self.load_time()
        self.save_reqs_here = filepath
        with open(self.save_reqs_here, "r") as rf:
            self.KEYS = json.loads(rf.read())
        return self

    def save_key_reqs(self):
        with open(self.save_reqs_here, "w") as rf:
            json.dump(self.KEYS, rf)

    def reset_key_reqs(self) -> [dict]:
        """Reset the number of requests performed by each key"""
        for k in self.KEYS:
            k["reqs"] = 0  # reset each key's num of requests to 0
            # this will also create the 'reqs' attribute for each key's dict if it wasn't created yet
        self.save_key_reqs()
        print("ACR Ratehandler: Keys Reset!")
        return self.KEYS

    def add_req_to_key(self, search_key: str, num: int = 1) -> int:
        """:param search_key the key to change
        :param num how much to add to its requests"""
        for k in self.KEYS:
            if k["key"] == search_key:
                k["reqs"] += num
                self.save_key_reqs()
                return k["reqs"]
        raise KeynameNotFound

    def has_day_passed(self, other_time: float):
        """is self.DATETIME_RESET.date() < datetime(other_time).date()?"""
        b = datetime.fromtimestamp(other_time).date() > self.DATETIME_RESET.date()
        if b:
            print("ACR Ratehandler: Day has passed!")
            self.reset_time()
        return b
