import requests

from env_variables import env_variables

class AntifraudController:
    def __init__(self):
        env_var = env_variables()
        antifraud_address = env_var.antifraud_address
        self.url = f"http://{antifraud_address}/api/validate"

    def check_user(self, user_email, promo_id):
        data = {
            "user_email": user_email,
            "promo_id": promo_id
        }

        response = requests.post(self.url, json=data)
        return response.json()


