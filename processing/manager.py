import os

from loguru import logger
from threading import Thread

from videos.stream import Stream
from videos.writer import VideoWriter


class VideoManagers:
    _instances = {}

    def __init__(self, mode, vis_mode, stream, stream_thread, save_dir, visualizer, end_title):
        # update parameters
        self.mode = mode
        self.vis_mode = vis_mode
        self.stream = stream
        self.stream_thread = stream_thread
        self.save_dir = save_dir
        self.visualizer = visualizer
        # TODO: maxsize
        self.vid_writer = VideoWriter(
            self.save_dir, stream.group, stream.channel, stream.date_time, stream.start_time, stream.infer_fps,
            stream.width, stream.height, vid_reload=True if mode == 'webcam' else False, title=end_title,
            visualizer=self.visualizer
        )
        # vis mode thread
        if self.vis_mode == 'write':
            self.vid_thread = Thread(target=self.vid_writer.process_video, args=(True, False), daemon=True)
        elif self.vis_mode == 'show':
            self.vid_thread = Thread(target=self.vid_writer.process_video, args=(False, True), daemon=True)
        elif self.vis_mode == 'all':
            self.vid_thread = Thread(target=self.vid_writer.process_video, args=(True, True), daemon=True)
        else:
            self.vid_thread = None
            logger.warning("Current vis_mode is %s, will ignore to build video writer !!" % self.vis_mode)
        self.epoch = {'e': 0, 'n': True, 'f': False}

    @staticmethod
    def get_mode(video_path):
        mode = 'video' if isinstance(video_path, list) or isinstance(video_path, str) else 'webcam'
        return mode

    def stop(self, stop_stream=False):
        if self.mode == 'video':
            self.stream.stop(stop_stream)
        else:
            self.stream.stop_signal = True

        if self.vid_writer is not None and not self.vid_writer.stop_flag:
            self.vid_writer.put_frame(None, '', '', -1)

    def start(self):
        # stream thread
        if self.stream_thread is not None:
            self.stream_thread.start()

        # writer threads
        if self.vid_thread is not None:
            self.vid_thread.start()

    @classmethod
    def create(
        cls, video_paths, div_fps, save_dir, vis_mode, video_sec=0,
        visualizer=None, end_title='', SYSDTFORMAT='', YMDFORMAT='', warn=True
    ):
        """
        Args:
            video_paths: {id: video_path}
        """
        for k, video_path in video_paths.items():
            mode = cls.get_mode(video_path)
            # check path
            if isinstance(video_path, str) and (not video_path or not os.path.exists(video_path)):
                continue

            # load stream
            stream, stream_thread = Stream.load(
                mode, video_path, div_fps, save_dir, video_sec=video_sec,
                SYSDTFORMAT=SYSDTFORMAT, YMDFORMAT=YMDFORMAT, warn=warn
            )

            # check stream was opened
            if not stream.capture.isOpened():
                continue

            # get manager
            cls._instances[k] = VideoManagers(mode, vis_mode, stream, stream_thread, save_dir, visualizer, end_title)
        return cls._instances


if __name__ == '__main__':
    # Create VideoManager
    video_managers = VideoManagers.create(
        {0: {
            'ip': "192.168.0.210", 'port': "8554", 'username': "admin", 'password': "password", 'content': "ch1",
            'group': "0929_full", 'channel': 'ch1'
        }},
        div_fps=2, save_dir='', vis_mode='show', video_sec=70, visualizer=None, end_title='',
        SYSDTFORMAT='%Y%m%d%H%M%S', YMDFORMAT='%Y%m%d000000'
    )

    # Start the video manager
    for k, manager in video_managers.items():
        manager.start()

    # Show video streaming
    frames = {}
    while not all([m.stream.stop_stream for m in video_managers.values()]):
        for k, manager in video_managers.items():
            # init frame
            if k not in frames:
                frames[k] = 1

            # read new frame
            ret, frames[k], img, info = manager.stream.read(frames[k])
            if not ret or img is None:
                continue

            # TODO: you can add your image recongnitionin in here
            """
            output = model(img)
            run_event_generator(img, output)
            img = visualize(output)
            ...
            """
            # TODO: you can set stop rules by yourself
            if manager.vid_writer.stop_flag:
                manager.stop(stop_stream=True)
                continue

            # show
            cur_date_time, cur_second, cur_time, vid_time = manager.stream.get_cur_info(info['sec'])
            manager.vid_writer.put_frame(img, cur_date_time, cur_time, cur_second, vis='a')

    # Stop the video manager
    for k, manager in video_managers.items():
        manager.stop(stop_stream=True)
        if not manager.vid_writer.stop_flag:
            manager.vid_writer.put_frame(None, '', '', -1)
            manager.vid_thread.join()
