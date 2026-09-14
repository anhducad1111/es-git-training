# Image Processing Feature

## Overview
Apply image processing filters to captured snapshots. Supports multiple processing modes that can be applied individually or combined.

## Usage

### Processing Modes
| Mode | Description | Algorithm |
|------|-------------|-----------|
| **AUTO CORRECT** | Automatic brightness and contrast adjustment | CLAHE (Contrast Limited Adaptive Histogram Equalization) |
| **ENHANCE CONTRAST** | Edge enhancement for sharper images | Unsharp Masking |
| **DENOISE** | Noise reduction for cleaner images | Non-Local Means Denoising |
| **BICUBIC (1.5x)** | Image upscale using bicubic interpolation | cv2.INTER_CUBIC |

### Applying Filters
1. Select snapshot from gallery
2. Click processing mode buttons to select (multiple allowed)
3. Selected buttons show filled color with checkmark
4. Click "APPLY SELECTED" to process
5. Preview updates with processed result

### Button States
| State | Visual | Description |
|-------|--------|-------------|
| **Normal** | Semi-transparent background | Ready to select |
| **Selected** | Solid color background | Included in processing |
| **Processing** | Darker color, "PROCESSING..." | Currently executing |
| **Done** | Shows result preview | Processing complete |

### Saving Processed Images
1. After processing, click "DOWNLOAD"
2. File dialog opens to choose save location
3. Processed image saved as PNG/JPG

## Implementation

### Processing Pipeline
```python
# snapshots_view.py - Toggle mode selection
def _toggle_mode(app, mode, btn):
    if mode in app._selected_modes:
        app._selected_modes.discard(mode)  # Deselect
    else:
        app._selected_modes.add(mode)      # Select

# Apply all selected modes
def _apply_selected(app):
    modes = list(app._selected_modes)
    worker = ImageProcessor(input_path, output_path, modes)
```

### Image Processor
```python
# image_processor.py
class ImageProcessor(QThread):
    def run(self):
        img = cv2.imread(self.input_path)
        
        # Apply each mode in sequence
        if isinstance(self.mode, list):
            result = img
            for m in self.mode:
                result = self._apply_mode(result, m)
        else:
            result = self._apply_mode(img, self.mode)
        
        # Return numpy array (no file save)
        self.finished.emit(result)

    def _apply_mode(self, img, mode):
        if mode == "auto":
            return self._auto_correct(img)
        elif mode == "contrast":
            return self._enhance_contrast(img)
        elif mode == "denoise":
            return self._denoise(img)
        elif mode == "bicubic":
            return self._bicubic_resize(img)
```

### Auto Correct (CLAHE)
```python
def _auto_correct(self, img):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
```

### Enhance Contrast (Unsharp Masking)
```python
def _enhance_contrast(self, img):
    gaussian = cv2.GaussianBlur(img, (0, 0), 3)
    sharpened = cv2.addWeighted(img, 1.5, gaussian, -0.5, 0)
    return sharpened
```

### Denoise (Non-Local Means)
```python
def _denoise(self, img):
    return cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
```

### Bicubic Resize
```python
def _bicubic_resize(self, img):
    h, w = img.shape[:2]
    new_w = int(w * 1.5)
    new_h = int(h * 1.5)
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
```

## Dependencies
- OpenCV (`opencv-python`)
- NumPy (included with OpenCV)

## Notes
- Processed images are stored in memory until downloaded
- Multiple modes can be applied in sequence
- Each mode button can be toggled independently
- Processing is performed in a separate thread to prevent UI blocking
