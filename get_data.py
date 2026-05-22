from PIL import Image, ImageOps
from PIL.ExifTags import TAGS
from datetime import datetime
from timezonefinder import TimezoneFinder
import pytz

def get_exif_data(image_path):
    image = Image.open(image_path)
    info = image._getexif()
    exif_dict = {}

    if info:
        for tag, value in info.items():
            tag_name = TAGS.get(tag, tag)
            exif_dict[tag_name] = value

    return exif_dict

def get_shutter(exif):
    shutter = exif.get("ExposureTime", "?")
    if shutter:
        # 만약 데이터가 (분자, 분모) 형태의 튜플로 들어올 경우를 대비
        if isinstance(shutter, tuple):
            shutter = shutter[0] / shutter[1]

        if shutter < 1:
            denom = round(1 / shutter)
            shutter = f"1/{denom}"

        else:
            shutter = f"{shutter}\""
    else:
        shutter = "?"
    return shutter

def convert_to_degrees(value):
    d = float(value[0])
    m = float(value[1])
    s = float(value[2])
    return d + (m / 60.0) + (s / 3600.0)

def get_gps(exif):
    gps_info = exif.get("GPSInfo", {})
    if not gps_info:
        return None

    try:
        lat = convert_to_degrees(gps_info[2])
        if gps_info[1] == 'S': lat = -lat

        lon = convert_to_degrees(gps_info[4])
        if gps_info[3] == 'W': lon = -lon

        return lat, lon
    except:
        return None


def get_datetime(exif):
    date_str = exif.get("DateTimeOriginal", "")
    if not date_str: return ""

    dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")

    coords = get_gps(exif)
    utc_offset_str = "UTC+00:00"

    if coords:
        tf = TimezoneFinder()
        tz_name = tf.timezone_at(lat=coords[0], lng=coords[1])  # 위경도로 타임존 이름 찾기
        if tz_name:
            timezone = pytz.timezone(tz_name)
            aware_dt = timezone.localize(dt)
            utc_offset = aware_dt.utcoffset()

            hours = int(utc_offset.total_seconds() / 3600)
            minutes = int((utc_offset.total_seconds() % 3600) / 60)
            utc_offset_str = f"UTC{'+' if hours >= 0 else ''}{hours:02d}:{abs(minutes):02d}"

    return dt.strftime(f"%Y-%B-%d %H:%M {utc_offset_str}")

class Picture():
    def __init__(self, image_path):
        img = Image.open(image_path)
        self.image_path = image_path
        self.exif = get_exif_data(image_path)
        self.image = self.image = ImageOps.exif_transpose(img)
        self.camera = self.exif.get("Model", "Unknown Camera")
        self.iso = self.exif.get("ISOSpeedRatings", "?")
        self.f_number = self.exif.get("FNumber", "?")
        self.shutter = get_shutter(self.exif)
        self.datetime = get_datetime(self.exif)

    def get_image(self):
        return self.image

    def get_camera(self):
        return self.camera

    def get_iso(self):
        return self.iso

    def get_f_number(self):
        return self.f_number

    def get_shutter(self):
        return self.shutter

    def get_datetime(self):
        return self.datetime