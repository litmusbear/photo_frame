import io
import os
from PIL import Image
import rawpy

def get_width(image):
    return image.size[0]


def get_height(image):
    return image.size[1]


def get_thickness(height):
    return int(height * 0.03)


def get_padding(height):
    return int(height * 0.15)


def add_border(img, w, h, t, p):
    border_width = w + (t * 2)
    border_height = h + t + p
    canvas = Image.new("RGB", (border_width, border_height), (255, 255, 255))
    canvas.paste(img, (t, t))
    return canvas


def save_uploaded_file_to_temp(uploaded_file, temp_path):
    file_bytes = uploaded_file.getbuffer()
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    raw_extensions = [".arw", ".cr2", ".cr3", ".nef", ".dng", ".orf", ".rw2", ".pef", ".raf"]

    if ext in raw_extensions:
        with rawpy.imread(io.BytesIO(file_bytes)) as raw:
            rgb = raw.postprocess(use_camera_wb=True)
            img = Image.fromarray(rgb)
            img.save(temp_path, format="JPEG", quality=95)
    else:
        with open(temp_path, "wb") as f:
            f.write(file_bytes)