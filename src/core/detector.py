"""Fire detection inference engine using a PyTorch YOLO model."""

import numpy as np
from typing import Dict, Any
import logging
import os
from ultralytics import YOLO

logger = logging.getLogger(__name__)


class FireDetector:
    """YOLO-based fire detector using a PyTorch model."""
    
    def __init__(self, model_path: str):
        """
        Initialize the fire detector with YOLOv8 model.
        
        Args:
            model_path: Path to a PyTorch model (.pt)
        """
        self.model_path = model_path
        if not self.model_path.endswith(".pt"):
            raise ValueError(f"Only PyTorch .pt models are supported. Received: {self.model_path}")

        self.current_frame: np.ndarray | None = None

        self._init_pytorch_model()
        logger.info("Detector ready")
    
    def _init_pytorch_model(self):
        """Initialize PyTorch model using Ultralytics YOLO."""
        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model not found: {self.model_path}")
            
            self.model = YOLO(self.model_path)
            logger.info(f"Model loaded: {self.model_path}")
        
        except ImportError:
            raise ImportError("ultralytics package required for PyTorch models. Install with: pip install ultralytics")
        except Exception as e:
            logger.error(f"Model load failed: {e}")
            raise
    
    def infer(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Run inference on a single frame.
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            Dictionary containing detections and metadata
        """
        self.current_frame = frame.copy()
        return self._infer_pytorch(frame)
    
    def _infer_pytorch(self, frame: np.ndarray) -> Dict[str, Any]:
        """Run inference using PyTorch model."""
        try:
            # Run inference
            results = self.model(frame, conf=0.5, iou=0.45, verbose=False)
            
            # Extract detections
            detections = []
            if results and len(results) > 0:
                result = results[0]
                
                if result.boxes is not None:
                    for box in result.boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                        conf = float(box.conf[0].cpu().numpy())
                        class_id = int(box.cls[0].cpu().numpy())
                        
                        detections.append({
                            "bbox": (int(x1), int(y1), int(x2), int(y2)),
                            "confidence": conf,
                            "class_id": class_id,
                            "class_name": "fire"
                        })
            
            return {
                "detections": detections,
                "frame_shape": frame.shape,
                "timestamp": None
            }
        
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return {"detections": [], "frame_shape": frame.shape, "timestamp": None}
