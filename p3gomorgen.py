#!/usr/bin/env python
from datetime import datetime
import urllib2
import json
import locale
import cmd
import sys
import vlc


FEED_URL = "http://www.dr.dk/mu/Feed/urn:dr:mu:bundle:4f3b8a2a860d9a33ccfdb3a6"
API_URL = "http://www.dr.dk/mu/programcard/expanded?id=go-morgen-p3-"


# change locale for parsing RSS feed dates
#locale.setlocale(locale.LC_TIME, ('en_US', 'UFT-8'))


def parse_date(s):
    cur = datetime.now()
    opts = [cur.day, cur.month, cur.year]
    if len(s.strip()) > 0:
        for i, x in enumerate(s.split('-')):
            t = int(x)
            opts[i] = t
    return datetime(opts[2], opts[1], opts[0])


def get_number(date):
    global FEED_URL
    feed = urllib2.urlopen(FEED_URL).read()

    # Coarse parsing file to, maybe, avoid XML attacks

    # truncate everything before actual items
    feed = feed[feed.find("<item>"):]
    # search for date
    date_idx = feed.find(date.strftime("%d %b %Y"))
    if date_idx < 0:
        print("Could not find date in DRs feed. Maybe its still live? Or try later. Quitting now")
        sys.exit(0)
    # search for url just before that
    url_idx = feed.rfind("<link>", 0, date_idx)
    # extract url
    url = feed[url_idx + 6:feed.find("</link>", url_idx, date_idx)]
    print("Extracted this DR P3 Live Radio Player URL: %s" % url)
    
    # return last number in this url
    return url.split('-')[-1]


def retrieve_url(date):
    global API_URL
    number = get_number(date)
    url = API_URL + str(number)
    print("Querying the DR MU: {}".format(url))
    data = urllib2.urlopen(url).read()
    obj = json.loads(data)
    actualDate = obj['Data'][0]["PrimaryBroadcastStartTime"] 
    prize = obj['Data'][0]["Assets"][0]['Links'][-1]['Uri']
    return (actualDate, prize)


def get_player(url):
    mp = vlc.MediaPlayer(url)
    return mp


class CLI(cmd.Cmd):
    prompt = "(stopped) > "
    def __init__(self, mp):
        cmd.Cmd.__init__(self)
        self._mp = mp
        
    def do_play(self, line):
        self._mp.play()
        self.prompt = "(playing) > "
        
    def do_pause(self, line):
        self._mp.pause()
        self.prompt = "(paused) > "

    def do_seek(self, line):
        self._mp.set_position(int(line) / 100.0)
        
    def do_quit(self, line):
        self._mp.stop()
        sys.exit(0)

    def do_EOF(self, line):
        return True


if __name__ == "__main__":
    import sys
    usage = """
    usage: ./p3gomorgen.py [date]

    data - ex: '29' (automagic this month), '29-10' (automagic this year), etc.
           Defaults to 'most recent' broadcast.

    Player commands:
    play
    pause
    quit
    seek [pct: 0-100]
    
    """
    arg = ''
    if len(sys.argv) > 1:
        arg = sys.argv[1]
    date = parse_date(arg)
    streamDate, media_url = retrieve_url(date)
    mp = get_player(media_url)
    cli = CLI(mp)
    cli.onecmd("play")
    cli.cmdloop("Loaded %s from \n %s\n\n%s" % (media_url, streamDate, usage))
