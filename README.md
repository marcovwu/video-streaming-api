# Video Streaming API (Beta)

This API provides a flexible and customizable framework for processing video streaming data. The API is designed to handle different video input sources, such as webcams, RTSP cameras, or pre-recorded videos, and to process the input data in real-time with customizable image processing strategies.

The API is composed of several modules, including `runner.py`, `dataset.py`, `manager.py`, `stream.py`, `writer.py`, and `strategy.py`. The runner and dataset modules are responsible for handling video input sources, while the `manager`, `stream`, `writer`, and `strategy` modules handle the processing of the input video data.

To get started with the API, users can extend their own image processing strategies from the `ImageProcessingStrategy` abstract class in `strategy.py`. They can then create a `Runner` instance and specify the video source and processing strategies to use. The API also supports multi-processing to handle high-throughput data processing requirements.

In addition, the API provides several utilities for naming the output files and directories, visualizing the input video stream, and controlling the frame rate of the output video. Users can also define their own rules for stopping the video streaming process.

## Installation

The API can be installed via pip in the future by running:
```
pip install video-streaming-api
```

## Usage

To use the API, first import the required modules:

```
from video_streaming_api.runner import StreamingRunner
from video_streaming_api.strategy import ImageProcessingStrategy
```

Then extend your own image processing strategies from `ImageProcessingStrategy` class and define your own processing flow. Create a `StreamingRunner` instance and specify the video source and processing strategies to use:

```
# init
streaming_runner = StreamingRunner(
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
streaming_runner.run()
```




