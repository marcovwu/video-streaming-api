import cv2
import sys
import time
import copy

from tqdm import tqdm
from pathlib import Path
from loguru import logger

if Path(__file__).parent not in sys.path:
    sys.path.append(str(Path(__file__).parent))
from processing.datasets import LoadBatchVideos
from processing.manager import VideoManagers
from processing.strategy import OnlyShowStrategy


class StreamingRunner:
    DEFINE_TEMPLATE = {"parent_folder": [], "start_time": "videoname"}

    def __init__(
        self, video_sources, video_defines=None, vid_batch=1, div_fps=1, preproc=None, imgsz=(640, 640), save_dir='./',
        vis_mode='write', queue_maxsize=10, vid_queue_maxsize=200, video_sec=600, visualizer=None, end_title='',
        SYSDTFORMAT='%Y%m%d%H%M%S', YMDFORMAT='%Y%m%d000000', warnning=True, start=False, close_prev_window=True,
        processing_strategy=OnlyShowStrategy
    ):
        self.video_sources, self.video_defines = StreamingRunner.update_video_info(video_sources, video_defines)
        if isinstance(self.video_sources, dict):
            # Create VideoManager
            self.dataset = None
            self.video_managers = VideoManagers.create(
                self.video_sources, self.video_defines, div_fps, save_dir, vis_mode, video_sec=video_sec,
                visualizer=visualizer, end_title=end_title, SYSDTFORMAT=SYSDTFORMAT, YMDFORMAT=YMDFORMAT,
                warn=warnning, queue_maxsize=queue_maxsize, vid_queue_maxsize=vid_queue_maxsize,
                close_prev_window=close_prev_window
            )
        else:
            # Create Dataset
            self.dataset = LoadBatchVideos(
                self.video_sources, self.video_defines, vid_batch, div_fps, save_dir, preproc, img_size=imgsz,
                video_sec=video_sec, vis_mode=vis_mode, SYSDTFORMAT=SYSDTFORMAT, YMDFORMAT=YMDFORMAT,
                visualizer=visualizer, queue_maxsize=queue_maxsize, vid_queue_maxsize=vid_queue_maxsize,
                close_prev_window=close_prev_window
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
        manager.stop()
        manager.stream_thread.join()
        if manager.vid_thread is not None and not manager.vid_writer.stop_flag:
            manager.vid_writer.put_frame(None, '', '', -1)
            manager.vid_thread.join()

    @staticmethod
    def update_video_info(video_sources, video_defines):
        if video_defines is None:
            if isinstance(video_sources, str):
                video_defines = copy.deepcopy(StreamingRunner.DEFINE_TEMPLATE)
            elif isinstance(video_sources, list):
                video_defines = [copy.deepcopy(StreamingRunner.DEFINE_TEMPLATE) for _ in video_sources]
            elif isinstance(video_sources, dict):
                video_defines = {_id: copy.deepcopy(StreamingRunner.DEFINE_TEMPLATE) for _id in video_sources.keys()}
            else:
                logger.error("Error video source: %s !!" % video_sources)
        return video_sources, video_defines

    def _start(self):
        # Start the video manager
        if self.video_managers is not None:
            for _, manager in self.video_managers.items():
                manager.start()
        self.stop_flag = False
        self.is_need_start = False

    def write_video(self, manager, result_frame, img_info):
        if manager.vid_writer.stop_flag:
            self.predictor_stop_flag[img_info["id"]] = True
            return
        vid_info = img_info["dt"], img_info["cur_time"], img_info["cur_sec"]
        # Init VideoWriter in new epoch
        if img_info["is_newepoch"]:
            manager.vid_writer.put_frame(None, *vid_info)
        # Current Result
        manager.vid_writer.put_frame(result_frame, *vid_info)
        # Stop VideoWrite in last frames
        if img_info["is_epochfinal"]:
            manager.vid_writer.put_frame(None, *vid_info)

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
                    manager.stop()
                    continue

                # show
                if w and manager.vid_thread is not None:
                    self.write_video(manager, img_info["raw_img"], img_info)
                    # cur_date_time, cur_second, cur_time, _ = manager.stream.get_cur_info(img_info['cur_sec'])
                    # manager.vid_writer.put_frame(img_info["raw_img"], cur_date_time, cur_time, cur_second, vis='a')

            pbar.set_description(('%20.4f' * 2) % (sys_info['infer'], time.time() - sys_info['start']))

        # Stop the video manager
        time.sleep(1)
        for _, manager in self.dataset.video_managers.items():
            StreamingRunner.stop_manager(manager)

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
                img_info = {"img": img, "frame": frames[k], "info": info}

                # Pre-processing batch images
                output = self.processing_strategy.pre_process_images(img_info, img, sys_info)

                # processing image and show output information in image
                w = self.processing_strategy.process_image(manager, (ret, frames[k], img_info, info, output))
                if self.processing_strategy.check_stop(manager, info):
                    manager.stop()
                    continue

                # show
                if w and manager.vid_thread is not None:
                    cur_date_time, cur_second, cur_time, _ = manager.stream.get_cur_info(info['sec'])
                    manager.vid_writer.put_frame(img_info["img"], cur_date_time, cur_time, cur_second, vis='a')

        # Stop the video manager
        time.sleep(1)
        for _, manager in self.video_managers.items():
            StreamingRunner.stop_manager(manager)

        # close main infer thread
        cv2.destroyAllWindows()

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


def Example():
    # init
    StreamingRunner.DEFINE_TEMPLATE = {"parent_folder": [None, None, None], "start_time": "current"}
    streaming_runner = StreamingRunner(
        video_sources=[
            {
                'ip': "zephyr.rtsp.stream", 'port': " ", 'username': " ", 'password': " ",
                'stream_name': "pattern?streamKey=87a01fc49801f9771ecd0bb7666d6c04", 'group': "out",
                'channel': 'ch1'
            },  # rtsp://zephyr.rtsp.stream/pattern?streamKey=87a01fc49801f9771ecd0bb7666d6c04
            {
                'ip': "zephyr.rtsp.stream", 'port': " ", 'username': " ", 'password': " ",
                'stream_name': "pattern?streamKey=87a01fc49801f9771ecd0bb7666d6c04", 'group': "out",
                'channel': 'ch2'
            },  # rtsp://zephyr.rtsp.stream/pattern?streamKey=87a01fc49801f9771ecd0bb7666d6c04
        ],  # Dictionary that uses VideoManagers. List (["/path_to_your_video/...mp4", ...]) will use LoadBatchVideos.
        vid_batch=1,  # Sets the batch in each stream.
        div_fps=1,  # Used to control inference FPS = original FPS / div_fps.
        preproc=None,  # Pre-processing Transformer for images.
        imgsz=(640, 640),  # Use to pre-process image to this size.
        save_dir='./',  # Used to write video in this format: /save_dir/group/channel/YMDFORMAT/SYSDTFORMAT.mp4
        vis_mode='all',  # 'show': show video streaming in window, 'write': only write into output video, 'all': both.
        queue_maxsize=10,  # Maximum size of the queue for pre-reading video streaming
        vid_queue_maxsize=200,  # Maximum size of the queue for writing video streaming
        video_sec=3600,  # Only used to record stream.video_sec and calculate stream.epochframes in real-time video.
        visualizer=None,  # A unique instance to show the video streaming.
        end_title='',  # Used by logger.info after the new video has been written to output from writer.
        SYSDTFORMAT='%Y%m%d%H%M%S',  # Used to name the datetime.mp4.
        YMDFORMAT='%Y%m%d000000',  # Used to name the date_time folder.
        warnning=True,  # Show warnings in the terminal. Set to False to skip showing information.
        start=False,  # Automatically start capturing images from video streaming after successful initialization.
        close_prev_window=True,  # Close previous window when new window be opened.
        processing_strategy=OnlyShowStrategy  # Create strategy instance by extending the ImageProcessingStrategy class.
    )

    # main
    streaming_runner.run()


if __name__ == "__main__":
    Example()
