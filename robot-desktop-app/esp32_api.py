import requests


class ESP32API:
    def __init__(self, car_ip, cam_ip):
        self.car_ip = car_ip
        self.cam_ip = cam_ip
        self._timeout = 3

    def set_speed(self, speed):
        """GET /speed?val={80-255}"""
        try:
            resp = requests.get(
                f"http://{self.car_ip}/speed",
                params={"val": speed},
                timeout=self._timeout,
            )
            return resp.status_code == 200
        except:
            return False

    def set_brake(self, enabled):
        """GET /api/distance?brake={0|1}"""
        try:
            resp = requests.get(
                f"http://{self.car_ip}/api/distance",
                params={"brake": 1 if enabled else 0},
                timeout=self._timeout,
            )
            return resp.status_code == 200
        except:
            return False

    def get_distance(self):
        """GET /api/distance"""
        try:
            resp = requests.get(
                f"http://{self.car_ip}/api/distance",
                timeout=self._timeout,
            )
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
        return None

    def set_servo(self, pan, tilt):
        """GET /servo/angle?pan={0-180}&tilt={0-180}"""
        try:
            resp = requests.get(
                f"http://{self.car_ip}/servo/angle",
                params={"pan": pan, "tilt": tilt},
                timeout=self._timeout,
            )
            return resp.status_code == 200
        except:
            return False

    def get_servo_status(self):
        """GET /servo/status"""
        try:
            resp = requests.get(
                f"http://{self.car_ip}/servo/status",
                timeout=self._timeout,
            )
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
        return None

    def center_servo(self):
        """GET /servo/center"""
        try:
            resp = requests.get(
                f"http://{self.car_ip}/servo/center",
                timeout=self._timeout,
            )
            return resp.status_code == 200
        except:
            return False

    def set_led(self, brightness):
        """GET /api/led?val={0-255} on ESP32-Cam"""
        try:
            resp = requests.get(
                f"http://{self.cam_ip}/api/led",
                params={"val": brightness},
                timeout=self._timeout,
            )
            return resp.status_code == 200
        except:
            return False

    def set_quality(self, quality):
        """GET /api/quality?val={0-63} on ESP32-Cam"""
        try:
            resp = requests.get(
                f"http://{self.cam_ip}/api/quality",
                params={"val": quality},
                timeout=self._timeout,
            )
            return resp.status_code == 200
        except:
            return False

    def get_pid(self):
        """GET /api/pid"""
        try:
            resp = requests.get(
                f"http://{self.car_ip}/api/pid",
                timeout=self._timeout,
            )
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
        return None

    def set_pid(self, kp=None, ki=None, kd=None, enabled=None, bias=None):
        """GET /api/pid?kp=&ki=&kd=&enabled=&bias="""
        params = {}
        if kp is not None:
            params["kp"] = kp
        if ki is not None:
            params["ki"] = ki
        if kd is not None:
            params["kd"] = kd
        if enabled is not None:
            params["enabled"] = 1 if enabled else 0
        if bias is not None:
            params["bias"] = bias
        try:
            resp = requests.get(
                f"http://{self.car_ip}/api/pid",
                params=params,
                timeout=self._timeout,
            )
            return resp.status_code == 200
        except:
            return False
