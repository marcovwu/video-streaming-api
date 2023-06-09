import cv2
import sys
import time

from tqdm import tqdm
from pathlib import Path
from loguru import logger

if Path(__file__).parent not in sys.path:
    sys.path.append(Path(__file__).parent)
from processing.datasets import LoadBatchVideos
from processing.manager import VideoManagers
from processing.strategy import OnlyShowStrategy


class Runner:
    def __init__(
        self, video_paths, vid_batch=1, div_fps=1, preproc=None, imgsz=(640, 640), save_dir='', vis_mode='write',
        video_sec=600, visualizer=None, end_title='', SYSDTFORMAT='%Y%m%d%H%M%S', YMDFORMAT='%Y%m%d000000',
        warnning=True, start=False, processing_strategy=OnlyShowStrategy
    ):
        if isinstance(video_paths, dict):
            # Create VideoManager
            self.dataset = None
            self.video_managers = VideoManagers.create(
                video_paths, div_fps, save_dir, vis_mode, video_sec,
                visualizer, end_title, SYSDTFORMAT, YMDFORMAT, warnning
            )
        else:
            # Create Dataset
            self.dataset = LoadBatchVideos(
                video_paths, vid_batch, div_fps, save_dir, preproc, img_size=imgsz, video_sec=video_sec,
                vis_mode=vis_mode, SYSDTFORMAT=SYSDTFORMAT, YMDFORMAT=YMDFORMAT, visualizer=visualizer
            )
            self.video_managers = None
        self.processing_strategy = processing_strategy

        # Initialize status
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
        if self.video_managers is not None:
            for _, manager in self.video_managers.items():
                manager.start()
        self.stop_flag = False
        self.is_need_start = False

    def process_batch_images(self):
        # Iter video streaming
        pbar = tqdm(enumerate(self.dataset), total=None if any([
            True if m.mode == 'webcam' else False for m in self.dataset.video_managers.values()
        ]) else len(self.dataset))
        logger.info(self.dataset.title + self.dataset.end_title)
        for _, (imgs_info, imgs) in pbar:
            if imgs is None:
                continue
            sys_info = {'start': time.time(), 'infer': 0.0}

            # Pre-processing batch images
            outputs = self.processing_strategy.pre_process_images(imgs_info, imgs, sys_info)

            # Processing batch images
            for i, img_info in enumerate(imgs_info):

                # processing image and show output information in image
                manager = self.dataset.video_managers[img_info["id"]]
                output = outputs[i] if i <= len(outputs) - 1 else None
                w = self.processing_strategy.process_image(manager, (img_info, imgs[i], output))
                if self.processing_strategy.check_stop(manager, img_info):
                    manager.stop(stop_stream=True)
                    continue

                # show
                if w and manager.vid_thread is not None:
                    cur_date_time, cur_second, cur_time, _ = manager.stream.get_cur_info(img_info['cur_sec'])
                    manager.vid_writer.put_frame(img_info["raw_img"], cur_date_time, cur_time, cur_second, vis='a')

            pbar.set_description(('%20.4f' * 2) % (sys_info['infer'], time.time() - sys_info['start']))

        # close main infer thread
        cv2.destroyAllWindows()

    def process_image(self):
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
                sys_info = {'start': time.time(), 'infer': 0.0}
                img_info = {"frame": frames[k], "info": info}

                # Pre-processing batch images
                output = self.processing_strategy.pre_process_images(img_info, img, sys_info)

                # processing image and show output information in image
                w = self.processing_strategy.process_image(manager, (ret, frames[k], img, info, output))
                if self.processing_strategy.check_stop(manager, info):
                    manager.stop(stop_stream=True)
                    continue

                # show
                if w and manager.vid_thread is not None:
                    cur_date_time, cur_second, cur_time, _ = manager.stream.get_cur_info(info['sec'])
                    manager.vid_writer.put_frame(img, cur_date_time, cur_time, cur_second, vis='a')

        # Stop the video manager
        for _, manager in self.video_managers.items():
            Runner.stop_manager(manager)

    def run(self):
        # Start process
        if self.is_need_start:
            self._start()

        # Process images
        if self.dataset is not None:
            self.process_batch_images()
        elif self.video_managers is not None:
            self.process_image()

        self.stop_flag = True


if __name__ == "__main__":
    # init
    runner = Runner(
        video_paths={
            0: {
                'ip': "192.168.66.28", 'port': "554", 'username': "Admin", 'password': "1234",
                'stream_name': "ch5", 'group': "TR", 'channel': 'Vivocam1'
            }
        },  # Dictionary that uses VideoManagers. List (["/path_to_your_video/...mp4", ...]) will use LoadBatchVideos.
        vid_batch=1,  # Sets the batch in each stream.
        div_fps=1,  # Used to control inference FPS = original FPS / div_fps.
        preproc=None,  # Pre-processing Transformer for images.
        imgsz=(640, 640),  # Use to pre-process image to this size.
        save_dir='',  # Used to write video in this format: /save_dir/group/channel/YMDFORMAT/SYSDTFORMAT.mp4
        vis_mode='all',  # 'show': show video streaming in window, 'write': only write into output video, 'all': both.
        video_sec=600,  # Only used to record stream.video_sec and calculate stream.epochframes in real-time video.
        visualizer=None,  # A unique instance to show the video streaming.
        end_title='',  # Used by logger.info after the new video has been written to output from writer.
        SYSDTFORMAT='%Y%m%d%H%M%S',  # Used to name the datetime.mp4.
        YMDFORMAT='%Y%m%d000000',  # Used to name the date_time folder.
        warnning=True,  # Show warnings in the terminal. Set to False to skip showing information.
        start=False,  # Automatically start capturing images from video streaming after successful initialization.
        processing_strategy=OnlyShowStrategy  # Create strategy instance by extending the ImageProcessingStrategy class.
    )

    # main
    runner.run()
