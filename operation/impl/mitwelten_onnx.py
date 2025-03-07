from operation.impl.yolov5onnx import Yolov5onnx
from operation.base.operation import Operation
from model.detection import Detection, Box
from model.model import Frame
import logging
import time

from utilities.decorator import Log_time

logger = logging.getLogger(__name__)


# TODO: Remove duplicated code (mitwelten ncnn)
class Mitwelten(Operation):
    def __init__(self, name: str, params = {}):
        logger.info(f"Initializing Mitwelten inference with name {name}")
        super().__init__(name)

        self.flower_model     = Yolov5onnx('flower_inference',     params.get("flower_params", {}))
        self.pollinator_model = Yolov5onnx('pollinator_inference', params.get("pollinator_params", {}))
        logger.info(f"Initialized Mitwelten inference with name {name}")
        

    @Log_time("Mitwelten ONNX Inference") 
    def process(self, frame: Frame) -> list[Detection]:
        start = time.time()
        result_boxes : list[Box] = []
        flower_detections: list[Box] = self.flower_model.process(frame)
        result_boxes.extend(flower_detections)
    
        orig_height, orig_width = frame.image.shape[:2]
    
        for flower_detection in flower_detections:

            fh = flower_detection.xywhn[3]   # normalized flower height
            fw = flower_detection.xywhn[2]   # normalized flower width
            fy = flower_detection.xywhn[1]   # normalized flower y_center
            fx = flower_detection.xywhn[0]   # normalized flower x_center
    
            x1 = int((fx - fw/2) * orig_width)
            y1 = int((fy - fh/2) * orig_height)
            x2 = int((fx + fw/2) * orig_width)
            y2 = int((fy + fh/2) * orig_height)
            
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(orig_width, x2), min(orig_height, y2)
    
            cropped_image = frame.image[y1:y2, x1:x2]
    
            tmp_frame = Frame(
                image=cropped_image,
                timestamp=frame.timestamp,
                frame_id=frame.frame_id,
                source_id=frame.source_id
            )

            pollinator_detections = self.pollinator_model.process(tmp_frame)
    
            cropped_h, cropped_w = cropped_image.shape[:2]
    
            for detection in pollinator_detections:
                px_center, py_center, pw, ph = detection.xywhn
    
                poll_x_center_pixels = px_center * cropped_w
                poll_y_center_pixels = py_center * cropped_h
                poll_w_pixels       = pw * cropped_w
                poll_h_pixels       = ph * cropped_h
    
                poll_x_center_orig = x1 + poll_x_center_pixels
                poll_y_center_orig = y1 + poll_y_center_pixels
    
                cx_norm = poll_x_center_orig / orig_width
                cy_norm = poll_y_center_orig / orig_height
                w_norm  = poll_w_pixels      / orig_width
                h_norm  = poll_h_pixels      / orig_height
    
                detection_on_orig_frame = [cx_norm, cy_norm, w_norm, h_norm]
    
                mapped_box = Box(
                    xywhn=detection_on_orig_frame,
                    conf=detection.conf,
                    label=detection.label
                )
                result_boxes.append(mapped_box)
    
        print(f"{self._name},{len(flower_detections)},{time.time() - start}")
        return result_boxes

