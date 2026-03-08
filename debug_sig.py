import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
import cloudinary.utils

folder = "pipeline/061cc183-189a-4de6-a9ac-b64f126f05ef"
public_id = "061cc183-189a-4de6-a9ac-b64f126f05ef"
timestamp = 1772431315

params = {
    "timestamp": timestamp,
    "folder": folder,
    "public_id": public_id
}

sig = cloudinary.utils.api_sign_request(params, settings.CLOUDINARY_API_SECRET)
print("Secret used:", settings.CLOUDINARY_API_SECRET)
print("Signature generated:", sig)
