# Object Detection

## Overview
Real-time object detection using HOG and YOLOv8 models in separate QThread.

## HOG Detection
Histogram of Oriented Gradients for person detection.

### Usage
1. Select "HOG" from dropdown in bottom controls
2. Click "DETECT" button
3. Green bounding boxes appear on detected persons

### Implementation
- `hog_detector.py` - HOGDetector QThread class
- Uses `cv2.HOGDescriptor` with SVM people detector
- Detects only persons
- Runs at ~10 FPS

## YOLOv8 Detection
YOLOv8 medium model for multi-class object detection.

### Usage
1. Select "YOLO" from dropdown in bottom controls
2. Click "DETECT" button
3. Green bounding boxes appear on detected objects

### Implementation
- `yolo_detector.py` - YOLODetector QThread class
- Uses ultralytics YOLOv8m model
- Detects 80 COCO classes
- Runs at ~7 FPS

### Supported Classes
person, bicycle, car, motorcycle, airplane, bus, train, truck, boat, traffic light, fire hydrant, stop sign, parking meter, bench, bird, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe, backpack, umbrella, handbag, tie, suitcase, frisbee, skis, snowboard, sports ball, kite, baseball bat, baseball glove, skateboard, surfboard, tennis racket, bottle, wine glass, cup, fork, knife, spoon, bowl, banana, apple, sandwich, orange, broccoli, carrot, hot dog, pizza, donut, cake, chair, couch, potted plant, bed, dining table, toilet, tv, laptop, mouse, remote, keyboard, cell phone, microwave, oven, toaster, sink, refrigerator, book, clock, vase, scissors, teddy bear, hair drier, toothbrush

## Frame Processing
```python
# In app.py _update_video_frame()
if isinstance(frame, QImage):
    # Convert QImage to BGR numpy array
    ptr = frame.bits()
    ptr.setsize(frame.sizeInBytes())
    arr = np.array(ptr).reshape(frame.height(), frame.width(), 4)
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
else:
    # Decode JPEG bytes
    nparr = np.frombuffer(frame, np.uint8)
    bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
```

## Detection Output Format
```python
{
    "x": int,        # Bounding box x
    "y": int,        # Bounding box y
    "w": int,        # Bounding box width
    "h": int,        # Bounding box height
    "confidence": float,  # Detection confidence
    "label": str     # Class label
}
```

## Performance
- HOG: Lightweight, person-only, ~10 FPS
- YOLOv8m: High accuracy, 80 classes, ~7 FPS
