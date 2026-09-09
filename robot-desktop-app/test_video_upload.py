import os
import sys
import requests
import time

sys.path.insert(0, os.path.dirname(__file__))
from config import load_config

def test_video_upload():
    config = load_config()
    base_url = config.get("cloud_api_url", "")
    device_uid = config.get("device_uid", "rover-001")
    
    print(f"API URL: {base_url}")
    print(f"Device UID: {device_uid}")
    
    test_url = f"{base_url}/rovers/{device_uid}/media"
    print(f"Upload endpoint: {test_url}")
    
    print("\n[1] Testing connection...")
    try:
        health_url = f"{base_url}/health"
        resp = requests.get(health_url, timeout=5)
        print(f"Health check: {resp.status_code} - {resp.text[:100]}")
    except Exception as e:
        print(f"Health check failed: {e}")
    
    print("\n[2] Creating test video file...")
    test_video = "test_video.avi"
    try:
        import cv2
        import numpy as np
        
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(test_video, fourcc, 10.0, (320, 240))
        
        for i in range(30):
            frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            cv2.putText(frame, f"Test Frame {i+1}", (50, 120), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            out.write(frame)
        
        out.release()
        print(f"Created test video: {test_video} ({os.path.getsize(test_video)} bytes)")
    except ImportError:
        print("OpenCV not installed. Creating dummy file instead.")
        with open(test_video, "wb") as f:
            f.write(os.urandom(10240))
        print(f"Created dummy file: {test_video}")
    
    print("\n[3] Uploading video to API...")
    try:
        with open(test_video, 'rb') as f:
            files = {'file': (test_video, f, 'video/avi')}
            response = requests.post(test_url, files=files, timeout=30)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text[:500]}")
        
        if response.status_code == 201:
            print("\n✓ Video upload SUCCESS!")
        else:
            print(f"\n✗ Video upload FAILED with status {response.status_code}")
    except Exception as e:
        print(f"\n✗ Upload error: {e}")
    
    print("\n[4] Listing media to verify...")
    try:
        resp = requests.get(test_url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            media_list = data.get("media", data) if isinstance(data, dict) else data
            print(f"Total media items: {len(media_list) if isinstance(media_list, list) else 'N/A'}")
            if isinstance(media_list, list) and len(media_list) > 0:
                latest = media_list[0]
                print(f"Latest item: {latest}")
    except Exception as e:
        print(f"List error: {e}")
    
    print("\n[5] Cleaning up...")
    if os.path.exists(test_video):
        os.remove(test_video)
        print(f"Removed {test_video}")
    
    print("\n" + "="*50)
    print("Test complete!")

if __name__ == "__main__":
    test_video_upload()
