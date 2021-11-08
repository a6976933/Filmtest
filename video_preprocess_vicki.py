from moviepy.editor import *
import os
import argparse
import time
import cv2
import numpy as np
import logging
import subprocess
from multiprocessing import Process, Lock, Pipe
import random


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def command_parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', '-p', type=str, required=True, help='video document path')
    return parser.parse_args()

def addBlackscreen(input_path, output_path):
    blackscreen = VideoFileClip('black40.mp4')
    video1 = VideoFileClip(input_path)
    fps = video1.fps
    print(video1.w)
    print(video1.h)

    blackscreen_resize = blackscreen.resize((video1.w,video1.h))
    videoname = output_path[:-4]
    finalclip = concatenate_videoclips([blackscreen_resize, video1])
    finalclip.write_videofile(videoname+'_black.mp4',codec='mpeg4')
    return video1.h, video1.w, fps

def adjustVideo(input_path, fps, w, h, output_path):
    print("Adjust video resolution and fps...")
    video_clip = VideoFileClip(input_path)
    new_clip = video_clip.set_fps(fps)
    new_clip = new_clip.resize((w,h))
    try:
        new_clip.write_videofile(output_path)
        logger.info("Saved .mp4 without Exception at {}".format(output_path))
    except IndexError:
        # Short by one frame, so get rid on the last frame:
        new_clip = new_clip.subclip(t_end=(new_clip.duration - 1.0/new_clip.fps))
        new_clip.write_videofile(output_path)
        logger.info("Saved .mp4 after Exception at {}".format(save_path))
    except Exception as e:
        logger.warning("Exception {} was raised!!".format(e))  
    return
   
def networkSimulate(conn, mode, rate, delay, delay_jitter, loss):
    
    s = "sudo tc qdisc del dev lo root"
    return_value = subprocess.run(s.split())
    print(return_value)
    s = "sudo tc qdisc add dev lo root handle 1:0 tbf rate "+rate+"kbit buffer 200000 limit 200000"
    return_value = subprocess.run(s.split())
    print(return_value)
    s = "sudo tc qdisc add dev lo parent 1:1 handle 2:0 netem delay "+delay+"ms "+delay_jitter+"ms distribution normal loss "+loss+"%"
    return_value = subprocess.run(s.split())
    if return_value.returncode == 0: # cmd runs correctly
        conn.send('Success')
        print('Network parameter set successfully')
    else:
        conn.send('Fail')
        print('Fail to set network parameters')
        return
    if mode == 2 or mode == 3: # keep changing network parameter
        if mode == 2:
            loss_new = 5
        elif mode == 3:
            loss_new = 10
        if mode == 2:
            rate_new = rate
        elif mode == 3:
            rate_new = str(1000)

        start_time = time.time()  
        interval = random.randint(1,10)+60 # randomly choose an interval from now to have burst packet loss
        print(interval)
        while True:
            # print('QQ')
            if conn.poll():
                if conn.recv() == 'End':
                    return

            end_time = time.time()
            if end_time - start_time >= interval:
                print('In')
                s = "sudo tc qdisc change dev lo root handle 1:0 tbf rate "+rate+"kbit buffer 200000 limit 200000"
                return_value = subprocess.run(s.split())
                s = "sudo tc qdisc change dev lo parent 1:1 handle 2:0 netem delay 60ms 30ms distribution normal loss "+str(loss_new)+"%"
                return_value = subprocess.run(s.split())
                time.sleep(5)
                s = "sudo tc qdisc change dev lo root handle 1:0 tbf rate "+rate+"kbit buffer 200000 limit 200000"
                return_value = subprocess.run(s.split())
                s = "sudo tc qdisc change dev lo parent 1:1 handle 2:0 netem delay "+delay+"ms "+delay_jitter+"ms distribution normal loss "+loss+"%"
                return_value = subprocess.run(s.split())
                interval = random.randint(30,60) # randomly choose an interval from now to have burst packet loss
                print(interval)
                start_time = time.time() 




def streaming(input_path, output_path, mode, rate, delay, delay_jitter, loss, fps):
    print('Start simulation')
    # os.system("sudo tc qdisc del dev lo root")
    # os.system("sudo tc qdisc add dev lo root handle 1:0 tbf rate "+rate+"kbit buffer 200000 limit 200000")
    # os.system("sudo tc qdisc add dev lo parent 1:1 handle 2:0 netem delay "+delay+"ms "+delay_jitter+"ms distribution normal loss "+loss+"%")
    # os.system("vlc "+input_path+" --no-video-title --play-and-exit --quiet :sout=#transcode{vcodec=h264}:rtp{sdp=rtsp://:8554/} :sout--all :sout-keep :file-caching=1000 &")
    # time.sleep(0.5)
    # os.system("ffmpeg -i rtsp://127.0.0.1:8554/ -codec copy -r "+ fps +" "+ output_path)

    parent_conn, child_conn = Pipe()
    simulation = Process(target=networkSimulate, args=(child_conn, mode, rate, delay, delay_jitter, loss))
    simulation.start()
    if parent_conn.recv() == 'Success':
        s = "vlc "+input_path+" --no-video-title --play-and-exit --quiet :sout=#transcode{vcodec=h264}:rtp{sdp=rtsp://:8554/} :sout--all :sout-keep :file-caching=1000 &"
        subprocess.run(s, shell=True)
        time.sleep(0.5)
        s = "ffmpeg -hide_banner -loglevel panic -i rtsp://127.0.0.1:8554/ -codec copy -r "+ fps +" "+ output_path
        subprocess.run(s.split())
    elif parent_conn.recv() == 'Fail':
        return
    # os.system("vlc rtsp://127.0.0.1:9000/ --network-caching=20000 --rtsp-frame-buffer-size=1000000 --sout=file/ts:"+output_path+" --play-and-exit --quiet")
    print('Simulatioin done.')
    parent_conn.send('End')
    return
    
def cut_video(input_path, output_path, fps):
    print("Remove residual black videos...")
    start_time = 0
    video = cv2.VideoCapture(input_path)
    if video.isOpened():
        width  = video.get(cv2.CAP_PROP_FRAME_WIDTH)  # float
        len_video_cv = video.get(cv2.CAP_PROP_FRAME_COUNT)/video.get(cv2.CAP_PROP_FPS)
        frame_cnt = 0
        while True:
            frame_exist, current_frame = video.read()
            if frame_exist:
                frame_cnt = frame_cnt+1;
                check_black = np.sum(current_frame, axis=2)
                check_black = np.sum(check_black, axis=1)
                if np.sum(check_black_ele > 0 for check_black_ele in check_black) > 0.01*width:
                    start_time = video.get(cv2.CAP_PROP_POS_MSEC)
                    print(start_time)
                    break
    video_clip = VideoFileClip(input_path)
    num_frame_moviepy = video_clip.reader.nframes
    len_video_moviepy = num_frame_moviepy/video_clip.fps
    if len_video_moviepy > len_video_cv and (len_video_moviepy-len_video_cv)+start_time/1000>5:
        print(len_video_moviepy-len_video_cv)
        start_time = (start_time/1000-5+(len_video_moviepy-len_video_cv))
    elif start_time > 5000:
        start_time = (start_time/1000-5)

    os.system("ffmpeg -i " +input_path+ " -ss 00:00:" +str(start_time)+ " -codec copy " +output_path)
        
    # video_clip = video_clip.set_fps(fps)
    # try:
    #     video_clip.write_videofile(output_path)
    #     logger.info("Saved .mp4 without Exception at {}".format(output_path))
    # except IndexError:
    #     # Short by one frame, so get rid on the last frame:
    #     video_clip = video_clip.subclip(t_end=(video_clip.duration - 1.0/video_clip.fps))
    #     video_clip.write_videofile(output_path)
    #     logger.info("Saved .mp4 after Exception at {}".format(save_path))
    # except Exception as e:
    #     logger.warning("Exception {} was raised!!".format(e))  

    #video_clip.write_videofile(output_path)
    return
    
def main():
    # parameter_list_1080 = [[10000,40,10,0.1,1080,15],[10000,80,40,0.1,1080,15],[10000,40,10,0.3,1080,15],[10000,40,10,0.5,1080,15],[10000,40,10,0.1,1080,10],[10000,40,10,0.1,1080,5],[10000,40,10,0.1,720,15],[10000,40,10,0.1,480,15],[10000,40,10,0.1,360,15],[10000,40,10,0.1,240,15],[5000,40,10,0.1,1080,15],[10000,80,40,0.5,1080,15]]
    parameter_list_1080 = [[10000,40,10,0.2,1080,30],[10000,60,30,0.5,1080,30],[10000,40,10,0.2,1080,15],[10000,60,30,0.5,1080,15],[10000,40,10,0.2,720,30],[10000,60,30,0.5,720,30],[10000,40,10,0.2,480,30],[10000,60,30,0.5,480,30],[10000,40,10,0.2,360,30],[10000,60,30,0.5,360,30]]
    # parameter_list_720 = [[10000,40,10,0.1,720,30],[10000,60,30,0.1,720,30],[10000,40,10,0.5,720,30],[10000,60,30,0.5,720,30],[10000,40,10,0.1,720,15],[10000,40,10,0.1,720,10],[5000,40,10,0.1,720,30],[10000,40,10,0.1,480,30],[10000,40,10,0.1,480,15],[10000,40,10,0.1,360,30],[10000,40,10,0.1,360,15],[10000,40,10,0.1,240,30],[10000,40,10,0.1,240,15]]
    # parameter_list_720 = [[10000,60,30,0.1,360,30],[10000,40,10,0.5,360,30],[10000,60,30,0.5,360,30],[5000,40,10,0.1,360,30],[10000,60,30,0.1,360,15],[10000,40,10,0.5,360,15],[10000,60,30,0.5,360,15],[5000,40,10,0.1,360,15]]
    parameter_list_720 = [[10000,40,10,0.2,720,30],[10000,60,30,0.5,720,30],[10000,40,10,0.2,720,15],[10000,60,30,0.5,720,15],[10000,40,10,0.2,480,30],[10000,60,30,0.5,480,30],[10000,40,10,0.2,360,30],[10000,60,30,0.5,360,30]]
    parameter_list_480 = [[10000,40,10,0.2,480,30],[10000,60,30,0.5,480,30],[10000,40,10,0.2,480,15],[10000,60,30,0.5,480,15],[10000,40,10,0.2,360,30],[10000,60,30,0.5,360,30]]
    args = command_parse()
    file_list = os.listdir(args.path)
   
    for filename in file_list:
        # parameter_list_1080 = [[10000,40,10,0.1,1080,15],[10000,80,40,0.1,1080,15],[10000,40,10,0.3,1080,15],[10000,40,10,0.5,1080,15],[10000,40,10,0.1,1080,10],[10000,40,10,0.1,1080,5],[10000,40,10,0.1,720,15],[10000,40,10,0.1,480,15],[10000,40,10,0.1,360,15],[10000,40,10,0.1,240,15],[5000,40,10,0.1,1080,15],[10000,80,40,0.5,1080,15]]
        parameter_list_1080 = [[10000,40,10,0.2,1080,30],[10000,60,30,0.5,1080,30],[10000,40,10,0.2,1080,15],[10000,60,30,0.5,1080,15],[10000,40,10,0.2,720,30],[10000,60,30,0.5,720,30],[10000,40,10,0.2,480,30],[10000,60,30,0.5,480,30],[10000,40,10,0.2,360,30],[10000,60,30,0.5,360,30],[10000,40,10,0.2,240,30],[10000,60,30,0.5,240,30]]
        # parameter_list_720 = [[10000,40,10,0.1,720,30],[10000,60,30,0.1,720,30],[10000,40,10,0.5,720,30],[10000,60,30,0.5,720,30],[10000,40,10,0.1,720,15],[10000,40,10,0.1,720,10],[5000,40,10,0.1,720,30],[10000,40,10,0.1,480,30],[10000,40,10,0.1,480,15],[10000,40,10,0.1,360,30],[10000,40,10,0.1,360,15],[10000,40,10,0.1,240,30],[10000,40,10,0.1,240,15]]
        # parameter_list_720 = [[10000,60,30,0.1,360,30],[10000,40,10,0.5,360,30],[10000,60,30,0.5,360,30],[5000,40,10,0.1,360,30],[10000,60,30,0.1,360,15],[10000,40,10,0.5,360,15],[10000,60,30,0.5,360,15],[5000,40,10,0.1,360,15]]
        parameter_list_720 = [[10000,40,10,0.2,720,30],[10000,60,30,0.5,720,30],[10000,40,10,0.2,720,15],[10000,60,30,0.5,720,15],[10000,40,10,0.2,480,30],[10000,60,30,0.5,480,30],[10000,40,10,0.2,360,30],[10000,60,30,0.5,360,30],[10000,40,10,0.2,240,30],[10000,60,30,0.5,240,30]]
        parameter_list_480 = [[10000,40,10,0.2,480,30],[10000,60,30,0.5,480,30],[10000,40,10,0.2,480,15],[10000,60,30,0.5,480,15],[10000,40,10,0.2,360,30],[10000,60,30,0.5,360,30],[10000,40,10,0.2,240,30],[10000,60,30,0.5,240,30]]
        flag_fpsis15 = 0
        print(filename)
        # video_height, video_width, fps = addBlackscreen(args.path+'/'+filename,'temp.mp4')
        # video_height = 720
        # video_width = 1280
        # fps = 15
        
        print(fps)
        if fps > 30:
            fps = 30
        elif np.abs(fps-15) <=1:
            fps = 15
        elif np.abs(fps-30) <=1:
            fps = 30

        if video_height == 1080:
            parameter_list = parameter_list_1080
            if fps != 15:
                adjustVideo('temp_black.mp4', 15, 1920, 1080, 'temp_black_resize_1080.mp4')
                adjustVideo('temp_black.mp4', 30, 1280, 720, 'temp_black_resize_720.mp4')
                adjustVideo('temp_black.mp4', 30, 854, 480, 'temp_black_resize_480.mp4')
                adjustVideo('temp_black.mp4', 30, 640, 360, 'temp_black_resize_360.mp4')
            elif fps == 15:
                flag_fpsis15 = 1
                print(len(parameter_list))
                adjustVideo('temp_black.mp4', 15, 1280, 720, 'temp_black_resize_720.mp4')
                adjustVideo('temp_black.mp4', 15, 854, 480, 'temp_black_resize_480.mp4')
                adjustVideo('temp_black.mp4', 15, 640, 360, 'temp_black_resize_360.mp4')

        elif video_height == 720 and video_width == 960:
            parameter_list = parameter_list_720
            if fps != 15:
                adjustVideo('temp_black.mp4', 15, 960, 720, 'temp_black_resize_720.mp4')
                adjustVideo('temp_black.mp4', 30, 640, 480, 'temp_black_resize_480.mp4')
                adjustVideo('temp_black.mp4', 30, 480, 360, 'temp_black_resize_360.mp4')
                adjustVideo('temp_black.mp4', 30, 320, 240, 'temp_black_resize_240.mp4')
            elif fps == 15:
                flag_fpsis15 = 1
                adjustVideo('temp_black.mp4', 15, 640, 480, 'temp_black_resize_480.mp4')
                adjustVideo('temp_black.mp4', 15, 480, 360, 'temp_black_resize_360.mp4')
                adjustVideo('temp_black.mp4', 15, 320, 240, 'temp_black_resize_240.mp4')
        
        elif video_height == 720:
            parameter_list = parameter_list_720
            if fps != 15:
                adjustVideo('temp_black.mp4', 15, 1280, 720, 'temp_black_resize_720.mp4')
                adjustVideo('temp_black.mp4', 30, 854, 480, 'temp_black_resize_480.mp4')
                adjustVideo('temp_black.mp4', 30, 640, 360, 'temp_black_resize_360.mp4')
                adjustVideo('temp_black.mp4', 30, 426, 240, 'temp_black_resize_240.mp4')
            elif fps == 15:
                flag_fpsis15 = 1
                adjustVideo('temp_black.mp4', 15, 854, 480, 'temp_black_resize_480.mp4')
                adjustVideo('temp_black.mp4', 15, 640, 360, 'temp_black_resize_360.mp4')
                adjustVideo('temp_black.mp4', 15, 426, 240, 'temp_black_resize_240.mp4')

        elif video_height == 480:
            parameter_list = parameter_list_480
            if fps != 15:
                adjustVideo('temp_black.mp4', 15, 640, 480, 'temp_black_resize_480.mp4')
                adjustVideo('temp_black.mp4', 30, 480, 360, 'temp_black_resize_360.mp4')
                adjustVideo('temp_black.mp4', 30, 320, 240, 'temp_black_resize_240.mp4')
            elif fps == 15:
                flag_fpsis15 = 1
                adjustVideo('temp_black.mp4', 15, 480, 360, 'temp_black_resize_360.mp4')
                adjustVideo('temp_black.mp4', 15, 320, 240, 'temp_black_resize_240.mp4')
            
        # parameter_list = parameter_list_720
        # flag_fpsis15 = 1
        if flag_fpsis15 == 1:
            parameter_list.pop(2)
            parameter_list.pop(2)

        print(len(parameter_list))
          
        if not os.path.exists(filename[:-4]):
            os.mkdir(filename[:-4])
        if not os.path.exists(filename[:-4]+"_origin"):
            os.mkdir(filename[:-4]+"_origin")

        for para_idx in range(0,len(parameter_list)):
            para = parameter_list[para_idx][:]  
            if flag_fpsis15 == 1:
                para[5] = 15
            print(para)
            scale = para[4]/video_height
            if scale != 1 or para[5] != fps:
                if para[4] == 720:
                    stream_file = 'temp_black_resize_720.mp4'
                elif para[4] == 480:
                    stream_file = 'temp_black_resize_480.mp4'
                elif para[4] == 360:
                    stream_file = 'temp_black_resize_360.mp4'
                elif para[4] == 1080:
                    stream_file = 'temp_black_resize_1080.mp4'
                elif para[4] == 240:
                    stream_file = 'temp_black_resize_240.mp4'
                # adjustVideo('temp_black.mp4', para[5], w, h, 'temp_black_resize.mp4')
            else:
                stream_file = 'temp_black.mp4'

            simulation_file = filename[:-4]+'_origin/'+filename[:-4]+'_'+str(para_idx+1)+'.mp4'
            if not os.path.exists(simulation_file):
                streaming(stream_file, simulation_file, 1, rate=str(para[0]), delay=str(para[1]), delay_jitter=str(para[2]), loss=str(para[3]), fps=str(para[5]))
            
            if para[1] == 40:
                simulation_file = filename[:-4]+'_origin/'+filename[:-4]+'_'+str(para_idx+1)+'_m.mp4'
                if not os.path.exists(simulation_file):
                    streaming(stream_file, simulation_file, 2, rate=str(para[0]), delay=str(para[1]), delay_jitter=str(para[2]), loss=str(para[3]), fps=str(para[5]))
                simulation_file = filename[:-4]+'_origin/'+filename[:-4]+'_'+str(para_idx+1)+'_m2.mp4'
                if not os.path.exists(simulation_file):
                    streaming(stream_file, simulation_file, 3, rate=str(para[0]), delay=str(para[1]), delay_jitter=str(para[2]), loss=str(para[3]), fps=str(para[5]))
                
            # cut_video(simulation_file, filename[:-4]+'/'+filename[:-4]+'_'+str(para_idx+1)+'.mp4', para[5])
            
        os.remove('temp_black.mp4')
        if os.path.exists('temp_black_resize_240.mp4'):
            os.remove('temp_black_resize_240.mp4')
        if os.path.exists('temp_black_resize_360.mp4'):
            os.remove('temp_black_resize_360.mp4')
        if os.path.exists('temp_black_resize_480.mp4'):
            os.remove('temp_black_resize_480.mp4')
        if os.path.exists('temp_black_resize_720.mp4'):
            os.remove('temp_black_resize_720.mp4')
        if os.path.exists('temp_black_resize_1080.mp4'):
            os.remove('temp_black_resize_1080.mp4')

         # video_height = 720
        # video_width = 1280
        # fps = 15
    return
    
if __name__=='__main__':
    main()
