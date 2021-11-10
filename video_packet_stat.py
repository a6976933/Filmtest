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
    s = "vlc /home/mvnl/Filmtest/test.mp4 --play-and-exit :sout='#rtp{sdp=rtsp://:8554/}' :sout--all :sout-keep"
    subprocess.run(s.split(), shell=True)

def opentcpdump(pipe, cmd):
    proc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    while True:
        if pipe.poll():
            if pipe.recv() == "End":
                proc.kill()

def opendump(ppp1):
    s = "sudo lsof -i -P -n"
    proc1 = subprocess.Popen(s.split(), stdout=subprocess.PIPE)
    proc2 = subprocess.Popen(["grep", "vlc"], stdin=proc1.stdout, stdout=subprocess.PIPE)
    proc1.stdout.close()
    sendportnum = []
    recvportnum = []
    while True:
        line = proc2.stdout.readline().decode().split()
        if(len(line) >= 9):
            newline = line[8].split('->')
            if(len(newline) >= 2):
                if(int(newline[0][10:]) != 8554):
                    sendportnum.append(int(newline[0][10:]))
                    if(len(sendportnum) > 1):
                        break
    s = "sudo lsof -i -P -n"
    proc1 = subprocess.Popen(s.split(), stdout=subprocess.PIPE)
    proc2 = subprocess.Popen(["grep", "ffmpeg"], stdin=proc1.stdout, stdout=subprocess.PIPE)
    proc1.stdout.close()
    while True:
        line = proc2.stdout.readline().decode().split()
        if(len(line) >= 9):
            if(line[7] == "UDP"):
                recvportnum.append(int(line[8].split(":")[1]))
                if(len(recvportnum) > 3):
                    break
    p1, cp1 = Pipe()
    p2, cp2 = Pipe()
    s = "sudo tcpdump -i lo "
    sdrcmd = s
    rcvcmd = s
    for k in sendportnum:
        sdrcmd += "port "+str(k)+" "
    sdrcmd += "-w sender.pcap"
    for k in recvportnum:
        rcvcmd += "port "+str(k)+" "
    rcvcmd += "-w receiver.pcap"
    tp1 = Process(target=opentcpdump, args=(cp1, sdrcmd, ))
    tp2 = Process(target=opentcpdump, args=(cp2, rcvcmd, ))
    tp1.start()
    tp2.start()
    while True:
        if ppp1.poll():
            if ppp1.recv() == "End":
                p1.send("End")
                p2.send("End")


pp1, cpp1 = Pipe()
#vlcp = Process(target=openVLC)
#vlcp.start()
#time.sleep(3)
#s = "ffmpeg -i rtsp://127.0.0.1:8554/ -codec copy /home/mvnl/Filmtest/output/abc.mp4"
#subprocess.run(s.split())
opendump(cpp1)
#pp1.send("End")
