import os
import subprocess
import datetime
from multiprocessing import Process, Lock, Pipe
from os.path import isfile, isdir, join
from matplotlib import pyplot as plt

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
