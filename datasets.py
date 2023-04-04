import os
import glob
import numpy as np

from pathlib import Path

from videos.manager import VideoManagers


class LoadBatchVideos:
    # include image suffixes
    IMG_FORMATS = 'bmp', 'dng', 'jpeg', 'jpg', 'mpo', 'png', 'tif', 'tiff', 'webp'
    # include video suffixes
    VID_FORMATS = 'asf', 'avi', 'gif', 'm4v', 'mkv', 'mov', 'mp4', 'mpeg', 'mpg', 'ts', 'wmv'

    def __init__(
        self, path, vid_batch=1, div_fps=1, save_dir='', preproc=None, img_size=(640, 640), many_folder=False,
        video_sec=70, vis_mode='write', SYSDTFORMAT='%Y%m%d%H%M%S', YMDFORMAT='%Y%m%d000000', visualizer=None
    ):
        # Initialize variables
        self.div_fps = div_fps
        self.preproc = preproc
        self.img_size = img_size
        self.vid_batch = vid_batch
        self.visualizer = visualizer
        self.end_title = '\n------------------------------------------------' + (
            '\n' + '%20s' * 2) % ('Infer Time', 'Total Time')
        # get video paths
        self.files = LoadBatchVideos.build_videos_dict(path, many_folder=many_folder)

        # Create video managers
        self.video_managers = VideoManagers.create(
            self.files, div_fps, save_dir, vis_mode, video_sec=video_sec, visualizer=visualizer,
            end_title=self.end_title, SYSDTFORMAT=SYSDTFORMAT, YMDFORMAT=YMDFORMAT
        )
        self._init_from_manager()

    @staticmethod
    def get_video_paths(p, many_folder):
        if '*' in p:
            files = sorted(glob.glob(p, recursive=True))  # glob
        elif os.path.isdir(p):
            if many_folder:
                files = sorted(glob.glob(os.path.join(p, '*/img/*.*')))  # dir
            else:
                if glob.glob(os.path.join(p, '*.*')):
                    files = sorted(glob.glob(os.path.join(p, '*.*')))  # dir
                else:
                    files = sorted(glob.glob(os.path.join(p, '*/*.*')))  # dir
        elif os.path.isfile(p):
            files = [p]  # files
        else:
            raise Exception(f'ERROR: {p} does not exist')
        return [x for x in files if x.split('.')[-1].lower() in LoadBatchVideos.VID_FORMATS]

    @staticmethod
    def build_videos_dict(path, many_folder=False):
        files = {}
        if isinstance(path, list):
            for i, p in enumerate(path):
                if isinstance(path, str):
                    p = str(Path(p).resolve())  # os-agnostic absolute path
                    files[i] = (p, many_folder)
                else:
                    files[i] = p
        else:
            p = str(Path(path).resolve())  # os-agnostic absolute path
            files[0] = LoadBatchVideos.get_video_paths(p, many_folder)
        return files

    @staticmethod
    def frame_counter(curframe, epochframe):
        """ Transfer the stream real frame to curframe in an epoch """
        frame = curframe % epochframe
        if curframe % epochframe == 0:
            frame = epochframe
        return frame

    def _init_from_manager(self):
        self.batch = len(self.video_managers)

        # setting the title for show
        self.title = ('\n' + '%15s' * 3) % ('Group', 'Channel', 'Video')
        for _, m in self.video_managers.items():
            self.title += ('\n' + '%15s' * 3) % (m.stream.group, m.stream.channel, m.vid_writer.start_time)

    def _update_epoch(self, k, manager):
        epoch = int(self.frames[k] / manager.stream.epochframes)
        if epoch > manager.epoch['e']:
            if self.frames[k] % manager.stream.epochframes == 0:
                manager.epoch['n'], manager.epoch['f'] = False, True
            else:
                manager.epoch = {'e': epoch, 'n': True, 'f': False}
        else:
            manager.epoch = {'e': epoch, 'n': False, 'f': False}

    def stop(self, k, stop_stream=False):
        self.video_managers[k].stop(stop_stream=stop_stream)

    def __iter__(self):
        self.frames = {}
        self.finalframes = {}
        # start video manager
        for k, video_manager in self.video_managers.items():
            self.frames[k] = 0
            self.finalframes[k] = 0
            video_manager.start()

        # show image
        if self.visualizer is not None:
            self.visualizer.run_start()
        return self

    def __next__(self):
        if self.batch == 0 or all([m.stream.stop_stream for m in self.video_managers.values()]):
            # close dataset video thread
            for k, manager in self.video_managers.items():
                if manager.vid_thread is not None and not manager.vid_writer.stop_flag:
                    manager.vid_writer.put_frame(None, '', '', -1)
                    manager.vid_thread.join()
            raise StopIteration

        img0s, imgs, inx = [], None, []
        for k, manager in self.video_managers.items():
            if manager.stream.capture.isOpened():
                for _ in range(self.vid_batch):
                    # Load Image
                    ret, self.frames[k], img, info = manager.stream.read(self.frames[k])
                    if not ret or img is None:
                        continue

                    # Concatenate Image Information
                    img0s.append(img)
                    if self.preproc is not None:
                        img, _ = self.preproc(img, None, self.img_size)
                    if imgs is None:
                        imgs = np.expand_dims(img, 0)
                    else:
                        imgs = np.concatenate((imgs, np.expand_dims(img, 0)), axis=0)

                    # Calculate Epoch Frame
                    self._update_epoch(k, manager)

                    # Record Information
                    self.finalframes[k] = LoadBatchVideos.frame_counter(self.frames[k], manager.stream.epochframes)
                    inx.append((k, self.finalframes[k], *manager.stream.get_cur_info(info['sec']), info))
        return inx, img0s, imgs

    def __len__(self):
        return int(np.ceil(max([
            m.stream.maxframes for m in self.video_managers.values()]) / self.vid_batch / self.div_fps)
        ) if len(self.video_managers.values()) else 0
