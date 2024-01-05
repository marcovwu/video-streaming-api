import unittest

from tests.create_youtube_to_rtsp import RTSPServerThread
from tests.strategy_example import CustomOnlyShowStrategy
from video_streaming.runner import StreamingRunner


class TestRTSPConnection(unittest.TestCase):

    def test_rtsp_connection(self):
        # 初始化 StreamingRunner 并执行测试
        streaming_runner = StreamingRunner(
            video_paths={
                0: {
                    'ip': "127.0.0.1", 'port': "8554", 'username': " ", 'password': " ",
                    'stream_name': "live.sdp", 'group': " ", 'channel': 'live2'
                }
            },
            vid_batch=1, div_fps=1, preproc=None, imgsz=(640, 640), save_dir='', vis_mode='all', video_sec=600,
            visualizer=None, end_title='', SYSDTFORMAT='%Y%m%d%H%M%S', YMDFORMAT='%Y%m%d000000', warnning=True,
            start=False, processing_strategy=CustomOnlyShowStrategy
        )
        streaming_runner.run()


if __name__ == '__main__':
    import sys

    # 解析命令行参数，查找是否提供了 youtube_url
    youtube_url_index = [i for i, arg in enumerate(sys.argv) if arg.startswith("youtube_url=")]
    if youtube_url_index:
        youtube_url = sys.argv[youtube_url_index[0]].split("=")[1]

        # 创建并启动 YouTubeToRTSPThread 线程
        youtube_to_rtsp_thread = RTSPServerThread(youtube_url, "rtsp://127.0.0.1:8554/live.sdp")
        youtube_to_rtsp_thread.start()
        input("Press Enter to continue capture from the RTSP server...\n")

        # 创建 TestRTSPConnection 类的实例并运行测试
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(TestRTSPConnection)
        unittest.TextTestRunner().run(suite)

        # 等待 youtube_to_rtsp_thread 完成
        youtube_to_rtsp_thread.stop_rtsp_server = True
        youtube_to_rtsp_thread.join()

        # 如果需要等待 youtube_to_rtsp_thread 完成再退出，可以使用下面的代码
        youtube_to_rtsp_thread.youtube_to_rtsp_complete.wait()
