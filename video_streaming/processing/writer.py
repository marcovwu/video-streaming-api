import os
import cv2
import time

from queue import Queue
from loguru import logger


VIDFORMAT = {'.mp4': "mp4v"}


class VideoWriter:
    def __init__(
        self, save_dir, video_define, start_time, runfps, width, height, init_writer=False,
        vid_reload=False, title='', vid_format='.mp4', queue=None, queue_maxsize=200, visualizer=None, keepname=False
    ):
        self.save_dir = save_dir
        self.video_define = video_define
        self.start_time = start_time
        self.runfps = runfps
        self.width = width
        self.height = height
        self.vid_format = vid_format
        self.title = title
        self.vid_reload = vid_reload
        self.keepname = keepname
        # init
        self.writer = None
        self.already_init_writer = init_writer
        self.stop_flag = True
        self.internal_show = False
        self.visualizer = visualizer
        self.queue_maxsize = queue_maxsize
        self.queue = Queue(maxsize=self.queue_maxsize) if queue is None else queue
        self._update_writer(start_time, is_need_new_writer=init_writer)

    def _init_writer_path(self, start_time):
        self.start_time = start_time if not self.keepname else self.start_time
        self.save_folder = os.path.join(self.save_dir, *self.video_define['parent_folder'])
        self.save_folder = self.save_folder if len(self.save_folder) else './'
        self.save_path = os.path.join(self.save_folder, self.start_time + self.vid_format)
        self.WINDOW_NAME = 'Process Video Streaming in %s' % self.save_path

    def _update_writer(self, start_time, current_date_time="", is_need_new_writer=True):
        # TODO: update new date folder into save_folder when is_need_new_writer is True
        self._init_writer_path(start_time)
        # Init New VideoWriter
        if is_need_new_writer:
            self.run_stop()
            os.makedirs(self.save_folder, exist_ok=True)
            self.writer = cv2.VideoWriter(
                self.save_path, cv2.VideoWriter_fourcc(*VIDFORMAT[self.vid_format]),
                self.runfps, (int(self.width), int(self.height))
            )
            self.already_init_writer = True
        self.stop_flag = False
        # self.queue.queue.clear()

    def _check_write(self, write, vis):
        return write and (vis == 'a' or vis == 'w')

    def _check_show(self, show, vis):
        return show and (vis == 'a' or vis == 's')

    def adjust_size(self, width, height, init_video_writer=False):
        self.width, self.height = width, height
        self._update_writer(self.start_time, is_need_new_writer=init_video_writer)

    def plot_time_delay(self, img, sec):
        delay_ms = (time.time() - sec) * 1000
        color = [0, 0, 255] if delay_ms > 50 else [0, 255, 0]
        if delay_ms > 1000 * 60 * 60 / 24:
            label = '(%.2fd)' % (delay_ms / 1000 / 60 / 60 / 24)
        elif delay_ms > 1000 * 60 * 60:
            label = '(%.2fh)' % (delay_ms / 1000 / 60 / 60)
        elif delay_ms > 1000 * 60:
            label = '(%.2fm)' % (delay_ms / 1000 / 60)
        elif delay_ms > 1000:
            label = '(%.2fs)' % (delay_ms / 1000)
        else:
            label = '(%.2fms)' % (delay_ms)
        pt = (int(self.width - 100), 30)
        cv2.putText(img, label, pt, 0, 0.5, color, thickness=1, lineType=cv2.LINE_AA)

    def run_stop(self):
        if self.writer is not None:
            self.writer.release()
            self.writer = None
            logger.info(f"Saved the video in {self.save_path}")
            return True
        return False

    def put_frame(self, result_frame, current_date_time, current_time, current_sec, vis='a'):
        drop = False
        if self.queue.full():
            drop = True
            self.queue.get()
        self.queue.put((result_frame, current_date_time, current_time, current_sec, vis))
        return drop

    def write_image(self, im0, current_date_time, current_time):
        if self.writer is None:
            if self.vid_reload or not self.already_init_writer:
                if self.title:
                    logger.info('\n' + self.title)
                self._update_writer(current_time, current_date_time=current_date_time, is_need_new_writer=True)
            else:
                return True
        # write
        self.writer.write(im0)
        return False

    def show_image(self, im0, current_sec, delay=True):
        if delay:
            self.plot_time_delay(im0, current_sec)
        if self.visualizer is None:
            self.internal_show = True
            cv2.imshow(self.WINDOW_NAME, im0)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                return True
        else:
            if self.visualizer.check_stop(self.WINDOW_NAME):
                return True
            # put to visualizer queue
            self.visualizer.put_frame(self.WINDOW_NAME, im0)
        return False

    def process_video(self, write=True, show=True, delay=True):
        while True:
            im0, current_date_time, current_time, current_sec, vis = self.queue.get()
            if im0 is None:
                # stop the current writer
                if current_time:
                    self.run_stop()
                else:
                    break
            else:
                # write
                if self._check_write(write, vis):
                    res = self.write_image(im0, current_date_time, current_time)
                    if res:
                        break

                # show
                if self._check_show(show, vis):
                    res = self.show_image(im0, current_sec, delay=delay)
                    if res:
                        break

        # put None to the queue of visualizer for release the current window
        self.stop_flag = True
        if self.internal_show and self._check_show(show, vis) and self.visualizer is None:
            cv2.destroyWindow(self.WINDOW_NAME)
        self.run_stop()
        logger.info('Stop video writer thread.')
