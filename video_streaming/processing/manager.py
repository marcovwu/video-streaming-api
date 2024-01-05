import os

from loguru import logger
from threading import Thread

from .stream import Stream
from .writer import VideoWriter


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
            self.save_dir, stream.video_define, stream.start_time, stream.infer_fps,
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
        cls, video_sources: dict, video_defines: dict, div_fps, save_dir, vis_mode, video_sec=0,
        visualizer=None, end_title='', SYSDTFORMAT='', YMDFORMAT='', warn=True
    ):
        """
        Args:
            video_infos: {id: ...} TODO
        """
        for k, video_source in video_sources.items():
            video_define = video_defines[k]
            mode = cls.get_mode(video_source)
            # check path
            if isinstance(video_source, str) and (not video_source or not os.path.exists(video_source)):
                continue

            # load stream
            stream, stream_thread = Stream.load(
                mode, video_source, video_define, div_fps, save_dir, video_sec=video_sec,
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
            'ip': "192.168.66.28", 'port': "554", 'username': "Admin", 'password': "1234",
            'stream_name': "ch1", 'group': "TR", 'channel': 'Vivocam1'
        }},
        {0: {"parent_folder": [None, None, None], "start_time": "videoname"}},
        div_fps=2, save_dir='', vis_mode='show', video_sec=600, visualizer=None, end_title='',
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
