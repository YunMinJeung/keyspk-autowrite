import hashlib
import hmac
import base64

class Signature:
    @staticmethod
    def generate(timestamp, method, uri, secret_key):
        message = "{}.{}.{}".format(timestamp, method, uri)
        hash = hmac.new(bytes(secret_key, "utf-8"), bytes(message, "utf-8"), hashlib.sha256)

        # base64 인코딩 후 bytes → string으로 변환
        return base64.b64encode(hash.digest()).decode("utf-8")
