from google import genai
from PyQt6.QtCore import QThread, pyqtSignal


class GeminiWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    tool_called = pyqtSignal(str, dict)

    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key
        self.client = None
        self.chat = None
        self._pending_message = None

    def create_custom_charts(self, custom_groups: dict, normalize: bool = False) -> str:
        """Creates custom charts based on user requests.

        Args:
            custom_groups: A dictionary where keys are chart titles and values are lists of sensor names.
                           Valid sensor names: "co2", "pm1.0", "pm2.5", "pm10", "temperature", "humidity", "pressure", "gas", "battery".
                           Example: {"CO2 Levels": ["co2"]}
            normalize: If True, apply Min-Max normalization to scale all values to 0-1 range.
                       Useful when comparing sensors with vastly different value scales.

        Returns:
            Confirmation message.
        """
        self.tool_called.emit("create_custom_charts", {"custom_groups": custom_groups, "normalize": normalize})
        return "Custom charts created successfully."

    def init_chat(self):
        try:
            self.client = genai.Client(api_key=self.api_key)
            self.chat = self.client.chats.create(
                model='gemini-3.5-flash-lite',
                config={
                    'tools': [self.create_custom_charts],
                    'temperature': 0.7,
                }
            )
            return True
        except Exception as e:
            self.error.emit(f"Failed to initialize Gemini: {str(e)}")
            return False

    def send_message(self, text):
        if not self.chat:
            if not self.init_chat():
                return
        self._pending_message = text
        self.start()

    def run(self):
        try:
            if self._pending_message:
                response = self.chat.send_message(self._pending_message)
                self._pending_message = None
                if response.text:
                    self.finished.emit(response.text)
        except Exception as e:
            self.error.emit(f"Gemini error: {str(e)}")
