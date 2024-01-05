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

    def test_process_streaming(self):
        if os.path.exists(self.video_source):
            streaming_runner = StreamingRunner(
                video_paths={
                    0: self.video_source
                },
                vid_batch=1, div_fps=1, preproc=None, imgsz=(640, 640), save_dir='', vis_mode='all', video_sec=600,
                visualizer=None, end_title='', SYSDTFORMAT='%Y%m%d000000', YMDFORMAT='%Y%m%d%H%M%S', warnning=True,
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
