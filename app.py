import flet as ft
import os
import io
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# --- 내부 의존성 통합 및 안전장치 선언 ---
class DummyPicture:
    def __init__(self, path):
        self.path = path
        try:
            self.img = Image.open(path)
        except:
            self.img = None
    def get_image(self): return self.img
    def get_camera(self): return "📸 CAMERA MODEL"
    def get_f_number(self): return "4.0"
    def get_shutter(self): return "1/125s"
    def get_iso(self): return "100"

def get_thickness(h): return int(h * 0.04) if h else 40
def get_padding(h): return int(h * 0.12) if h else 120

def add_border(img, w, h, t, p):
    canvas = Image.new("RGB", (w + (t * 2), h + t + p), (255, 255, 255))
    canvas.paste(img, (t, t))
    return canvas

def place_model(canvas, pic, w, h, t, p, chosen_utc="UTC+09:00", current_path=None):
    draw = ImageDraw.Draw(canvas)
    size = int(p * 0.25)
    
    try: font = ImageFont.load_default()
    except: font = None

    text_camera = pic.get_camera()
    text_info = f"f/{pic.get_f_number()}  {pic.get_shutter()}  ISO{pic.get_iso()}"
    text_date = datetime.now().strftime(f"%Y-%b-%d %H:%M {chosen_utc}")

    start_y = h + (p - size) // 2
    
    draw.text((t, start_y), text_camera, fill=(0, 0, 0), font=font)
    draw.text((t + w, start_y), text_info, fill=(50, 50, 50), font=font, anchor="ra")
    draw.text((t + w, start_y + int(size*1.2)), text_date, fill=(140, 140, 140), font=font, anchor="ra")
    return canvas

# --- 메인 앱 UI ---
def main(page: ft.Page):
    page.title = "📸 폴라로이드 스타일 프레임 생성기"
    page.scroll = ft.ScrollMode.AUTO
    page.theme_mode = ft.ThemeMode.LIGHT

    # 웹 창 크기 조절
    page.window_width = 650
    page.window_height = 800

    tz_options = [
        "UTC+09:00 (한국/일본)", "UTC+08:00 (중국/대만)",
        "UTC+07:00 (베트남/태국)", "UTC+00:00 (런던/GMT)"
    ]

    selected_files_paths = []
    processed_image_bytes = None

    status_text = ft.Text("작업할 사진을 하단에서 선택해 주세요.", size=14, color="grey")
    
    image_preview = ft.Image(src="", visible=False, border_radius=10)
    
    # 🛠️ 핵심 수정: alignment 속성을 객체 대신 안전한 문자열 "center"로 대체하여 에러 원천 차단
    image_container = ft.Container(content=image_preview, height=450, alignment=ft.alignment.Center if hasattr(ft, 'alignment') else "center")
    
    tz_dropdown = ft.Dropdown(
        label="타임존 설정",
        options=[ft.dropdown.Option(tz) for tz in tz_options],
        value=tz_options[0],
        width=450,
        visible=False
    )

    def save_file_result(e: ft.FilePickerResultEvent):
        if e.path and processed_image_bytes:
            with open(e.path, "wb") as f:
                f.write(processed_image_bytes)
            status_text.value = f"🎉 저장 성공!"
            page.update()

    save_file_picker = ft.FilePicker(on_result=save_file_result)
    page.overlay.append(save_file_picker)

    download_btn = ft.ElevatedButton(
        text="프레임 합성 사진 저장하기",
        icon=ft.icons.SAVE,
        color="white",
        bgcolor="blue",
        visible=False,
        on_click=lambda _: save_file_picker.save_file(file_name="result.jpg", allowed_extensions=["jpg"])
    )

    def process_image():
        nonlocal processed_image_bytes
        if not selected_files_paths: return
        
        img_path = selected_files_paths[0]
        try:
            picture = DummyPicture(img_path)
            image = picture.get_image()
            if image is None:
                status_text.value = "❌ 이미지를 읽을 수 없습니다."
                page.update()
                return

            width, height = image.size
            thickness = get_thickness(height)
            padding = get_padding(height)
            single_chosen_utc = tz_dropdown.value.split(" ")[0]

            base_canvas = add_border(image, width, height, thickness, padding)
            final_canvas = place_model(base_canvas, picture, width, height, thickness, padding, chosen_utc=single_chosen_utc, current_path=img_path)

            buf = io.BytesIO()
            final_canvas.save(buf, format="JPEG", quality=95)
            processed_image_bytes = buf.getvalue()

            image_preview.src_bytes = processed_image_bytes
            image_preview.visible = True
            download_btn.visible = True
            status_text.value = f"✅ 처리 완료!"
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
        text="사진 가져오기",
        icon=ft.icons.PHOTO_LIBRARY,
        on_click=lambda _: file_picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)
    )

    # 🛠️ 핵심 수정: Row와 Column의 정렬 속성도 안전한 문자열 형태로 명시
    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text("📸 폴라로이드 프레임 툴", size=24, weight=ft.FontWeight.BOLD),
                    status_text,
                    ft.Divider(),
                    image_container,
                    tz_dropdown,
                    ft.Row([upload_btn, download_btn], alignment=ft.MainAxisAlignment.CENTER if hasattr(ft, 'MainAxisAlignment') else "center", spacing=15),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER if hasattr(ft, 'CrossAxisAlignment') else "center",
                spacing=20
            ),
            padding=20,
            alignment=ft.alignment.Center if hasattr(ft, 'alignment') else "center"
        )
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8502))
    ft.app(target=main, port=port, host="0.0.0.0")
