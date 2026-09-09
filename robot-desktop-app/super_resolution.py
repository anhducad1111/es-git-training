import os
import json
import requests
from PyQt6.QtCore import QThread, pyqtSignal
from PIL import Image
from config import load_config


class SuperResolutionWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    status = pyqtSignal(str)
    
    def __init__(self, image_path, output_path, use_hf=True):
        super().__init__()
        self.image_path = image_path
        self.output_path = output_path
        self._use_hf = use_hf
        self._config = load_config()
        self._hf_token = self._config.get("hf_token", "")
        self._base_url = "https://hichi2-reals.hf.space"
    
    def run(self):
        if not self._use_hf or not self._hf_token:
            self.status.emit("Using bicubic")
            self._fallback_bicubic()
            return
        
        try:
            self.status.emit("Trying Hugging Face API...")
            self._try_hf_api()
        except Exception as e:
            self.status.emit(f"HF API failed: {str(e)[:50]}")
            self.status.emit("Falling back to bicubic...")
            self._fallback_bicubic()
    
    def _try_hf_api(self):
        headers = {"Authorization": f"Bearer {self._hf_token}"}
        
        with open(self.image_path, 'rb') as f:
            upload_resp = requests.post(
                f"{self._base_url}/gradio_api/upload",
                headers=headers,
                files={"files": f},
                timeout=30
            )
        
        if upload_resp.status_code != 200:
            raise Exception(f"Upload failed: {upload_resp.status_code}")
        
        upload_path = upload_resp.json()[0]
        
        submit_resp = requests.post(
            f"{self._base_url}/gradio_api/call/infer",
            headers=headers,
            json={"data": [{"path": upload_path, "meta": {"_type": "gradio.FileData"}}]},
            timeout=30
        )
        
        if submit_resp.status_code != 200:
            raise Exception(f"Submit failed: {submit_resp.status_code}")
        
        event_id = submit_resp.json().get("event_id")
        if not event_id:
            raise Exception("No event_id returned")
        
        # ストリーミングで結果を受け取る（stream=Trueを設定）
        result_resp = requests.get(
            f"{self._base_url}/gradio_api/call/infer/{event_id}",
            headers=headers,
            stream=True,
            timeout=60
        )
        
        if result_resp.status_code != 200:
            raise Exception(f"Result failed: {result_resp.status_code}")
        
        for line in result_resp.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data:'):
                    data = line_str[5:].strip()
                    if data == '[DONE]':
                        break
                    try:
                        parsed = json.loads(data)
                        # Gradioの完了イベントまたは結果データ配列を処理
                        if isinstance(parsed, list) and len(parsed) > 0:
                            img_data = parsed[0]
                            if isinstance(img_data, dict):
                                img_url = img_data.get('url') or img_data.get('path')
                                if img_url:
                                    if img_url.startswith('/'):
                                        img_url = f"{self._base_url}{img_url}"
                                    img_response = requests.get(img_url, headers=headers, timeout=30)
                                    with open(self.output_path, 'wb') as f:
                                        f.write(img_response.content)
                                    self._apply_unsharp_mask(self.output_path)
                                    self.finished.emit(self.output_path)
                                    return
                    except json.JSONDecodeError:
                        continue
        
        raise Exception("No valid result received")
    
    def _apply_unsharp_mask(self, image_path):
        try:
            from PIL import ImageFilter
            img = Image.open(image_path)
            sharpened = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
            sharpened.save(image_path, "PNG")
        except Exception:
            pass
    
    def _fallback_bicubic(self):
        try:
            img = Image.open(self.image_path)
            width, height = img.size
            new_width = width * 4
            new_height = height * 4
            upscaled = img.resize((new_width, new_height), Image.BICUBIC)
            upscaled.save(self.output_path, "PNG")
            self._apply_unsharp_mask(self.output_path)
            self.finished.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))
