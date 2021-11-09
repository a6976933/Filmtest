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
mode = ""

def getNowFormatTime():
    return datetime.strftime(datetime.now(), "%Y-%m-%d-%H:%M:%S")

def record2File(text, logFile):
    logFile.write(getNowFormatTime()+" "+text+'\n')
    logFile.flush()

def command_parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', '-p', type=str, required=True, help='video document path')
    return parser.parse_args()

def bWDecreaseTest(childPipe, startBW=10000, amount=0.8, interval=2):
    bandwidth = startBW
    #adjustNetworkEnvBw(bw=bandwidth)
    logFile = open(datetime.strftime(datetime.now(), '%Y%m%d%H%M%S')+".txt", "w+")
    childPipe.send("bw start")
    record2File("start simulation", logFile)
    interval = interval
    start = time.time()
    while True:
        if childPipe.poll():
            if childPipe.recv() == "End":
                adjustNetworkEnvBw(stop=True)
                break
        end = time.time()
        if end-start >= interval:
            bandwidth *= amount
            start = end
            record2File("bandwidth increase to "+str(bandwidth)+" kbps", logFile)
            adjustNetworkEnvBw(bw=bandwidth)

def latencyIncreaseTest(childPipe, amount=200, interval=4):
    latency = 0
    childPipe.send("lat start")
    logFile = open(datetime.strftime(datetime.now(), '%Y%m%d%H%M%S')+".txt", "w+")
    record2File("start simulation", logFile)
    interval = interval
    start = time.time()
    print(start)
    while True:
        if childPipe.poll():
            if childPipe.recv() == "End":
                adjustNetworkEnvLat(stop=True)
                break
        end = time.time()
        #print(end-start)
        if end-start >= interval:
            start = end
            latency += amount
            record2File("latency increase to "+str(latency)+" ms", logFile)
            print("latency increase to "+str(latency)+" ms")
            adjustNetworkEnvLat(latency=latency)
            #adjustNetworkEnvLat(jitter=latency/2)

def packetLossIncreaseTest(childPipe, amount=0.02, interval=10):
    packetLoss = 0
    childPipe.send("pl start")
    interval = interval
    start = time.time()
    while True:
        if childPipe.poll():
            if childPipe.recv() == "End":
                adjustNetworkEnvLat(stop=True)
                break
        end = time.time()
        if end-start >= interval:
            packetLoss += amount
            adjustNetworkEnvLat(packetLoss=packetLoss)

def adjustNetworkEnvBw(bw=-1, stop=False, mode="ubuntu"):
    if mode == 'ubuntu':
        if stop:
            return
        netemCmd = "sudo tc qdisc change dev lo root handle 1:0 tbf rate "+str(bw)+"kbit buffer 200000 limit 200000"
        subprocess.run(netemCmd.split(' '))
        return


def adjustNetworkEnvLat(latency=-1, packetLoss=-1, targetBW=-1, defaultBW=-1, stop=False, jitter=-1, mode="ubuntu"):
    if mode == 'ubuntu':
        netemCmd = "sudo tc qdisc change dev lo"
        nBW = False
        #parent 1:1 handle 2:0 netem delay "+defaultDelay+"ms "+defaultJitter+"ms distribution normal loss "+defaultLoss+"%"
        if(latency != -1):
            nBW = True
            netemCmd += " parent 1:1 handle 2:0 netem delay "+str(latency)+"ms"
        if(jitter != -1):
            if nBW:
                netemCmd += " "+str(jitter)+"ms"
        if(packetLoss != -1):
            if not nBW:
                netemCmd += " parent 1:1 handle 2:0 netem distribution normal loss "+packetLoss+"%"
            else:
                nBW = True
                netemCmd += " distribution normal loss "+packetLoss+"%"
        ret = subprocess.run(netemCmd.split(' '))
        print("ret val: ",ret)
        return
    if mode == 'mac':
        comcastCmd = "comcast --device=en0"
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
        #comcastCmd = "echo > 82246 | "+comcastCmd
        proc = subprocess.Popen(["comcast","--stop"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        line = proc.stdout.readline().decode()
        print(line)
        if(line[:9] == "Password:"):
            proc.stdin.write("82246")
        proc = subprocess.Popen(comcastCmd.split(' '), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        line = proc.stdout.readline().decode()
        print(line)
        if(line[:9] == "Password:"):
            proc.stdin.write("82246")
    
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

    parent_conn, child_conn = Pipe()
    simulation = Process(target=latencyIncreaseTest, args=(child_conn, ))
    simulation.start()
    
    if parent_conn.recv().split(' ')[1] == 'start':
        s = "vlc "+input_path+"  --play-and-exit --quiet :sout=#rtp{sdp=rtsp://:8554/} :sout--all :sout-keep"
        #vlcProc = Process(target=openVLC, args=(s, ))
        #vlcProc.start()
        #time.sleep(3)

        s = "ffmpeg -i rtmp://127.0.0.1/vod/test.mp4 -codec copy -r "+fps+" "+output_path
        subprocess.run(s.split())
    #time.sleep(0.5)
    #s = "ffmpeg -i rtsp://127.0.0.1:8554/ -rtsp-transport tcp -codec copy -r "+fps+" "+output_path
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
    #vlcProc.join()
    print('Simulatioin done.')
    parent_conn.send("End")
    #parent_conn.send('End')
    return


if __name__ == "__main__":
    args = command_parse()
    fileList = os.listdir(args.path)
    defaultBW = "10000kbit"
    defaultDelay = "1"
    defaultJitter = "1"
    defaultLoss = "0"
    #mode = "lat"
    #if mode == "lat":
    #subprocess.run('export GOPATH=\"$HOME/go\"')
    tmpcmd = "sudo tc qdisc del dev lo root"
    subprocess.run(tmpcmd.split(' '))
    tmpcmd = "sudo tc qdisc add dev lo root handle 1:0 tbf rate "+defaultBW+" buffer 200000 limit 200000"
    subprocess.run(tmpcmd.split(' '))
    tmpcmd = "sudo tc qdisc add dev lo parent 1:1 handle 2:0 netem delay "+defaultDelay+"ms "+defaultJitter+"ms distribution normal loss "+defaultLoss+"%"
    subprocess.run(tmpcmd.split(' '))


    for filename in fileList:
        if(isfile(filename) and filename[-4:] == '.mp4'):
            filepath = join(args.path, filename)
            print(filepath)
            outputPath = join(args.path, "output", filename[:-4]+'.mp4')
            print(outputPath)
            streaming(filepath, outputPath, 0, 0, 0, 0, 0, '30')
    
    #logFile.close()

