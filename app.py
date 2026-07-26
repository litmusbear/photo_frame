import os
import io
import re
import uuid
import urllib.parse
import traceback
from flask import Flask, render_template, request, send_file, jsonify
from PIL import Image

try:
    import piexif

    HAS_PIEXIF = True
except ImportError:
    HAS_PIEXIF = False

# 기존 비즈니스 로직 모듈 임포트
from timezones import timezone_options
from place_data import place_model
from get_data import ReturnPictureEXIF
from logo import logo
from border import *

# lenses.py 연동
try:
    from lenses import OLD_LENSES_BY_BRAND, MANUAL_F_NUMBERS, COMMON_EQUIV_FOCAL_LENGTHS
except ImportError:
    OLD_LENSES_BY_BRAND = {
        "EXIF 기본값": ["EXIF 정보 사용"],
        "직접 입력": ["사용자 지정 입력"],
        "Yashica / Contax": ["Yashica ML 50mm f/1.4", "Carl Zeiss Planar T* 50mm f/1.4 C/Y"],
        "Pentax / M42": ["Helios 44-2 58mm f/2.0", "Asahi Pentax Super-Takumar 50mm f/1.4"],
        "Leica / L39": ["Leica Summicron-M 50mm f/2.0"],
        "Canon FD": ["Canon FD 50mm f/1.4 SSC"],
        "Nikon F": ["Nikkor-S Auto 50mm f/1.4"]
    }
    MANUAL_F_NUMBERS = ["EXIF 유지", "f/1.2", "f/1.4", "f/1.8", "f/2.0", "f/2.8", "f/4.0", "f/5.6", "f/8.0"]
    COMMON_EQUIV_FOCAL_LENGTHS = ["EXIF 유지", "24mm", "28mm", "35mm", "40mm", "50mm", "58mm", "75mm", "85mm", "135mm", "직접 입력"]

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 최대 100MB 파일 지원


def clean_uploaded_filename(filename):
    """iOS/Safari 사진 앱 업로드 시 붙는 쿼리스트링 정제"""
    decoded = urllib.parse.unquote(filename)
    clean_name = decoded.split("?")[0].split("&")[0]
    if "uuid=" in clean_name and "code=" in clean_name:
        ext = os.path.splitext(clean_name)[1]
        return f"RAW_Image{ext}"
    return os.path.basename(clean_name)


def update_and_extract_exif_bytes(source_path, override_lens="", override_f="", override_focal=""):
    """수동으로 선택하거나 입력한 메타데이터를 원본 EXIF에 주입하여 바이너리로 반환"""
    if not HAS_PIEXIF:
        try:
            with Image.open(source_path) as img:
                return img.info.get("exif")
        except Exception:
            return None

    try:
        exif_dict = piexif.load(source_path)
    except Exception:
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

    # 방향 정보 리셋 (회전 문제 방지)
    if "0th" in exif_dict and piexif.ImageIFD.Orientation in exif_dict["0th"]:
        exif_dict["0th"][piexif.ImageIFD.Orientation] = 1

    # 1. 렌즈 모델 주입
    if override_lens:
        exif_dict["Exif"][piexif.ExifIFD.LensModel] = override_lens.encode('utf-8')

    # 2. 조리개 값 (FNumber) 주입
    if override_f:
        try:
            f_val = float(override_f.replace("f/", "").strip())
            exif_dict["Exif"][piexif.ExifIFD.FNumber] = (int(round(f_val * 10)), 10)
        except Exception:
            pass

    # 3. 화각 값 (FocalLength / 35mm 환산) 주입
    if override_focal:
        try:
            focal_num = float(re.sub(r'[^0-9.]', '', override_focal))
            exif_dict["Exif"][piexif.ExifIFD.FocalLength] = (int(round(focal_num * 10)), 10)
            exif_dict["Exif"][piexif.ExifIFD.FocalLengthIn35mmFilm] = int(round(focal_num))
        except Exception:
            pass

    try:
        return piexif.dump(exif_dict)
    except Exception:
        return None


@app.route('/')
def index():
    return render_template(
        'index.html',
        brands=list(OLD_LENSES_BY_BRAND.keys()),
        lenses_by_brand=OLD_LENSES_BY_BRAND,
        f_numbers=MANUAL_F_NUMBERS,
        focal_lengths=COMMON_EQUIV_FOCAL_LENGTHS,
        timezones=timezone_options
    )


@app.route('/process', methods=['POST'])
def process_image():
    if 'file' not in request.files:
        return jsonify({'error': '업로드된 파일이 없습니다.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '선택된 파일이 없습니다.'}), 400

    display_name = clean_uploaded_filename(file.filename)

    # Form 수동 입력값 읽기
    override_lens = request.form.get('override_lens', '')
    override_f = request.form.get('override_f', '')
    override_focal = request.form.get('override_focal', '')
    chosen_utc_raw = request.form.get('chosen_utc', 'UTC+09:00')
    chosen_utc = chosen_utc_raw.split(" ")[0]

    unique_id = uuid.uuid4().hex[:8]
    temp_path = f"temp_{unique_id}.jpg"

    try:
        # 파일 저장 (Streamlit의 save_uploaded_file_to_temp 대응)
        file.save(temp_path)

        picture = ReturnPictureEXIF(temp_path)
        image = picture.get_image()
        if image is None:
            raise ValueError("이미지를 읽을 수 없습니다.")

        width = get_width(image)
        height = get_height(image)
        thickness = get_thickness(height)
        padding = get_padding(height)
        logo_file = logo(picture)

        base_canvas = add_border(image, width, height, thickness, padding)

        final_canvas = place_model(
            base_canvas, picture, width, height, thickness, padding, logo_file,
            chosen_utc=chosen_utc,
            current_path=temp_path,
            override_lens=override_lens,
            override_f=override_f,
            override_focal=override_focal
        )

        # EXIF 데이터 주입 및 재구성
        updated_exif_bytes = update_and_extract_exif_bytes(
            temp_path,
            override_lens=override_lens,
            override_f=override_f,
            override_focal=override_focal
        )

        output_io = io.BytesIO()
        if updated_exif_bytes:
            try:
                final_canvas.save(output_io, format="JPEG", quality=95, exif=updated_exif_bytes)
            except Exception:
                final_canvas.save(output_io, format="JPEG", quality=95)
        else:
            final_canvas.save(output_io, format="JPEG", quality=95)

        output_io.seek(0)

        clean_filename = os.path.splitext(display_name)[0]
        download_name = f"result_{clean_filename}.jpg"

        return send_file(
            output_io,
            mimetype='image/jpeg',
            as_attachment=True,
            download_filename=download_name
        )

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'error': f"'{display_name}' 처리 중 오류 발생: {str(e)}"}), 500

    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
