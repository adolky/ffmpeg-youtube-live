#!/usr/bin/env python3
"""
Test script to demonstrate the encoder detection functionality.
This script will show which encoders are available and which one is selected as best.

Run with: python test_encoder_detection.py
"""

import sys
sys.path.append('.')

try:
    from youtubelive_ffmpeg import _detect_available_encoders, _find_best_encoder
    import logging
    
    # Enable logging to see the encoder selection process
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("GPU Encoder Detection Test")
    print("=" * 40)
    
    print("\n1. Detecting available encoders...")
    available_encoders = _detect_available_encoders()
    print(f"Found {len(available_encoders)} H.264 encoders:")
    for encoder in available_encoders:
        print(f"  - {encoder}")
    
    print("\n2. Testing encoder performance and selecting best...")
    best_encoder, best_preset = _find_best_encoder()
    
    print(f"\n3. Selected encoder: {best_encoder}")
    print(f"   Preset settings: {' '.join(best_preset)}")
    
    if best_encoder != 'libx264':
        print("   Type: GPU accelerated ✓")
    else:
        print("   Type: CPU (no GPU encoders available)")
    
    print("\n4. Example FFmpeg command that would be generated:")
    example_cmd = [
        'ffmpeg', '-re', '-stream_loop', '-1', '-i', 'video.mp4', '-ac', '2',
        '-c:v', best_encoder, '-pix_fmt', 'yuv420p'
    ] + best_preset + [
        '-b:v', '3000k', '-g', '60', '-c:a', 'aac', '-b:a', '160k', '-ar', '44100',
        '-threads', '0', '-maxrate', '3000k', '-bufsize', '6000k', '-f', 'flv',
        'rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY'
    ]
    
    print(' '.join(example_cmd))
    
except FileNotFoundError as e:
    print(f"FFmpeg not found: {e}")
    print("\nThis is expected if FFmpeg is not installed.")
    print("Install FFmpeg to test the encoder detection functionality.")
except Exception as e:
    print(f"Error: {e}")