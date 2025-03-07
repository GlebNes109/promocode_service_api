import redis
from datetime import datetime, timedelta
import pytz
from env_variables import env_variables


class RedisController:
    def __init__(self):
        env_var = env_variables()
        self.client = redis.StrictRedis(
        host=env_var.redis_host,
        port=env_var.redis_port,
        # password='1232'
        )

    def add_key_to_db(self, company_id, token):
        self.client.set(company_id, token)

    def validate_key(self, company_id, token):
        try:
            if self.client.get(company_id).decode("utf-8") == token:
                return True
            else:
                return False
        except:
            return False

    def get_user_antifraud_result(self, user_id):
        # если с таким ключом нет, вернуть None
        key = "antifraud_" + user_id

        try:
            value = self.client.get(key)
            if value is None:
                return None
            return value.decode("utf-8")
        except:
            return None

    def save_user_antifraud_result(self, user_id, value, timestr):
        key = "antifraud_" + user_id

        # timestr в формате "2025-01-26T22:02:22.015"
        # конвертим в datetime (антифрод возвращает в UTC+0)
        utc_time = datetime.strptime(timestr, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=pytz.utc)
        timezone_plus3 = pytz.timezone("Europe/Moscow")
        time_in_plus3 = utc_time.astimezone(timezone_plus3)

        # в Unix-формате
        exp_time = int(time_in_plus3.timestamp())

        self.client.set(key, str(value))
        self.client.expireat(key, exp_time)


