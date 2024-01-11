# Video Streaming API (Beta)

This API provides a flexible and customizable framework for processing video streaming data. The API is designed to handle different video input sources, such as webcams, RTSP cameras, or pre-recorded videos, and to process the input data in real-time with customizable image processing strategies.

The API is composed of several modules, including `runner.py`, `dataset.py`, `manager.py`, `stream.py`, `writer.py`, and `strategy.py`. The runner and dataset modules are responsible for handling video input sources, while the `manager`, `stream`, `writer`, and `strategy` modules handle the processing of the input video data.

To get started with the API, users can extend their own image processing strategies from the `ImageProcessingStrategy` abstract class in `strategy.py`. They can then create a `StreamingRunner` instance and specify the video source and processing strategies to use. The API also supports multi-processing to handle high-throughput data processing requirements.

In addition, the API provides several utilities for naming the output files and directories, visualizing the input video stream, and controlling the frame rate of the output video. Users can also define their own rules for stopping the video streaming process.

## Installation

The API can be installed via pip in the future by running:
```css
pip install video-streaming-api
```

## Usage

To use the API, first import the required modules:

### Import Required Modules

```python
from video_streaming.runner import StreamingRunner
from video_streaming.processing.strategy import ImageProcessingStrategy
```

### Define Video Sources
Define the video sources with their respective configurations:
```python
# Example1: Dictionary that uses VideoManagers.
video_sources = {
    0: {
        'ip': "192.168.200.1",
        'port': "8554",
        'username': "Admin1",
        'password': "1234",
        'stream_name': "ch1",
        'group': "Taiwan",
        'channel': 'Taipei'
    },
    1: {
        'ip': "192.168.201.1",
        'port': "8554",
        'username': "Admin2",
        'password': "5678",
        'stream_name': "ch2",
        'group': "Taiwan",
        'channel': 'Taipei'
    },
    # Add more video sources as needed...
}

# Example2: List (["/path_to_your_video/...mp4", ...]) will use LoadBatchVideos.
video_sources = [
    "your_video_root1/videoname1.mp4",
    "your_video_root2/videoname2.mp4",
    # Add more video sources as needed...
]
```

### (Optional) Define Video Configuration

Choose one of the following approaches:

#### 1. Using Base Template
If multiple video sources share the same configuration, you can modify the `DEFINE_TEMPLATE` in `StreamingRunner` as a base:

```python
# Define a base template for video configuration.
# Video Defines:
#   - If parent_folder is [None, None], the save_folder will automatically read the source directory.
#   - If video_source is 'your_dir/abc/def/videoname.mp4', save_folder will be 'save_dir/abc/def'.
#   - Start time choices:
#     - 'current': use the current time and SYSDTFORMAT as the video name.
#     - 'datetime': use the video source's video name as datetime.
#     - 'videoname': directly use the video name as the video name.
StreamingRunner.DEFINE_TEMPLATE = {
    "parent_folder": [None, ...],  # For example: If parent_folder is [None, None], save_folder will automatically read the source directory.
    "start_time": "datetime"  # Start time choices: 'current', 'datetime', 'videoname'.
}

# The video configurations will automatically align with the video_sources using the base template.
video_defines = {
    0: {**StreamingRunner.DEFINE_TEMPLATE, "parent_folder": [], "start_time": "current"},
    1: {**StreamingRunner.DEFINE_TEMPLATE, "parent_folder": ["custom_path"], "start_time": "datetime"},
}
```

#### 2. Directly Define Configurations
Alternatively, you can directly define video_defines to align the configurations with each video source in the video_sources dictionary.
```python
video_defines = {
    0: {"parent_folder": [None, None], "start_time": "current"},
    1: {"parent_folder": [None], "start_time": "datetime"},
    # Add more configurations as needed...
}
```

### Streaming Runner
Then extend your own image processing strategies from `ImageProcessingStrategy` class and define your own processing flow. Create a `StreamingRunner` instance and specify the video source and processing strategies to use:
```python
# Initialize
streaming_runner = StreamingRunner(
    video_sources,
    video_defines=video_defines,  # default: {"parent_folder": [], "start_time": "current"}
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

# Run
streaming_runner.run()
```
