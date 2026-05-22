import flet as ft
import os
import io
from datetime import datetime
from PIL import Image, ImageDraw

# 기존에 만드신 모듈들
from get_data import Picture
from font import *
from logo import logo
from border import *

def add_border(img, w, h, t, p):
    border_width = w + (t * 2)
    border_height = h + t + p
    canvas = Image.new("RGB", (border_width, border_height), (255, 255, 255))
    canvas.paste(img, (t, t))
    return canvas

def place_model(canvas, pic, w, h, t, p, l_file, chosen_utc=None, current_path=None):
    font_obj = set_font(p)  
    font_reg = regular(p)
    font_dat = date_font(p)
    size, d_size = font_size(p)
    
    draw = ImageDraw.Draw(canvas)
    text_camera = pic.get_camera()
    text_info = f"f/{pic.get_f_number()}  {pic.get_shutter()}  ISO{pic.get_iso()}"
    
    utc_offset_str = chosen_utc if chosen_utc else "UTC+09:00"
    text_date = ""
    date_str = ""
    has_valid_gps = False
    
    try:
        with Image.open(current_path) as img_exif:
            exif_data = img_exif._getexif()
        if exif_data:
            from PIL.ExifTags import TAGS
            readable_exif = {TAGS.get(tag, tag): val for tag, val in exif_data.items()}
            date_str = readable_exif.get("DateTimeOriginal", "")
            gps_info = readable_exif.get("GPSInfo", {})
            coords = None
            if gps_info and 2 in gps_info and 4 in gps_info:
                try:
                    def to_degrees(value):
                        return float(value[0]) + (float(value[1]) / 60.0) + (float(value[2]) / 3600.0)
                    lat = to_degrees(gps_info[2])
                    if readable_exif.get("GPSLatitudeRef", "N") == "S": lat = -lat
                    lon = to_degrees(gps_info[4])
                    if readable_exif.get("GPSLongitudeRef", "E") == "W": lon = -lon
                    if abs(lat) > 0.001 and abs(lon) > 0.001: coords = (lat, lon)
                except: coords = None

            if coords:
                try:
                    from timezonefinder import TimezoneFinder
                    import pytz
                    tf = TimezoneFinder()
                    tz_name = tf.timezone_at(lat=coords[0], lng=coords[1])
                    if tz_name:
                        timezone = pytz.timezone(tz_name)
                        dt_obj = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                        aware_dt = timezone.localize(dt_obj)
                        utc_offset = aware_dt.utcoffset()
                        hours = int(utc_offset.total_seconds() / 3600)
                        minutes = int((utc_offset.total_seconds() % 3600) / 60)
                        utc_offset_str = f"UTC{'+' if hours >= 0 else ''}{hours:02d}:{abs(minutes):02d}"
                        has_valid_gps = True
                except: pass
    except: pass

    if has_valid_gps and date_str:
        try:
            dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
            text_date = dt.strftime(f"%Y-%b-%d %H:%M {utc_offset_str}")
        except: pass

    if not text_date:
        if date_str:
            try:
                dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                text_date = dt.strftime(f"%Y-%b-%d %H:%M {chosen_utc}")
            except: date_str = ""
        if not date_str:
            try:
                file_mtime = os.path.getmtime(current_path)
                dt = datetime.fromtimestamp(file_mtime)
                text_date = dt.strftime(f"%Y-%b-%d %H:%M {chosen_utc}")
            except:
                text_date = datetime.now().strftime(f"%Y-%b-%d %H:%M {chosen_utc}")

    line_spacing = int(size * 0.2)
    start_y = h + (p - (size + line_spacing + d_size)) // 2
    visual_center_y = int(start_y + (size * 0.62)) 
    spacing = int(w * 0.01)
    current_x = t

    try:
        if l_file and os.path.exists(l_file):
            logo_img = Image.open(l_file).convert("RGBA")
            logo_h = int(size * 0.95) 
            logo_w = int(logo_img.width * (logo_h / logo_img.height))
            logo_img = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            canvas.paste(logo_img, (int(current_x), int(visual_center_y - (logo_h // 2))), logo_img)
            current_x = current_x + logo_w + int(spacing * 0.7)
    except: pass

    info_x = t + w
    info_width = draw.textlength(text_info, font=font_reg)
    max_available_x = info_x - info_width - (spacing * 2)
    max_text_width = max_available_x - current_x
    current_text_width = draw.textlength(text_camera, font=font_obj)
    camera_stroke_width = 0
    
    if current_text_width > max_text_width:
        scale_factor = max(max_text_width / current_text_width, 0.4)
        new_size = int(size * scale_factor)
        font_obj = create_custom_font(new_size, is_bold=True)
        if scale_factor < 0.8:
            camera_stroke_width = max(1, int(new_size * 0.03))

    draw.text((int(current_x), int(start_y)), text_camera, fill=(0, 0, 0), font=font_obj, anchor="la", stroke_width=camera_stroke_width, stroke_fill=(0, 0, 0))
    draw.text((int(info_x), int(start_y)), text_info, fill=(50, 50, 50), font=font_reg, anchor="ra")

    if text_date:
        date_y = int(start_y + size + line_spacing)
        draw.text((int(info_x), date_y), text_date, fill=(140, 140, 140), font=font_dat, anchor="ra")

    return canvas


def main(page: ft.Page):
    page.title = "📸 폴라로이드 스타일 프레임 생성기"
    page.scroll = ft.ScrollMode.AUTO
    page.theme_mode = ft.ThemeMode.LIGHT

    # 웹 환경 크기 설정
    page.window_width = 650
    page.window_height = 800

    tz_options = [
        "UTC+09:00 (한국/일본/인도네시아 동부)", "UTC+08:00 (중국/대만/홍콩/싱가포르/필리핀)",
        "UTC+07:00 (베트남/태국/인도네시아 서부)", "UTC+05:30 (인도/스리랑카)",
        "UTC+04:00 (두바이/아랍에미리트/오만)", "UTC+03:00 (사우디/터키/동유럽/모스크바)",
        "UTC+02:00 (그리스/이집트/남아공/중유럽 서머타임)", "UTC+01:00 (프랑스/독일/이탈리아/스페인/서유럽)",
        "UTC+00:00 (런던/영국/아일랜드/GMT 표준시)", "UTC-04:00 (미국 동부 서머타임/캐나다)",
        "UTC-05:00 (뉴욕/워싱턴/미국 동부 표준시)", "UTC-06:00 (시카고/미국 중부 표준시)",
        "UTC-08:00 (로스앤젤레스/샌프란시스코/미국 태평양 표준시)", "UTC-10:00 (하와이)",
        "UTC+10:00 (시드니/멜버른/호주 동부)", "UTC+12:00 (뉴질랜드/피지)"
    ]

    selected_files_paths = []
    processed_image_bytes = None
    output_filename = "result_image.jpg"

    status_text = ft.Text("작업할 사진을 하단에서 선택해 주세요.", size=14, color="grey")
    
    # 🛠️ 핵심 조치: 최신 버전 에러('src' 누락)를 극복하기 위해 빈 문자열 임시 할당
    image_preview = ft.Image(src="", visible=False, border_radius=10)
    image_container = ft.Container(content=image_preview, height=450, alignment=ft.alignment.center)
    
    tz_dropdown = ft.Dropdown(
        label="GPS 미검출 시 적용할 타임존 설정",
        options=[ft.dropdown.Option(tz) for tz in tz_options],
        value=tz_options[0],
        width=450,
        visible=False
    )

    def save_file_result(e: ft.FilePickerResultEvent):
        if e.path and processed_image_bytes:
            with open(e.path, "wb") as f:
                f.write(processed_image_bytes)
            status_text.value = f"🎉 성공적으로 저장되었습니다: {os.path.basename(e.path)}"
            page.update()

    save_file_picker = ft.FilePicker(on_result=save_file_result)
    page.overlay.append(save_file_picker)

    download_btn = ft.ElevatedButton(
        text="프레임 합성 사진 저장하기",
        icon=ft.icons.SAVE,
        color="white",
        bgcolor="blue",
        visible=False,
        on_click=lambda _: save_file_picker.save_file(file_name=output_filename, allowed_extensions=["jpg"])
    )

    def process_image():
        nonlocal processed_image_bytes, output_filename
        if not selected_files_paths:
            return
        
        img_path = selected_files_paths[0]
        output_filename = f"result_{os.path.basename(img_path)}"
        
        try:
            picture = Picture(img_path)
            image = picture.get_image()
            if image is None:
                status_text.value = "❌ 이미지를 읽을 수 없습니다."
                page.update()
                return

            width, height = image.size
            thickness = get_thickness(height)
            padding = get_padding(height)
            
            logo_file = logo(picture)
            if not logo_file:
                exif_str = str(image._getexif()).upper()
                if "SONY" in exif_str or "ILCE" in exif_str or "ZV-" in exif_str:
                    logo_file = "logos/sony.png"

            single_chosen_utc = tz_dropdown.value.split(" ")[0]

            base_canvas = add_border(image, width, height, thickness, padding)
            final_canvas = place_model(
                base_canvas, picture, width, height, thickness, padding, logo_file, 
                chosen_utc=single_chosen_utc, current_path=img_path
            )

            buf = io.BytesIO()
            final_canvas.save(buf, format="JPEG", quality=95)
            processed_image_bytes = buf.getvalue()

            image_preview.src_bytes = processed_image_bytes
            image_preview.visible = True
            download_btn.visible = True
            status_text.value = f"✅ 처리 완료! ({os.path.basename(img_path)})"
        except Exception as ex:
            status_text.value = f"⚠️ 오류 발생: {ex}"
        
        page.update()

    tz_dropdown.on_change = lambda _: process_image()

    def pick_files_result(e: ft.FilePickerResultEvent):
        if e.files:
            selected_files_paths.clear()
            selected_files_paths.append(e.files[0].path)
            tz_dropdown.visible = True
            process_image()

    file_picker = ft.FilePicker(on_result=pick_files_result)
    page.overlay.append(file_picker)

    upload_btn = ft.FilledButton(
        text="사진 가져오기 (컴퓨터에서 선택)",
        icon=ft.icons.PHOTO_LIBRARY,
        on_click=lambda _: file_picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)
    )

    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text("📸 데스크톱 폴라로이드 프레임 툴", size=24, weight=ft.FontWeight.BOLD),
                    status_text,
                    ft.Divider(),
                    image_container,
                    tz_dropdown,
                    ft.Row([upload_btn, download_btn], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20
            ),
            padding=20,
            alignment=ft.alignment.center
        )
    )

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8502))
    ft.app(target=main, port=port, host="0.0.0.0", assets_dir=".")
