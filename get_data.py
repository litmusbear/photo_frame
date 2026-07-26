import re
from datetime import datetime
import exifread
from PIL import Image, ImageOps
from PIL.ExifTags import TAGS
import pytz
from timezonefinder import TimezoneFinder

# lenses.py 불러오기 예외 처리
try:
    from lenses import KNOWN_COMPACT_LENSES
except ImportError:
    KNOWN_COMPACT_LENSES = {}

def get_exif_data(image_path):
    exif_dict = {}
    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=True)
            if tags:
                for tag, val in tags.items():
                    clean_tag = tag.split()[-1] if ' ' in tag else tag
                    exif_dict[clean_tag] = str(val)
                    exif_dict[tag] = str(val)
    except Exception:
        pass

    try:
        image = Image.open(image_path)
        info = image._getexif()
        if info:
            for tag, value in info.items():
                tag_name = TAGS.get(tag, tag)
                if tag_name not in exif_dict:
                    exif_dict[tag_name] = value
    except Exception:
        pass

    return exif_dict


BRANDS_SAFE_TO_STRIP = {
    "CANON",
    "PANASONIC",
    "SONY",
    "OLYMPUS",
    "RICOH",
}


def clean_camera_name(exif):
    make = exif.get("Make", "")
    model = exif.get("Model", "Unknown Camera")

    if isinstance(make, bytes): make = make.decode('utf-8', errors='ignore')
    if isinstance(model, bytes): model = model.decode('utf-8', errors='ignore')

    if make:
        make_keyword = make.split()[0] if make.split() else make
        if make_keyword.upper() in BRANDS_SAFE_TO_STRIP:
            pattern = re.compile(r"^\s*" + re.escape(make_keyword) + r"\s+", re.IGNORECASE)
            model = pattern.sub("", model).strip()

    return model


def get_shutter(exif):
    shutter_raw = exif.get("ExposureTime", "?")
    if not shutter_raw or shutter_raw == "?":
        return "?"

    val = None
    if isinstance(shutter_raw, tuple) and len(shutter_raw) == 2:
        val = shutter_raw[0] / shutter_raw[1] if shutter_raw[1] != 0 else None
    elif isinstance(shutter_raw, (int, float)):
        val = float(shutter_raw)
    elif isinstance(shutter_raw, str):
        if "/" in shutter_raw:
            try:
                n, d = shutter_raw.split("/")
                val = float(n) / float(d) if float(d) != 0 else None
            except Exception:
                val = None
        else:
            try:
                val = float(shutter_raw)
            except Exception:
                val = None

    if val is None or val == 0:
        return str(shutter_raw)

    if val < 1:
        denom = round(1 / val)
        return f"1/{denom}"
    else:
        return f"{round(val, 1)}\""


def convert_to_degrees(value):
    try:
        d = float(value[0][0] / value[0][1]) if isinstance(value[0], tuple) else float(value[0])
        m = float(value[1][0] / value[1][1]) if isinstance(value[1], tuple) else float(value[1])
        s = float(value[2][0] / value[2][1]) if isinstance(value[2], tuple) else float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return 0.0


def get_gps(exif):
    gps_info = exif.get("GPSInfo", {})
    if not gps_info:
        return None
    try:
        lat = convert_to_degrees(gps_info[2])
        if gps_info.get(1) == 'S': lat = -lat
        lon = convert_to_degrees(gps_info[4])
        if gps_info.get(3) == 'W': lon = -lon
        return lat, lon
    except Exception:
        return None


def get_datetime(exif):
    date_str = exif.get("DateTimeOriginal", "")
    if not date_str: return ""

    try:
        dt = datetime.strptime(str(date_str), "%Y:%m:%d %H:%M:%S")
    except Exception:
        return str(date_str)

    coords = get_gps(exif)
    utc_offset_str = "UTC+00:00"

    if coords:
        try:
            tf = TimezoneFinder()
            tz_name = tf.timezone_at(lat=coords[0], lng=coords[1])
            if tz_name:
                timezone = pytz.timezone(tz_name)
                aware_dt = timezone.localize(dt)
                utc_offset = aware_dt.utcoffset()
                hours = int(utc_offset.total_seconds() / 3600)
                minutes = int((utc_offset.total_seconds() % 3600) / 60)
                utc_offset_str = f"UTC{'+' if hours >= 0 else ''}{hours:02d}:{abs(minutes):02d}"
        except Exception:
            pass

    return dt.strftime(f"%Y-%b-%d %H:%M {utc_offset_str}")


def lookup_known_lens(camera_model):
    if not camera_model:
        return ""
    model_upper = camera_model.upper()
    for keyword, lens_spec in KNOWN_COMPACT_LENSES.items():
        if keyword.upper() in model_upper:
            return lens_spec
    return ""


def get_lens(exif, camera_model=""):
    known = lookup_known_lens(camera_model)
    if known:
        return known

    lens = exif.get("LensModel", "")
    lens_str = str(lens).strip() if lens else ""

    if not lens_str or lens_str.lower() in ["none", "unknown", "?", "built-in"]:
        return ""

    if camera_model:
        pattern = re.compile(re.escape(camera_model), re.IGNORECASE)
        lens_str = pattern.sub("", lens_str).strip()

    if "camera" in lens_str.lower():
        specs = re.findall(r'\d+(?:\.\d+)?\s*mm|\bf\/\d+(?:\.\d+)?', lens_str, re.IGNORECASE)
        if specs:
            lens_str = " ".join(specs).strip()
        else:
            lens_str = ""
    return lens_str.strip(" ,-_")


class ReturnPictureEXIF():
    def __init__(self, image_path):
        img = Image.open(image_path)
        self.image_path = image_path
        self.exif = get_exif_data(image_path)
        self.image = ImageOps.exif_transpose(img)
        self.camera = clean_camera_name(self.exif)
        self.iso = self.exif.get("ISOSpeedRatings", "?")

        # F-Number 처리
        f_val = self.exif.get("FNumber", "?")

        if isinstance(f_val, str) and "/" in f_val:
            try:
                num, den = f_val.split("/")
                f_val = float(num) / float(den) if float(den) != 0 else "?"
            except Exception:
                pass
        elif isinstance(f_val, tuple) and len(f_val) == 2:
            try:
                f_val = f_val[0] / f_val[1] if f_val[1] != 0 else "?"
            except Exception:
                pass

        try:
            if f_val != "?" and f_val is not None:
                self.f_number = f"{float(f_val):.1f}"
            else:
                self.f_number = "?"
        except Exception:
            self.f_number = str(f_val)

        self.shutter = get_shutter(self.exif)
        self.datetime = get_datetime(self.exif)

        base_lens = get_lens(self.exif, self.camera)

        eq_focal = self.exif.get("FocalLengthIn35mmFilm", "")
        if isinstance(eq_focal, tuple) and len(eq_focal) == 2:
            eq_focal = eq_focal[0] / eq_focal[1] if eq_focal[1] != 0 else ""

        if not eq_focal or str(eq_focal) == "?":
            eq_focal = self.exif.get("FocalLength", "")
            if isinstance(eq_focal, tuple) and len(eq_focal) == 2:
                eq_focal = eq_focal[0] / eq_focal[1] if eq_focal[1] != 0 else ""

        try:
            focal_str = f"@{int(float(eq_focal))}mm" if eq_focal and str(eq_focal) != "?" else ""
        except Exception:
            focal_str = ""

        if base_lens:
            self.lens = f"{base_lens} {focal_str}".strip()
        else:
            self.lens = f"Lens Unspecified {focal_str}".strip()

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

    def get_lens(self):
        return self.lens