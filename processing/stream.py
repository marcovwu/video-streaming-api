import os
import cv2
import sys
import time

from queue import Queue
from pathlib import Path
from loguru import logger
from threading import Thread
from datetime import datetime
from abc import ABC, abstractmethod


class Stream(ABC):
    VIDOE_DTFORMAT = '%Y/%m/%d %H:%M:%S'

    @classmethod
    def load(cls, mode, video_path, div_fps, save_dir, video_sec=0, SYSDTFORMAT='', YMDFORMAT='', warn=True):
        if cls != Stream:
            raise NotImplementedError("Subclasses must implement from_dict()")
        if mode == "video":
            stream = VideoStream(video_path, div_fps, save_dir, SYSDTFORMAT=SYSDTFORMAT)
            stream_thread = None
        elif mode == "webcam":
            # TODO: maxsize
            stream = LiveVideoStream(
                video_path, video_sec, div_fps, save_dir, SYSDTFORMAT, YMDFORMAT, queue_maxsize=10, warn=warn)
            stream_thread = Thread(target=stream.run, daemon=True)
        else:
            raise ValueError("Invalid shape type")
        if stream.fps <= 0.0:
            logger.warning("Something error in %s video, will skip to inference this video!!" % video_path)
        return stream, stream_thread

    @staticmethod
    def make_ydt(year_date_time):
        if len(year_date_time) == 12:
            return '20' + year_date_time
        return year_date_time

    @abstractmethod
    def get_cur_info(self, cur_second):
        """ Get the time & sec in cur frame (second) """
        pass

    @abstractmethod
    def stop(self, stop_stream=True):
        """ Stop current stream (stop_stream=False) or thread (stop_stream=True)"""
        pass

    @abstractmethod
    def run_stop(self, frame):
        """ Check whether if need to stop the stream """
        pass

    @abstractmethod
    def get_image(self):
        """ Capture new image from stream """
        pass

    @abstractmethod
    def read(self, frame):
        """ Read new image from stream """
        pass


class VideoStream(Stream):
    def __init__(self, source, div_fps=1, save_dir='', SYSDTFORMAT='%Y%m%d%H%M%S'):
        # div path
        self.save_dir = save_dir
        self.SYSDTFORMAT = SYSDTFORMAT
        self.group = source.split(os.sep)[-4]
        self.channel = source.split('/')[-3]
        self.date_time = source.split(os.sep)[-2]
        self.save_folder = Path(os.path.join(self.save_dir, self.group, self.channel, self.date_time))
        self.start_time = Stream.make_ydt('.'.join(os.path.basename(source).split('.')[:-1]))
        self.start_sec = datetime.strptime(self.start_time, self.SYSDTFORMAT).timestamp()
        # init
        self.div_fps = div_fps
        self.stop_stream = False
        self.cur_frame_id = 0
        self.capture = cv2.VideoCapture(source)
        self.fps = self.capture.get(cv2.CAP_PROP_FPS)
        self.width = self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)  # float
        self.height = self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)  # float
        self.maxframes = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.epochframes = self.maxframes
        self.infer_fps = self.fps // self.div_fps

    def get_cur_info(self, cur_second):
        """ Get the time & sec in cur frame (second) """
        cur_time = datetime.fromtimestamp(cur_second).strftime(self.SYSDTFORMAT)
        vid_time = datetime.fromtimestamp(cur_second).strftime(Stream.VIDOE_DTFORMAT)
        return self.date_time, cur_second, cur_time, vid_time

    def stop(self, stop_stream=True):
        self.stop_stream = stop_stream
        if self.capture is not None and self.capture.isOpened():
            self.capture.release()
            logger.info('Stop the video capture process.')

    def run_stop(self, frame):
        if frame >= self.maxframes:
            self.stop(stop_stream=True)
            return True
        return False

    def get_image(self):
        ret = True
        while ret:
            ret, img = self.capture.read()
            self.cur_frame_id += 1
            if self.cur_frame_id % self.div_fps != 0:
                break
        return ret, img, {'sec': self.start_sec + (self.cur_frame_id / self.fps), 'curframe': self.cur_frame_id}

    def read(self, frame):
        """ Read new image from stream """
        ret, img, info = False, None, {'sec': -1}
        while img is None and self.capture.isOpened() and not self.run_stop(frame):
            ret, img, info = self.get_image()
            if 'curframe' in info:
                frame = info['curframe'] if ret else self.epochframes
        return ret, frame, img, info


class LiveVideoStream:
    def __init__(
        self, stream_info, video_sec, div_fps, save_dir, SYSDTFORMAT, YMDFORMAT, queue=None, queue_maxsize=10, warn=True
    ):
        # info
        self.ip = stream_info['ip']
        self.port = stream_info['port']
        self.content = stream_info['content']
        self.username = stream_info['username']
        self.password = stream_info['password']
        self.group = stream_info['group']
        self.channel = stream_info['channel']
        # var
        self.video_sec = video_sec
        self.div_fps = div_fps
        self.save_dir = save_dir
        self.SYSDTFORMAT = SYSDTFORMAT
        self.YMDFORMAT = YMDFORMAT
        self.warnning = warn
        # cfg
        self.capture = None
        self.queue_maxsize = queue_maxsize
        self.queue = Queue(maxsize=self.queue_maxsize) if queue is None else queue
        self.disc_frame_thres = 5  # 5 times in read error
        self.lost_internet_wait_sec = 60 * 15  # 15 minutes in seconds
        self.queue_wait_sec = self.queue_maxsize * 16 * 0.5   # max 16 channels and tolerance second

        # Start the Process
        self.reset_attemps()
        self.start()
        while self.capture is None or not self.capture.isOpened():
            logger.warning('Initialization the LiveStream Failed !!')
            if not self.set_camera():
                logger.error('Camera connection error occurring frequently during initialization.')
                logger.error('Please check if the %s/%s camera is working properly.' % (self.group, self.channel))
                break

    def init(self):
        """ Initialize variables that will be used for live streaming. """
        userinfo = "" if self.username == ' ' and self.password == ' ' else f"{self.username}:{self.password}"
        self.rtsp_url = f"rtsp://{userinfo}@{self.ip}:{self.port}/{self.content}"
        self.stop_stream = False
        self.stop_signal = False
        self.fps = 0
        self.prev_real_sec = None
        # check queue
        wt = time.time()
        if self.queue.qsize():
            logger.warning('Waiting to infer %s size of queue ...' % str(self.queue.qsize()))
            while self.queue.qsize() and (time.time() - wt <= self.queue_wait_sec):
                time.sleep(0.01)
        if self.queue.qsize():
            logger.warning('Remain %s queue size.' % str(self.queue.qsize()))
            logger.warning('Timeout while waiting to infer images queue in %s!!' % str(self.start_time))
        self.queue.queue.clear()

        # error handling
        self.disc_frame_count = 0
        self.drop_frame_count = 0

    def reset_attemps(self):
        self.reconnection_attemps = 20

    def _update_stream_info(self, fps, width, height):
        """ Update the new video stream information. """
        self.fps = fps
        self.infer_fps = self.fps // self.div_fps
        self.width = width
        self.height = height
        # Update parameters
        self.date_time, self.start_sec, self.start_time, self.vid_time = self.get_cur_info(self.prev_real_sec)
        self.save_folder = Path(os.path.join(self.save_dir, self.group, self.channel, self.date_time))
        self.maxframes = sys.maxsize
        self.epochframes = round(self.video_sec * self.fps)
        self.drop_frame_thres = self.fps * 60 * 10  # 10 minutes

    def _update_frame_info(self, ret, img, cur_real_sec, cur_sec, cur_frame: int, cur_frame_id: int):
        """ Update new image inofrmation and put them to queue. """
        # Calculate FPS and Delay time
        # cur_fps = 1 / (cur_sec - self.prev_sec) if cur_sec != self.prev_sec else 0
        # cur_delay_time = (cur_frame - self.prev_frame) / self.fps - (cur_sec - self.prev_sec)
        # real_fps = 1 / (cur_real_sec - self.prev_real_sec)

        # Update parameters
        self.reset_attemps()
        self.stop_stream = False
        self.prev_img = img
        self.prev_real_sec = cur_real_sec
        self.prev_sec = cur_sec
        self.prev_frame = cur_frame
        self.prev_frame_id = cur_frame_id

        # Check to release the queue space
        if self.queue.full():
            self.queue.get()
            if self.warnning:
                logger.warning('Drop camera queue!')
            if self.drop_frame_count < self.drop_frame_thres:
                self.drop_frame_count += 1
            else:
                raise Exception('Process thread might be dead, shutting down')
        else:
            self.drop_frame_count = 0

        # Put new information to queue
        self.queue.put((ret, img, {'sec': cur_real_sec, 'frame': cur_frame, 'curframe': cur_frame_id}))

    def get_cur_info(self, cur_second):
        """ Get the time & sec in cur frame (second) """
        cur_date_time = datetime.fromtimestamp(cur_second).strftime(self.YMDFORMAT)
        cur_time = datetime.fromtimestamp(cur_second).strftime(self.SYSDTFORMAT)
        vid_time = datetime.fromtimestamp(cur_second).strftime(Stream.VIDOE_DTFORMAT)
        return cur_date_time, cur_second, cur_time, vid_time

    def set_camera(self):
        if self.reconnection_attemps <= 0:
            logger.warning('Reset attempts exausted, scan for possible rtsp url change')
            return False
        else:
            logger.warning('"Camera Disconnected" or "Failed to Load Live Video Image" !!')
            logger.warning('Try to reconnect, attempts remaining: {}'.format(self.reconnection_attemps))
            self.start()
        return True

    def read_image(self, fix=True):
        """ Read image from capture """
        while True:
            ret, img = self.capture.read()

            # cur information
            cur_real_sec = time.time()
            cur_sec = self.capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            cur_frame = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
            # calc frame_id
            if self.prev_real_sec is not None:
                cur_frame_id = int(self.prev_frame_id + max(1, round((cur_real_sec - self.prev_real_sec) * self.fps)))
            else:
                cur_frame_id = self.div_fps

            # Camera Error handling
            if fix:
                warning_msg, ret, img, cur_real_sec, cur_sec, cur_frame = self.handle_error(
                    ret, img, cur_real_sec, cur_sec, cur_frame)
                if warning_msg:
                    logger.warning('\n' + warning_msg)
            # Prevent read times
            if self.disc_frame_count > self.disc_frame_thres:
                ret, img = False, None
                self.disc_frame_count = 0
                logger.warning('Read image failed, re-connecting to the camera')
                break

            # Success to read new image
            if ret:
                break
            else:
                self.disc_frame_count += 1

        return ret, img, cur_real_sec, cur_sec, cur_frame, cur_frame_id

    def handle_error(self, ret, img, cur_real_sec, cur_sec, cur_frame):
        """
            （1）影像毀損，代表 camera deocde image 失敗 frame counter 停止 + 1
            （2）網路問題，代表沒有讀取到 image 所以 msec counter 和 previous 一樣
            （3）讀取失敗，代表 img is None, time, frame 皆為一樣，此時必須 error_counter += 1
        """
        warning_msg = ""
        if cur_frame == self.prev_frame:
            ret, img = False, None
            warning_msg += "Packet loss or delay at the camera side !!\n"
        else:
            # Network delays
            if cur_sec == self.prev_sec:
                warning_msg += "Read image timeout, resolve network delays encountered during image reading !!\n"
                ret, img = False, None
                # Use previous sec and fps to get cur sec
                cur_real_sec = self.prev_real_sec + (cur_frame - self.prev_frame) / self.fps
                cur_sec = self.prev_sec + (cur_frame - self.prev_frame) / self.fps

            # Assign previous image
            if img is None:
                ret, img = False, None
                if cur_sec > self.prev_sec and cur_frame > self.prev_frame:
                    warning_msg += "The image receiving process experiences packet loss or delay.\n"

                # prevent prev_img still None
                if self.prev_img is None:
                    warning_msg += 'Video Capture error %d times\n' % int(self.disc_frame_count)
                else:
                    self.disc_frame_count += 1
                    warning_msg += "Giving previous image as the new image.(%d times)\n" % int(self.disc_frame_count)
                    ret, img = True, self.prev_img
            else:
                self.disc_frame_count = 0

        return warning_msg, ret, img, cur_real_sec, cur_sec, cur_frame

    def process_image(self, fix=True):
        """ Read new image from capture and Update to queue. """
        # Load New Image
        cur_frame_id = -0.5  # prevent div_fps is 1
        while ((cur_frame_id % self.div_fps) != 0):
            ret, img, cur_real_sec, cur_sec, cur_frame, cur_frame_id = self.read_image(fix=fix)
            if not ret:
                self.stop(stop_stream=False)
                return ret

        # Update information or Stop the capture.
        self._update_frame_info(ret, img, cur_real_sec, cur_sec, cur_frame, cur_frame_id)
        return ret

    def start(self):
        self.init()
        self.reconnection_attemps -= 1
        if self.capture is not None and self.capture.isOpened():
            self.stop()
        self.capture = cv2.VideoCapture(self.rtsp_url)

        if self.capture.isOpened():
            logger.info('Connect camera successfull !!')
            # Set parameters
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # Init image
            logger.info('Waiting to process init image ...')
            if self.process_image(fix=False):
                logger.info('Process the image successfull. ')
                # Update parameters
                fps = self.capture.get(cv2.CAP_PROP_FPS)
                width = self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
                if fps > 0:
                    self._update_stream_info(fps, width, height)
                else:
                    logger.warning('Bad FPS in live streaming !!')
                    self.stop()
            else:
                logger.warning('Process image failed !!')
                self.stop()
        else:
            logger.warning('Load LiveStream Failed !!')
            self.stop()

    def stop(self, stop_stream=False):
        # put stop signal to main process
        self.stop_stream = stop_stream
        if self.stop_stream:
            if self.queue.full():
                self.queue.get()
            self.queue.put((False, None, {}))

        # release
        if self.capture is not None and self.capture.isOpened():
            self.capture.release()
            logger.info('Stop the video capture process.')
        else:
            logger.info('Already release the capture process.')

    def run_stop(self, frame):
        if frame < 0:
            self.stop(stop_stream=True)
            return True
        return False

    def get_image(self):
        try:
            ret, img, info = self.queue.get(block=True, timeout=self.lost_internet_wait_sec)
        except Exception:
            self.stop()
            ret, img, info = False, None, {}
            logger.warning("Queue is empty!!")
        return ret, img, info

    def read(self, frame):
        """ Read new image from stream """
        ret, img, info = False, None, {'sec': -1}
        while img is None and self.capture.isOpened() and not self.run_stop(frame):
            ret, img, info = self.get_image()
            if 'curframe' in info:
                frame = info['curframe'] if ret else self.epochframes
        return ret, frame, img, info

    def run(self):
        while True:
            if self.stop_signal:
                break
            elif self.capture.isOpened():
                # Get New Image
                ret = self.process_image(fix=True)

            elif not self.stop_stream:
                # Camera Disconnected or Load LiveVideo Image Failed
                if not self.set_camera():
                    break

            else:
                break
            time.sleep(0.01 / self.fps if self.fps > 0 else 0.0001)

        # Stop Stream Process
        self.stop(stop_stream=True)
