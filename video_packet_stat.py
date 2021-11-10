import os
import argparse
import time
#import numpy as np
import logging
import subprocess
from datetime import datetime
from multiprocessing import Process, Lock, Pipe
from os.path import isfile, isdir, join
import random

def openVLC():
    s = "vlc test.mp4  --play-and-exit --quiet :sout=#rtp{sdp=rtsp://:8554/} :sout--all :sout-keep"
    subprocess.run(s.split())

def openpcap():
    pass
s = "sudo lsof -i -P -n | grep vlc"
proc = subprocess.Popen(s.split(), stdout=subprocess.PIPE)
while True:
    line = proc.stdout.readline().decode().split()
    print(line)
    print(line[9])
    

#s = "ffmpeg -i rtsp://127.0.0.1:8554-codec copy -r 30 /home/mvnl/output/abc.mp4"
#subprocess.run(s.split())


