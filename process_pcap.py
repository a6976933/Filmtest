import os
import subprocess
import datetime
import json
from multiprocessing import Process, Lock, Pipe
from os.path import isfile, isdir, join
from matplotlib import pyplot as plt
from mpl_toolkits.axisartist.parasite_axes import HostAxes, ParasiteAxes


f = open("rtpjson3.json")
f1 = open("2021-11-17162232.txt")
packets = json.load(f)
startTime = datetime.datetime(year=2021,month=11,day=17,hour=16,minute=22,second=33,microsecond=0)
packetTime = []
packetTime.append(startTime)
packetLoss = [0]
delay = [0]
bandwidth = [10.0]
lastdelay = 0
lastbandwidth = 10.0
seqnumv = -1
seqnuma = -1
adjustData = f1.readline().split()
adjDataTime = datetime.datetime.strptime(adjustData[0]+" "+adjustData[1], "%Y-%m-%d %H:%M:%S.%f")
print(adjustData)
for packet in packets:
    if "rtp" in packet["_source"]["layers"]:
        #print(packet["_source"]["layers"]["frame"]["frame.time"][:15].split()[3])
        rtpTime = datetime.datetime.strptime("2021-11-17 "+packet["_source"]["layers"]["frame"]["frame.time"].split()[3][:15], "%Y-%m-%d %H:%M:%S.%f")
        #rtpTime.year = 2021
        #rtpTime.month = 11
        #rtpTime.day = 17
        delta = rtpTime - packetTime[-1]
        #print(delta)
        milidelta = int(delta.total_seconds()*100//10)
        #print(milidelta)
        #milidelta += delta.second*10]
        hasdelta = False
        for i in range(0,milidelta):
            packetLoss.append(0)
            packetTime.append(packetTime[-1]+datetime.timedelta(milliseconds=100))
            bandwidth.append(lastbandwidth)
            delay.append(lastdelay)
            hasdelta = True
            if adjDataTime-packetTime[-1] < datetime.timedelta(milliseconds=100):
                if adjustData[2] == "latency:":
                    delay[-1] = int(adjustData[3][:-2])
                    lastdelay = delay[-1]
                else:
                    bandwidth[-1] = float(adjustData[3][:-4]) / 1000
                    lastbandwidth = bandwidth[-1]
                adjustData = f1.readline().split()
                adjDataTime = datetime.datetime.strptime(adjustData[0]+" "+adjustData[1], "%Y-%m-%d %H:%M:%S.%f")
                print(adjDataTime)
        print(packet["_source"]["layers"]["rtp"]["rtp.ssrc"])
        if packet["_source"]["layers"]["rtp"]["rtp.ssrc"] == "0x5e6f302e":
            if seqnumv == -1:
                seqnumv = int(packet["_source"]["layers"]["rtp"]["rtp.seq"])
            else:
                nowseq = int(packet["_source"]["layers"]["rtp"]["rtp.seq"])
                print(nowseq)
                if nowseq-seqnumv > 1:
                    print(nowseq)
                    print(seqnumv)
                    print(adjDataTime)
                    packetLoss[-1] += nowseq-seqnumv-1
                seqnumv = nowseq
        if packet["_source"]["layers"]["rtp"]["rtp.ssrc"] == "0x5929d8d4":
            if seqnuma == -1:
                seqnuma = int(packet["_source"]["layers"]["rtp"]["rtp.seq"])
            else:
                nowseq = int(packet["_source"]["layers"]["rtp"]["rtp.seq"])
                if nowseq-seqnuma > 1:
                    packetLoss[-1] += nowseq-seqnuma-1
                seqnuma = nowseq

fig = plt.figure(1)
host = HostAxes(fig,[0.15, 0.1, 0.65, 0.8])
par1 = ParasiteAxes(host, sharex=host)
par2 = ParasiteAxes(host, sharex=host)
host.parasites.append(par1)
host.parasites.append(par2)
host.axis["right"].set_visible(False)

par1.axis["right"].set_visible(True)
par1.axis["right"].major_ticklabels.set_visible(True)
par1.axis["right"].label.set_visible(True)

par2.axis["right2"] = par2.new_fixed_axis(loc="right", offset=(60, 0))
par2.set_ylim(0,10)
p1, = host.plot(packetTime,packetLoss, label="packet loss")
p2, = par1.plot(packetTime,delay, label="delay(ms)")
p3, = par2.plot(packetTime,bandwidth, label="bandwidth(Mbps)")


host.set_xlabel("Time")
host.set_ylabel("Packet Loss number")
par1.set_ylabel("Delay(ms)")
par2.set_ylabel("Bandwidth(Mbps)")

host.legend()

host.axis["left"].label.set_color('black')
par1.axis["right"].label.set_color('red')
par2.axis["right2"].label.set_color('green')
fig.add_axes(host)
#plt.plot(packetTime, bandwidth)
plt.show()
        #packetTime.append(datetime.datetime.strptime(packet["_source"]["layers"]["frame"]["frame.time"].split()[3], "%H:%M:%S.%f"))




'''
f = open("sender.txt")
band = []
timeserie = []
enter = False
lastTime = None
nowMili = 0
odd = True
packTime = None
for line in f:
    line = line.split()
    if odd:
        packTime = datetime.datetime.strptime(line[0], "%H:%M:%S.%f")
        odd = False
    elif not odd:
        if not enter:
            lastTime = packTime
            enter = True
            timeserie.append(lastTime)
            band.append(int(line[-1]))
        else:
            if packTime-lastTime < datetime.timedelta(milliseconds=10):
                band[-1] += int(line[-1])
            else:
                lastTime = packTime
                timeserie.append(timeserie[-1] + datetime.timedelta(milliseconds=10))
                band.append(int(line[-1]))
        odd = True

plt.plot(timeserie, band)
plt.show()
'''