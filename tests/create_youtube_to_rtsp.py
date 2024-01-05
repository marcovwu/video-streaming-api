import os
import cv2
import subprocess
import threading

from pytube import YouTube


def download_youtube_video(youtube_url, save_path='./', filename='test.mp4'):
    try:
        # 創建 YouTube 對象
        yt = YouTube(youtube_url)
        video_title, _ = os.path.splitext(yt.title)

        # 選擇最高質量的視頻流
        video_stream = yt.streams.get_highest_resolution()

        # 下載影片
        print(f"開始下載: {yt.title}")
        video_stream.download(output_path=save_path, filename=filename)
        print("下載完成!")
        return os.path.join(save_path, filename)

    except Exception as e:
        print(f"下載失敗: {str(e)}")


class RTSPServerThread(threading.Thread):
    def __init__(self, video_source=0, rtsp_url="rtsp://localhost:8554/live.sdp"):
        super().__init__()
        self.video_source = video_source
        self.rtsp_url = rtsp_url
        self.stop_server = threading.Event()

    def run_capture(self):
        # 開啟影片來源
        cap = cv2.VideoCapture(self.video_source)

        # 使用ffmpeg命令啟動RTSP伺服器
        cmd = [
            'ffmpeg',
            '-re',
            '-i', '-',
            '-vcodec', 'copy',
            '-acodec', 'copy',
            '-f', 'rtsp', self.rtsp_url
        ]

        # 使用管道連接 OpenCV 與 ffmpeg
        process = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)

        # 讀取影片並將每一幀寫入 ffmpeg 的 stdin 中
        while True:
            ret, frame = cap.read()
            if not ret or self.stop_server.is_set():
                break

            # 寫入 ffmpeg 的 stdin 中
            process.stdin.write(frame.tobytes().decode('latin-1'))

        # 關閉 stdin 以確保 ffmpeg 完全處理完所有輸入
        process.stdin.close()

        # 等待 ffmpeg 完成
        process.wait()

        # 釋放影片來源
        cap.release()

    def run(self):
        cmd = [
            'ffmpeg',
            '-re',
            '-i', self.video_source,
            '-vcodec', 'copy',
            '-acodec', 'copy',
            '-f', 'rtsp', self.rtsp_url
        ]
        print(' '.join(cmd))
        os.system(' '.join(cmd))


if __name__ == "__main__":
    youtube_video_url = "https://www.youtube.com/watch?v=GVuiftq3KsI&ab_channel=TimerHare"
    video_source = download_youtube_video(youtube_video_url, save_path='./', filename='test.mp4')
    print(f'YouTube Live Stream URL: {video_source}')

    # main
    rtsp_server = RTSPServerThread(video_source=video_source)
    rtsp_server.start()
    input("Press Enter to stop the RTSP server...\n")
    rtsp_server.stop_server.set()  # 設定stop_server事件
    rtsp_server.join()
