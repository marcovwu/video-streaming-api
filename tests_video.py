import os
import sys
import unittest
import datetime

from tests.create_youtube_to_rtsp import download_youtube_video
from video_streaming.processing.strategy import OnlyShowStrategy
from video_streaming.runner import StreamingRunner


class TestStreaming(unittest.TestCase):

    def setUp(self):
        self.video_source = self.get_video_info("https://www.youtube.com/watch?v=GVuiftq3KsI&ab_channel=TimerHare")

    # def test_one_streaming(self):
    #     if os.path.exists(self.video_source):
    #         streaming_runner = StreamingRunner(
    #             video_sources=self.video_source,
    #             vid_batch=1, div_fps=1, preproc=None, imgsz=(640, 640), save_dir='./', vis_mode='show', video_sec=600,
    #             visualizer=None, end_title='', SYSDTFORMAT='%Y%m%d%H%M%S', YMDFORMAT='%Y%m%d000000', warnning=True,
    #             start=False, processing_strategy=OnlyShowStrategy
    #         )
    #         streaming_runner.run()

    # def test_dict_streaming(self):
    #     if os.path.exists(self.video_source):
    #         streaming_runner = StreamingRunner(
    #             video_sources={0: self.video_source},
    #             vid_batch=1, div_fps=1, preproc=None, imgsz=(640, 640), save_dir='./', vis_mode='show', video_sec=600,
    #             visualizer=None, end_title='', SYSDTFORMAT='%Y%m%d%H%M%S', YMDFORMAT='%Y%m%d000000', warnning=True,
    #             start=False, processing_strategy=OnlyShowStrategy
    #         )
    #         streaming_runner.run()

    def test_batch_streaming(self):
        if os.path.exists(self.video_source):
            streaming_runner = StreamingRunner(
                video_sources=[self.video_source, self.video_source],
                vid_batch=1, div_fps=1, preproc=None, imgsz=(640, 640), save_dir='./', vis_mode='show', video_sec=600,
                visualizer=None, end_title='', SYSDTFORMAT='%Y%m%d%H%M%S', YMDFORMAT='%Y%m%d000000', warnning=True,
                start=False, processing_strategy=OnlyShowStrategy
            )
            streaming_runner.run()

    def test_rtsp_streaming(self):
        if os.path.exists(self.video_source):
            streaming_runner = StreamingRunner(
                video_sources={
                    0: {
                        'ip': "zephyr.rtsp.stream", 'port': " ", 'username': " ", 'password': " ",
                        'stream_name': "pattern?streamKey=87a01fc49801f9771ecd0bb7666d6c04", 'group': "out",
                        'channel': 'ch1'
                    },  # rtsp://zephyr.rtsp.stream/pattern?streamKey=87a01fc49801f9771ecd0bb7666d6c04
                    1: {
                        'ip': "zephyr.rtsp.stream", 'port': " ", 'username': " ", 'password': " ",
                        'stream_name': "pattern?streamKey=87a01fc49801f9771ecd0bb7666d6c04", 'group': "out",
                        'channel': 'ch2'
                    }  # rtsp://zephyr.rtsp.stream/pattern?streamKey=87a01fc49801f9771ecd0bb7666d6c04
                },
                vid_batch=1, div_fps=1, preproc=None, imgsz=(640, 640), save_dir='./', vis_mode='all', video_sec=600,
                visualizer=None, end_title='', SYSDTFORMAT='%Y%m%d%H%M%S', YMDFORMAT='%Y%m%d000000', warnning=True,
                start=False, processing_strategy=OnlyShowStrategy
            )
            streaming_runner.run()

    def get_video_info(self, youtube_url=None):
        if youtube_url is None:
            start_with = "youtube_url="
            youtube_url_index = [i for i, arg in enumerate(sys.argv) if arg.startswith(start_with)]
            if youtube_url_index:
                youtube_url = sys.argv[youtube_url_index[0]][len(start_with):]
        if isinstance(youtube_url, str):
            current = datetime.datetime.now()
            video_source = [
                os.path.join('tests', 'group', 'channel', current.strftime('%Y0101000000')),
                current.strftime('%Y0101000000') + '.mp4']
            os.makedirs(video_source[0], exist_ok=True)
            video_source = download_youtube_video(youtube_url, save_path=video_source[0], filename=video_source[1])
            print(f'YouTube Live Stream URL: {video_source}')
            return video_source
        return ""


if __name__ == "__main__":
    unittest.main()
