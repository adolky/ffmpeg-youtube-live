#!/usr/bin/env python
"""
LIVE STREAM TO YOUTUBE LIVE using FFMPEG -- screenshare

https://www.scivision.co/youtube-live-ffmpeg-livestream/
https://support.google.com/youtube/answer/2853702

Windows: get DirectShow device list from:
   ffmpeg -list_devices true -f dshow -i dummy
"""
from youtubelive_ffmpeg import youtubelive
import sys
#
if sys.platform.startswith('win'):
    audiochan = 'audio="Internal Microphone"'
    videochan = 'video="UScreenCapture"'
elif sys.platform.startswith('darwin'):
    audiochan = 'default'
    videochan = 'default'
elif sys.platform.startswith('linux'):
    audiochan = 'default'
    videochan = '/dev/video0'


if __name__ == '__main__':
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('-fps',default=10,type=int)
    p.add_argument('-res',default='1024x720')
    p.add_argument('-o','--origin',help='x,y coordinates of upper-left hand capture area (pixel)',
                   nargs=2,type=int,default=[0,0])
    p.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging to see encoder selection process')
    p = p.parse_args()

    P = {'fps': p.fps,
         'res': p.res,
         'origin':p.origin,
         'videochan': videochan,
         'audiochan': audiochan,
         'vidsource': 'screen',
         'verbose': p.verbose,
            }

    youtubelive(P)
