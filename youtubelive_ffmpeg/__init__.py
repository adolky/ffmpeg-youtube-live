from pathlib import Path
from getpass import getpass
import subprocess as sp
from sys import platform
import logging,os
import time
# %%
try:
    sp.check_call(('ffmpeg','-h'), stdout=sp.DEVNULL, stderr=sp.DEVNULL)
    FFMPEG = 'ffmpeg'
except FileNotFoundError:
    try:
        sp.check_call(('avconv','-h'), stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        FFMPEG = 'avconv'
    except FileNotFoundError:
        raise FileNotFoundError('FFmpeg program is not found. Is ffmpeg on your PATH?')
# %% https://trac.ffmpeg.org/wiki/Capture/Desktop
if platform.startswith('linux'):
    if 'XDG_SESSION_TYPE' in os.environ and os.environ['XDG_SESSION_TYPE'] == 'wayland':
        logging.error('Wayland may only give black output with cursor. Login with X11 desktop')
    vcap = 'x11grab'
    acap = 'pulse'
# v4l2-ctl --list-devices
    hcam = 'v4l2'
elif platform.startswith('darwin'):
    vcap = 'avfoundation'
    acap = '0:0'  # determine from ffmpeg -f avfoundation -list_devices true -i ""
  # ffmpeg -f avfoundation -list_devices true -i ""
    hcam = 'avfoundation'
elif platform.startswith('win'):
    vcap = 'dshow'
    hvcap = 'video="UScreenCapture"'
    acap = 'dshow'
    # ffmpeg -list_devices true -f dshow -i dummy
    hcam = 'dshow'
else:
    raise ValueError(f'not sure which operating system you are using {platform}')

# %% minimum bitrates specified by YouTube. Key is vertical pixels (height)
br30 = {'2160':13000,
        '1440':6000,
        '1080':3000,
        '720':1500,
        '480':500,
        '360':400,
        '240':300,
        }

br60 = {'2160':20000,
        '1440':9000,
        '1080':4500,
        '720':2250,
        }


COMPPRESET='veryfast'

# Global variables for best encoder
BEST_ENCODER = None
BEST_ENCODER_PRESET = None

# %% video
def _videostream(P:dict) -> tuple:
    """optimizes video settings for YouTube Live"""
# %% configure video input
    if P['vidsource'] == 'screen':
        vid1 = _screengrab(P)
    elif P['vidsource'].startswith('cam'):
        vid1 = _webcam(P)
    elif P['vidsource'] == 'file':
        vid1 = _filein(P)
    else:
        raise ValueError(f'unknown vidsource {P["vidsource"]}')
# %% configure video output
    cvbr = _bitrate(P)

    # Get the best available encoder
    best_encoder, best_preset = _find_best_encoder()
    
    vid2 = ['-c:v', best_encoder, '-pix_fmt', 'yuv420p']

    if 'image' in P and P['image']:
        vid2 += ['-tune','stillimage']
    else:
        vid2 += best_preset + [
                '-b:v',str(cvbr)+'k',
                '-g',_group(P)]


    return vid1, vid2, cvbr


def _group(P:dict) -> str:

    if 'fps' in P:
        g = str(2*P['fps'])
    else: # TODO assume 30 fps
        g = '60'

    return g


def _bitrate(P:dict) -> list:
    if 'image' in P and P['image']:
        return

    if P['vidsource'] == 'file': # TODO get from input file
        return 3000
# %%
    if 'res' in P:
        y = P['res'].split('x')[1]

        if P['fps'] <= 30:
           cvbr = br30[y]
        else:
           cvbr = br60[y]
    else:  # TODO assuming 720 webcam for now
        if P['fps'] <= 30:
            cvbr = br30['720']
        else:
            cvbr = br60['720']

    return cvbr


def _screengrab(P:dict) -> list:
    """choose to grab video from desktop. May not work for Wayland."""
    vid1 = ['-f', vcap,
            '-r',str(P['fps']),
            '-s',P['res']]

    if platform.startswith('linux'):
        vid1 += ['-i',f':0.0+{P["origin"][0]},{P["origin"][1]}']
    elif platform.startswith('win'):
        vid1 += ['-i',P['videochan']]
    elif platform.startswith('darwin'):
        pass  # FIXME: verify

    return vid1


def _webcam(P:dict) -> list:
    """configure webcam"""
    vid1 = ['-f',hcam,
            '-r',str(P['fps']),
            '-i',P['videochan']]

    return vid1


def _filein(P:dict) -> list:
    """file input"""
    fn = Path(P['filein']).expanduser()

    if 'image' in P and P['image']:
        vid1 = ['-loop','1']
    else:
        vid1 = ['-re']



    if 'loop' in P and P['loop']:
        vid1 += ['-stream_loop','-1']  # FFmpeg >= 3
    else:
        vid1 += []

    if 'image' in P and P['image']: # still image, typically used with audio-only input files
        vid1 += ['-i',str(P['image'])]


    vid1 += ['-i',str(fn)]

    return vid1


# %% audio
def _audiostream(P:dict) -> list:
    """
    -ac 2 NOT -ac 1 to avoid "non monotonous DTS in output stream" errors
    """
    if not P['vidsource'] == 'file':
        return ['-f',acap, '-ac','2', '-i', P['audiochan']]
    else: #  file input
        return ['-ac','2']


def _audiocomp(P:dict) -> list:
    """select audio codec"""
    return ['-c:a','aac','-b:a','160k','-ar','44100' ]


def _buffer(P:dict,cvbr:int) -> list:
    buf = ['-threads','0']

    if not 'image' in P or not P['image']:
        buf += ['-maxrate','{}k'.format(cvbr),
                  '-bufsize','{}k'.format(2*cvbr)]
    else: # static image + audio
        buf += ['-shortest']

    buf += ['-f','flv']

    return buf


def _detect_available_encoders():
    """Detect available H.264 encoders on the system"""
    try:
        if platform.startswith('win'):
            result = sp.run([FFMPEG, '-encoders'], capture_output=True, text=True)
            encoders = []
            for line in result.stdout.split('\n'):
                if 'h264' in line.lower():
                    encoders.append(line.strip())
        else:
            result = sp.run([FFMPEG, '-encoders'], capture_output=True, text=True)
            encoders = []
            for line in result.stdout.split('\n'):
                if 'h264' in line.lower():
                    encoders.append(line.strip())
        return encoders
    except Exception as e:
        logging.warning(f"Could not detect available encoders: {e}")
        return []


def _test_encoder_performance(encoder, preset_args):
    """Test encoder performance with a 10-second test video"""
    test_cmd = [
        FFMPEG, '-f', 'lavfi', '-i', 'testsrc=duration=10:size=1920x1080:rate=30',
        '-c:v', encoder
    ] + preset_args + [
        '-b:v', '3000k', '-f', 'null', '-'
    ]
    
    try:
        start_time = time.time()
        result = sp.run(test_cmd, capture_output=True, text=True, timeout=30)
        end_time = time.time()
        
        if result.returncode == 0:
            encode_time = end_time - start_time
            logging.info(f"Encoder {encoder} completed test in {encode_time:.2f}s")
            return encode_time
        else:
            logging.warning(f"Encoder {encoder} failed test: {result.stderr}")
            return None
    except sp.TimeoutExpired:
        logging.warning(f"Encoder {encoder} test timed out")
        return None
    except Exception as e:
        logging.warning(f"Error testing encoder {encoder}: {e}")
        return None


def _find_best_encoder():
    """Find and test the best available GPU encoder"""
    global BEST_ENCODER, BEST_ENCODER_PRESET
    
    if BEST_ENCODER is not None:
        return BEST_ENCODER, BEST_ENCODER_PRESET
    
    # Define encoder priorities and their settings
    encoders_to_test = [
        ('h264_nvenc', ['-preset', 'fast']),           # NVIDIA GPU
        ('h264_amf', ['-usage', 'ultralowlatency']),   # AMD GPU  
        ('h264_qsv', ['-preset', 'fast']),             # Intel GPU
        ('h264_videotoolbox', ['-preset', 'fast']),    # macOS hardware
        ('libx264', ['-preset', 'veryfast'])           # CPU fallback
    ]
    
    best_encoder = 'libx264'
    best_preset = ['-preset', 'veryfast']
    best_time = float('inf')
    
    logging.info("Testing available encoders for best performance...")
    
    for encoder, preset_args in encoders_to_test:
        logging.info(f"Testing encoder: {encoder}")
        encode_time = _test_encoder_performance(encoder, preset_args)
        
        if encode_time is not None and encode_time < best_time:
            best_time = encode_time
            best_encoder = encoder
            best_preset = preset_args
            logging.info(f"New best encoder: {encoder} ({encode_time:.2f}s)")
    
    # Cache the result
    BEST_ENCODER = best_encoder
    BEST_ENCODER_PRESET = best_preset
    
    if best_encoder != 'libx264':
        logging.info(f"Using GPU encoder: {best_encoder}")
    else:
        logging.info("Using CPU encoder: libx264 (no GPU encoder available)")
    
    return best_encoder, best_preset

# %% top-level
def youtubelive(P:dict):
    """LIVE STREAM to YouTube Live"""
    
    # Enable logging if requested
    if P.get('verbose', False):
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    vid1,vid2,cvbr = _videostream(P)

    aud1 = _audiostream(P)
    aud2 = _audiocomp(P)

    buf = _buffer(P,cvbr)

    cmd = [FFMPEG] + vid1 + aud1 + vid2 + aud2 + buf

    # Show which encoder is being used
    encoder_info = f"Using encoder: {BEST_ENCODER}"
    if BEST_ENCODER != 'libx264':
        encoder_info += " (GPU accelerated)"
    else:
        encoder_info += " (CPU)"
    print(f"\n{encoder_info}")
    print('\n',' '.join(cmd),'\n')

    if 'streamid' in P: # for loop case
        streamid = P['streamid']
    else:
        streamid = getpass('YouTube Live Stream ID: ')

    sp.check_call(cmd+['rtmp://a.rtmp.youtube.com/live2/' + streamid],
                stdout=sp.DEVNULL)


def disksave4youtube(P:dict, outfn:Path=None):
    """
    records to disk screen capture with audio for upload to YouTube

    if not outfn, just cite command that would have run
    """
    if outfn:
        outfn = Path(outfn).expanduser()

    vid1 = _screengrab(P)

    aud1 = _audiostream(P)
    aud2 = _audiocomp(P)

    cmd = [FFMPEG] + vid1 + aud1 + aud2
    if platform.startswith('win'):
        cmd += ['-copy_ts']

    print('\n',' '.join(cmd),'\n')

    if outfn:
        sp.check_call(cmd + [str(outfn)])
    else:
        print('specify filename to save screen capture with audio to disk.')

