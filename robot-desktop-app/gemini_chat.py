from google import genai
from PyQt6.QtCore import QThread, pyqtSignal


class GeminiChat(QThread):
    response = pyqtSignal(str)
    error = pyqtSignal(str)
    tool_called = pyqtSignal(str, dict)

    VALID_SENSORS = ["temperature", "humidity", "gas", "distance"]

    def __init__(self, api_key, prompt, sensor_data=None):
        super().__init__()
        self.api_key = api_key
        self.prompt = prompt
        self.sensor_data = sensor_data or {}
        self.client = None
        self.chat = None

    def create_custom_charts(self, custom_groups: dict, normalize: bool = False) -> str:
        """Creates custom charts based on user requests.

        Args:
            custom_groups: A dictionary where keys are chart titles and values are lists of sensor names.
                           Valid sensor names: "temperature", "humidity", "gas", "distance".
                           Example: {"Temperature vs Gas": ["temperature", "gas"]}
            normalize: If True, apply Min-Max normalization to scale all values to 0-1 range.

        Returns:
            Confirmation message.
        """
        self.tool_called.emit("create_custom_charts", {"custom_groups": custom_groups, "normalize": normalize})
        return "Custom charts created successfully."

    def _init_chat(self):
        self.client = genai.Client(api_key=self.api_key)
        system_instruction = (
            "You are a sensor data analyst for a rover robot. "
            "Answer questions about the sensor readings concisely. "
            "Available sensors: temperature, humidity, gas, distance. "
            "You can create custom charts by calling create_custom_charts with "
            "a dictionary mapping chart titles to lists of sensor names."
        )
        self.chat = self.client.chats.create(
            model="gemini-3.5-flash-lite",
            config={
                "tools": [self.create_custom_charts],
                "temperature": 0.7,
                "system_instruction": system_instruction,
            },
        )

    def run(self):
        try:
            if not self.chat:
                self._init_chat()

            context = f"Current sensor data: {self.sensor_data}\n\nUser question: {self.prompt}"
            response = self.chat.send_message(context)
            if response.text:
                self.response.emit(response.text)
        except Exception as e:
            self.error.emit(f"Gemini error: {str(e)}")
