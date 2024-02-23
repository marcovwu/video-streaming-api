import cv2
import time

from loguru import logger
from queue import Queue
from threading import Thread


class Visualizer:
    def __init__(self, queue=None, maxsize=30, start=True):
        self.windows = {}
        self.maxsize = maxsize
        self.queue = queue
        self.thread = None
        self.stop_signal = {}
        if start:
            self.run_start()

    def run_start(self):
        self.stop_signal = {}
        self.stop_flag = False
        self.queue = Queue(maxsize=self.maxsize) if self.queue is None else self.queue
        self.thread = Thread(target=self.show, daemon=True)
        self.thread.start()

    def run_stop(self):
        if self.thread is None:
            return
        for window_name in list(self.windows.keys()):
            # Check full
            if self.windows[window_name]['q'].full():
                self.windows[window_name]['q'].get()

            # put stop information to queue
            self.windows[window_name]['q'].put(None)
        self.stop_flag = True
        self.thread.join()

    def check_stop(self, window_name):
        if window_name in self.stop_signal:
            return self.stop_signal[window_name]
        return False

    def _check_window(self, window_name):
        # new window information in dict
        if window_name not in self.windows:
            self.stop_signal[window_name] = False
            self.windows[window_name] = {'q': Queue(self.maxsize), 'start': False}

    def put_frame(self, window_name, img):
        # Check stop
        if (window_name in self.stop_signal and self.stop_signal[window_name]) or window_name is None:
            return False

        # new a window
        self._check_window(window_name)

        # Check full
        if self.windows[window_name]['q'].full():
            self.windows[window_name]['q'].get()

        # put new image information
        self.windows[window_name]['q'].put(img)
        return True

    def show_img(self, window_name, img):
        """ Show image """
        # new a window
        self._check_window(window_name)
        if not self.windows[window_name]['start']:
            self.windows[window_name]['start'] = True
            cv2.namedWindow(window_name)

        # waitkey to show image
        if cv2.waitKey(1) & 0xFF == ord('q'):
            img = None

        # show image or close window
        if img is None:
            self.stop_signal[window_name] = True
            self.windows.pop(window_name)
            cv2.destroyWindow(window_name)
        else:
            cv2.imshow(window_name, img)

    def show(self):
        """ Show video streaming """
        while not (self.stop_flag and all(self.stop_signal)):
            # get image information
            show_window = 0
            for window_name in list(self.windows.keys()):
                if not self.windows[window_name]['q'].empty():
                    img = self.windows[window_name]['q'].get()

                    # new a window to show image
                    self.show_img(window_name, img)
                    show_window += 1
            if show_window == 0:
                time.sleep(0.1)

        # Stop the process
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        logger.info('Stop visualizer thread.')
