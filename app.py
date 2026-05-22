import flet as ft
import os
import io
import base64
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# --- 내부 의존성 통합 및 안전장치 선언 ---
class DummyPicture:
    def __init__(self, pil_img):
        self.img = pil_img
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

def place_model(canvas, pic, w, h, t, p, chosen_utc="UTC+09:00"):
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

    page.window_width = 650
    page.window_height = 800

    tz_options = [
        "UTC+09:00 (한국/일본)", "UTC+08:00 (중국/대만)",
        "UTC+07:00 (베트남/태국)", "UTC+00:00 (런던/GMT)"
    ]

    # 웹 환경 대응을 위해 가상 경로 대신 램 상의 바이트(Bytes) 정보로 상태 관리
    uploaded_file_bytes = None
    processed_image_bytes = None
    file_name_holder = ["result.jpg"]

    status_text = ft.Text("작업할 사진을 하단에서 선택해 주세요.", size=14, color="grey")
    image_preview = ft.Image(src="", visible=False, border_radius=10)
    
    # 🛠️ [들여쓰기 수정 완료] 공백 라인을 칼같이 정렬했습니다.
    image_container = ft.Container(
        content=image_preview, 
        height=450, 
        alignment=ft.Alignment(0, 0)
    )

    tz_dropdown = ft.Dropdown(
        label="타임존 설정",
        options=[ft.dropdown.Option(tz) for tz in tz_options],
        value=tz_options[0],
        width=450,
        visible=False
    )

    # 웹 전용 다운로드 핸들러 브릿지
    def start_download(e):
        if processed_image_bytes:
            # 브라우저에 바이너리 데이터를 직접 던져 다운로드를 유도하는 Flet 내장 API 활용
            base64_data = base64.b64encode(processed_image_bytes).decode("utf-8")
            page.launch_url(f"data:image/jpeg;base64,{base64_data}", web_window_name=file_name_holder[0])
            status_text.value = f"🎉 다운로드 요청 완료!"
            page.update()

    download_btn = ft.ElevatedButton(
        text="프레임 합성 사진 저장하기",
        icon=ft.icons.SAVE,
        color="white",
        bgcolor="blue",
        visible=False,
        on_click=start_download
    )

    def process_image():
        nonlocal processed_image_bytes
        if uploaded_file_bytes is None: return
        
        try:
            # 서버 로컬 파일이 아닌, 업로드된 스트림 바이트로부터 직접 기동
            raw_img = Image.open(io.BytesIO(uploaded_file_bytes))
            picture = DummyPicture(raw_img)
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
            final_canvas = place_model(base_canvas, picture, width, height, thickness, padding, chosen_utc=single_chosen_utc)

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

    # 웹 업로드용 이벤트 핸들러 패치
    def pick_files_result(e: ft.FilePickerResultEvent):
        nonlocal uploaded_file_bytes
        if e.files:
            file_info = e.files[0]
            file_name_holder[0] = f"polaroid_{file_info.name}"
            
            # 렌더 서버 환경에서는 e.files[0].path가 무조건 None이므로 웹 업로드용 전용 API 서치
            if page.web:
                # Flet 웹 서버가 클라이언트로부터 브라우저 메모리 버퍼를 주입받는 통로
                import requests
                # Flet이 제공하는 임시 파일 주소로부터 바이트 추출
                uploaded_file_bytes = requests.get(file_info.path).content if file_info.path.startswith("http") else None
            
            # 일반 로컬 호스트 테스트용 대체제 빌드업
            if not uploaded_file_bytes and file_info.path and os.path.exists(file_info.path):
                with open(file_info.path, "rb") as f:
                    uploaded_file_bytes = f.read()

            if uploaded_file_bytes:
                tz_dropdown.visible = True
                process_image()
            else:
                status_text.value = "❌ 웹 파일 스트림 획득에 실패했습니다."
                page.update()

    file_picker = ft.FilePicker(on_result=pick_files_result)
    page.overlay.append(file_picker)

    upload_btn = ft.FilledButton(
        text="사진 가져오기",
        icon=ft.icons.PHOTO_LIBRARY,
        on_click=lambda _: file_picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)
    )

    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text("📸 폴라로이드 프레임 툴", size=24, weight=ft.FontWeight.BOLD),
                    status_text,
                    ft.Divider(),
                    image_container,
                    tz_dropdown,
                    ft.Row([upload_btn, download_btn], alignment="center", spacing=15),
                ],
                horizontal_alignment="center",
                spacing=20
            ),
            padding=20,
            alignment=ft.alignment.Center if hasattr(ft, 'alignment') else "center"
        )
    )

# app.py 맨 밑바닥의 구동부를 이 코드로 덮어씌워 줍니다.
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8502))
    
    # 렌더 배포 서버용 ft.run / ft.app 하위 호환 크로스오버 구동
    if hasattr(ft, 'run'):
        # 💡 target=main이 아니라 첫 번째 인자로 main 함수를 바로 던져줍니다.
        ft.run(main, port=port, host="0.0.0.0")
    else:
        ft.app(target=main, port=port, host="0.0.0.0")
