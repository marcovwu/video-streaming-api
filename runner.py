from videos.manager import VideoManagers
from videos.strategy import OnlyShowStrategy


class Runner:
    def __init__(
        self, video_paths, div_fps=1, save_dir='', vis_mode='write', video_sec=600, visualizer=None, start=False,
        end_title='', SYSDTFORMAT='%Y%m%d%H%M%S', YMDFORMAT='%Y%m%d000000', warnning=True,
        processing_strategy=OnlyShowStrategy
    ):
        # Create VideoManager
        self.video_managers = VideoManagers.create(
            video_paths, div_fps, save_dir, vis_mode, video_sec, visualizer, end_title, SYSDTFORMAT, YMDFORMAT, warnning
        )
        self.processing_strategy = processing_strategy
        if start:
            self._start()
        else:
            self.stop_flag = True
            self.is_need_start = True

    @staticmethod
    def stop_manager(manager):
        manager.stop(stop_stream=True)
        manager.stream_thread.join()
        if manager.vid_thread is not None and not manager.vid_writer.stop_flag:
            manager.vid_writer.put_frame(None, '', '', -1)
            manager.vid_thread.join()

    def _start(self):
        # Start the video manager
        for _, manager in self.video_managers.items():
            manager.start()
        self.stop_flag = False
        self.is_need_start = False

    def run(self):
        if self.is_need_start:
            self._start()

        # Show video streaming
        frames = {}
        while not all([m.stream.stop_stream for m in self.video_managers.values()]):
            for k, manager in self.video_managers.items():
                # init frame
                if k not in frames:
                    frames[k] = 1

                # read new frame
                ret, frames[k], img, info = manager.stream.read(frames[k])
                if not ret or img is None:
                    continue

                # processing image and show output information in image
                w = self.processing_strategy.process_image(manager, (ret, frames[k], img, info))
                if self.processing_strategy.check_stop(manager):
                    manager.stop(stop_stream=True)
                    continue

                # show
                if w and manager.vid_thread is not None:
                    cur_date_time, cur_second, cur_time, _ = manager.stream.get_cur_info(info['sec'])
                    manager.vid_writer.put_frame(img, cur_date_time, cur_time, cur_second, vis='a')

        # Stop the video manager
        for k, manager in self.video_managers.items():
            Runner.stop_manager(manager)
        self.stop_flag = True


if __name__ == "__main__":
    # init
    runner = Runner(
        video_paths={
            0: {
                'ip': "192.168.0.210", 'port': "8554", 'username': "admin", 'password': "password", 'content': "ch1",
                'group': "0929_full", 'channel': 'ch1'
            }
        },
        div_fps=1,  # Used to control inference FPS = original FPS / div_fps.
        save_dir='',  # Used to write video in this format: /save_dir/group/channel/YMDFORMAT/SYSDTFORMAT.mp4
        vis_mode='all',  # 'show': show video streaming in window, 'write': only write into output video, 'all': both.
        # video_sec=60,  # Only used to record stream.video_sec and calculate stream.epochframes in real-time video.
        # visualizer=None,  # A unique instance to show the video streaming.
        # start=False,  # Automatically start capturing images from video streaming after successful initialization.
        # end_title='',  # Used by logger.info after the new video has been written to output from writer.
        SYSDTFORMAT='%Y%m%d%H%M%S',  # Used to name the datetime.mp4.
        YMDFORMAT='%Y%m%d000000',  # Used to name the date_time folder.
        warning=True,  # Show warnings in the terminal. Set to False to skip showing information.
        processing_strategy=OnlyShowStrategy  # Create strategy instance by extending the ImageProcessingStrategy class.
    )

    # main
    runner.run()
