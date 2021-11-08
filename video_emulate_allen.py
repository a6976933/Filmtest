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

logFile = None

def record2File(text):
    logFile.write(text)
    logFile.flush()

def command_parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', '-p', type=str, required=True, help='video document path')
    return parser.parse_args()

def bWDecreaseTest(childPipe, startBW=10, amount=1, interval=10):
    bandwidth = startBW
    adjustNetworkEnv(defaultBW=bandwidth)
    childPipe.sned("bw start")
    interval = interval
    start = time.time()
    while True:
        if childPipe.poll():
            if childPipe.recv() == "End":
                adjustNetworkEnv(stop=True)
                break
        end = time.time()
        if end-start >= interval:
            bandwidth -= amount
            adjustNetworkEnv(targetBW=bandwidth)

def latencyIncreaseTest(childPipe, amount=100, interval=10):
    latency = 0
    childPipe.send("lat start")
    interval = interval
    start = time.time()
    while True:
        if childPipe.poll():
            if childPipe.recv() == "End":
                adjustNetworkEnv(stop=True)
                break
        end = time.time()
        if end-start >= interval:
            latency += amount
            adjustNetworkEnv(latency=latency)

def packetLossIncreaseTest(childPipe, amount=0.02, interval=10):
    packetLoss = 0
    childPipe.send("pl start")
    interval = interval
    start = time.time()
    while True:
        if childPipe.poll():
            if childPipe.recv() == "End":
                adjustNetworkEnv(stop=True)
                break
        end = time.time()
        if end-start >= interval:
            packetLoss += amount
            adjustNetworkEnv(packetLoss=packetLoss)

#def networkEnvTest(childPipe, mode):



def adjustNetworkEnv(latency=-1, packetLoss=-1, targetBW=-1, defaultBW=-1, stop=False):
    comcastCmd = "sudo comcast --device=en0"
    if(latency != -1):
        comcastCmd += " --latency="+str(latency)
    if(packetLoss != -1):
        comcastCmd += " --packet-loss="+str(packetLoss)
    if(targetBW != -1):
        comcastCmd += " --target-bw="+str(targetBW)
    if(defaultBW != -1):
        comcastCmd += " --default-bw="+str(defaultBW)
    if(stop):
        comcastCmd = "comcast --device=en0 --stop"
    subprocess.Popen(comcastCmd.split(' '), stdin=subprocess.PIPE, stdout=subprocess.PIPE)

def openVLC(command):
    subprocess.run(command, shell=True)

def openRTSPServer(command):
    #subprocess.run(command, shell=True)
    proc = subprocess.Popen(command, stdout=subprocess.PIPE)
    while True:
        print("-------------------------------------------")
        line = proc.stdout.readline().decode().split(' ')
        print(len(line))
        print(line)
        if(len(line) == 8):
            if(line[5] == 'runOnDemand' and line[6] == 'command' and line[7] == 'stopped'):
                print("KILL THE PROCESS")
                proc.kill()
                return
    
def streaming(input_path, output_path, mode, rate, delay, delay_jitter, loss, fps):
    print('Start simulation')
    # os.system("sudo tc qdisc del dev lo root")
    # os.system("sudo tc qdisc add dev lo root handle 1:0 tbf rate "+rate+"kbit buffer 200000 limit 200000")
    # os.system("sudo tc qdisc add dev lo parent 1:1 handle 2:0 netem delay "+delay+"ms "+delay_jitter+"ms distribution normal loss "+loss+"%")
    # os.system("vlc "+input_path+" --no-video-title --play-and-exit --quiet :sout=#transcode{vcodec=h264}:rtp{sdp=rtsp://:8554/} :sout--all :sout-keep :file-caching=1000 &")
    # time.sleep(0.5)
    # os.system("ffmpeg -i rtsp://127.0.0.1:8554/ -codec copy -r "+ fps +" "+ output_path)
    '''
    parent_conn, child_conn = Pipe()
    simulation = Process(target=networkSimulate, args=(child_conn, mode, rate, delay, delay_jitter, loss)) --no-video-title
    simulation.start()
    '''
    #if parent_conn.recv() == 'Success':


    s = "vlc "+input_path+"  --play-and-exit --quiet :sout=#rtp{sdp=rtsp://:8554/} :sout--all :sout-keep"
    vlcProc = Process(target=openVLC, args=(s, ))
    vlcProc.start()
    time.sleep(1)

    s = "ffmpeg -i rtsp://127.0.0.1:8554/ -codec copy -r "+fps+" "+output_path
    subprocess.run(s.split())
    #time.sleep(0.5)
    #s = "/Users/allenwang/ffmpeg/ffmpeg -hide_banner -loglevel panic -i rtsp://@127.0.0.1:8554/ -codec copy "+output_path /"+input_path+" "+input_path+"
    #"/Users/allenwang/ffmpeg/ffmpeg -hide_banner -loglevel panic -i rtsp://127.0.0.1:8554/ -codec copy -r "+ fps +" "+ output_path
    #subprocess.run(s.split())
    #elif parent_conn.recv() == 'Fail':
    #    return
    # os.system("vlc rtsp://127.0.0.1:9000/ --network-caching=20000 --rtsp-frame-buffer-size=1000000 --sout=file/ts:"+output_path+" --play-and-exit --quiet")
    #/Users/allenwang/ffmpeg/ffmpeg -hide_banner -loglevel panic -i rtsp://127.0.0.1:8554/ -codec copy -r 30 /Users/allenwang/filmtest/output/
    #vlc -vvv 655381338.945520.mp4 --sout '#rtp{dst=127.0.0.1,port=8554,sdp=rtsp://:8554/}'
    #/Users/allenwang/ffmpeg/ffmpeg -i rtsp://@127.0.0.1:8554/ -codec copy /Users/allenwang/filmtest/output/testtest.mp4
    #vlc -vvv rtsp://127.0.0.1:8554/live --sout="#transcode{vcodec=h264}:std{access=file,mux=mp4,dst=/Users/allenwang/filmtest/output/test1.mp4}"
    vlcProc.join()
    print('Simulatioin done.')
    #parent_conn.send('End')
    return


if __name__ == "__main__":
    args = command_parse()
    fileList = os.listdir(args.path)
    logFile = open(datetime.strftime(datetime.now(), '%Y%m%d%H%M%S')+".txt", "w+")
    for filename in fileList:
        if(isfile(filename) and filename[-4:] == '.mp4'):
            filepath = join(args.path, filename)
            print(filepath)
            outputPath = join(args.path, "output", filename[:-4]+'.mp4')
            print(outputPath)
            streaming(filepath, outputPath, 0, 0, 0, 0, 0, '30')
    logFile.close()

