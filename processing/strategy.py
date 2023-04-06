import os
import cv2

from loguru import logger

from abc import ABC, abstractmethod


class ImageProcessingStrategy(ABC):
    @abstractmethod
    def pre_process_images(images_info, images, system_info):
        """ Only use to inference the batch images from dataset
            Implement your pre-process flow here, for example:
            - Perform some image processing on the input image
            - Generate some events based on the processed image
            - Plot the output information into image

        Args:
            images_info: An dictionary of the images informations.
            images: A cv2 array of the input images.
            system_info: A dictionary of the system informations. (Use to update timer output)

        Returns:
            A tuple output will send to process_image.
        """
        return tuple()

    @abstractmethod
    def process_image(manager, image_info):
        """ Implement your process flow here, for example:
            - Perform some image processing on the input image
            - Generate some events based on the processed image
            - Plot the output information into image

        Args:
            manager: An instance of the processing manager class.
            image_info: A dictionary containing information about the input image.

        Returns:
            A boolean indicating whether the image needs to be shown or written in the next step.
        """
        return True

    @abstractmethod
    def check_stop(manager, image_info):
        """ Define your rules for stopping the current video streaming here.

        Args:
            manager: An instance of the processing manager class.

        Returns:
            A boolean indicating whether to stop the video streaming.
        """
        return False


class OnlyShowStrategy(ImageProcessingStrategy):
    def pre_process_images(images_info, images, system_info):
        return tuple()

    def process_image(manager, image_info):
        return True

    def check_stop(manager, image_info):
        if manager.vid_writer.stop_flag:
            return True
        return False


class CaptureBackgroundStrategy(ImageProcessingStrategy):
    bad_image_counter = 0
    bad_image_thres = 30
    is_need_capture = True

    def pre_process_images(images_info, images, system_info):
        return tuple()

    def process_image(manager, image_info):
        _, _, img, info, _ = image_info
        if CaptureBackgroundStrategy.is_need_capture:
            if img is None:
                CaptureBackgroundStrategy.bad_image_counter += 1
                if CaptureBackgroundStrategy.bad_image_counter > CaptureBackgroundStrategy.bad_image_thres:
                    logger.error('Captured bad image too many times, please check your video streaming information !!')
            else:
                CaptureBackgroundStrategy.is_need_capture = False
                # get and create save path
                save_path = os.path.join(manager.stream.save_dir, manager.stream.group, manager.stream.channel)
                os.makedirs(save_path, exist_ok=True)

                # save image
                name = manager.stream.get_cur_info(info['sec'])[2] + str(info['curframe'])
                save_name = os.path.join(save_path, name + '.png')
                cv2.imwrite(save_name, img)
                logger.info('Capture background image to %s successfull !!' % (save_name))
        return True

    def check_stop(manager, image_info):
        if not CaptureBackgroundStrategy.is_need_capture:
            return True
        return False


class RecordVideoStrategy(ImageProcessingStrategy):
    SHOW = True

    def __init__(self, record_seconds, start_sec=-1):
        self.frame = 0
        self.is_need_record = True
        self.start_sec = start_sec
        # init
        self.record_seconds = record_seconds

    def _show_image(self, manager, img):
        if RecordVideoStrategy.SHOW:
            if manager.vid_writer.WINDOW_NAME in manager.visualizer.stop_signal \
               and manager.visualizer.stop_signal[manager.vid_writer.WINDOW_NAME]:
                cv2.destroyAllWindows()
                self.is_need_record = False
            else:
                manager.visualizer.show_img(manager.vid_writer.WINDOW_NAME, img)

    def pre_process_images(self, images_info, images, system_info):
        return tuple()

    def process_image(self, manager, image_info):
        _, _, img, info, _ = image_info
        if self.is_need_record:
            if img is not None:
                # show
                self._show_image(manager, img)
                # whether if start
                if self.start_sec < 0:
                    return False
                # start record
                if info['sec'] >= self.start_sec:
                    self.frame += 1
                    # show current result
                    t = self.frame / manager.stream.infer_fps
                    t2 = t / self.record_seconds
                    print(f"Record seconds: {t:.2f}/{self.record_seconds} ({(t2 * 100):.2f}%)", end="\r")
                    return True
        return False

    def check_stop(self, manager, image_info):
        if self.is_need_record and manager.stream.capture.isOpened() \
           and (self.frame / manager.stream.infer_fps < self.record_seconds)  \
           and (not manager.vid_writer.stop_flag):
            return False

        # stop
        return True
