# utils/file_utils.py

import os
import re

def make_safe_key(control_id, filename):
    # 1. Remove file extension first (to avoid dots)
    base_filename = filename.rsplit(".", 1)[0]

    # 2. Clean both parts - (NO dot allowed)
    safe_control = re.sub(r"[^A-Za-z0-9_-]", "_", control_id)
    safe_file = re.sub(r"[^A-Za-z0-9_-]", "_", base_filename)

    # 3. Combine
    combined = f"{safe_control}_{safe_file}"

    # 4. Final aggressive clean (must match Azure key rules exactly)
    final_key = re.sub(r"[^A-Za-z0-9_\-=]", "_", combined)

    return final_key

def list_files(folder):
    return [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]

