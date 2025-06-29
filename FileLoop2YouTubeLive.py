#!/usr/bin/env python
"""
LIVE STREAM TO YOUTUBE LIVE using FFMPEG -- Looping input file endlessly

https://www.scivision.co/youtube-live-ffmpeg-livestream/
https://support.google.com/youtube/answer/2853702
"""
from youtubelive_ffmpeg import youtubelive

if __name__ == '__main__':
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('filein',help='file to loop endlessly to YouTube Live.  Keep in mind copyright and TOS!')
    p.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging to see encoder selection process')
    p = p.parse_args()

    P = {'filein': p.filein,
         'vidsource': 'file',
         'loop':True,
         'verbose': p.verbose,
            }

    youtubelive(P)
