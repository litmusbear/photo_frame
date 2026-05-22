import streamlit as st
from PIL import Image, ImageDraw
import uuid
import os
import io

from get_data import Picture
from font import *
from logo import logo
from border import *

st.title("📸 폴라로이드 스타일 사진 프레임 생성기")

uploaded_files = st.file_uploader("사진들을 업로드하세요", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files:
    temp_file_paths = []

    for uploaded_file in uploaded_files:
        unique_id = uuid.uuid4().hex
        temp_path = f"temp_{unique_id}.jpg"
        temp_file_paths.append(temp_path)

        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        try:
            # 1. 데이터 불러오기
            picture = Picture(temp_path)
            image = picture.get_image()
            if image is None:
                raise ValueError("이미지를 읽을 수 없습니다.")

            width, height = image.size
            thickness = get_thickness(height)
            padding = get_padding(height)
            logo_file = logo(picture)


            # 2. 테두리 추가 함수
            def add_border(img, w, h, t, p):
                border_width = w + (t * 2)
                border_height = h + t + p
                canvas = Image.new("RGB", (border_width, border_height), (255, 255, 255))
                canvas.paste(img, (t, t))
                return canvas


            # 3. 모델명/정보/로고/날짜 배치 함수 (Y축 정렬 수정 버전)
            def place_model(canvas, pic, w, h, t, p, l_file):
                font_obj = set_font(p)
                font_reg = regular(p)
                font_dat = date_font(p)
                size, d_size = font_size(p)

                draw = ImageDraw.Draw(canvas)

                text_camera = pic.get_camera()
                text_info = f"f/{pic.get_f_number()}  {pic.get_shutter()}  ISO{pic.get_iso()}"
                text_date = pic.get_datetime()

                # 좌우 좌표: 사진 라인에 맞춤
                camera_x = t
                info_x = t + w

                line_spacing = int(size * 0.2)
                total_text_height = size + line_spacing + d_size

                # 오른쪽 정보 첫 줄의 Y 시작점
                start_y = h + (p - total_text_height) // 2
                # 로고 중앙 정렬을 위한 보정값
                visual_top_y = int(start_y + (size * 0.52))

                spacing = int(w * 0.012)
                current_camera_x = camera_x

                # [로고 처리]
                try:
                    if l_file and os.path.exists(l_file):
                        logo_img = Image.open(l_file).convert("RGBA")
                        logo_h = int(size * 1.0)
                        logo_w = int(logo_img.width * (logo_h / logo_img.height))
                        logo_img = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)

                        logo_x = current_camera_x
                        logo_y = int(visual_top_y - (logo_h // 2))
                        canvas.paste(logo_img, (logo_x, logo_y), logo_img)

                        current_camera_x = logo_x + logo_w + spacing
                except Exception:
                    pass

                # [텍스트 그리기]
                # 기기명을 anchor="la"(왼쪽 상단)로 설정하여 start_y 라인에 맞춤
                draw.text((current_camera_x, start_y), text_camera, fill=(0, 0, 0), font=font_obj, anchor="la")

                # 우측 촬영 정보 (동일한 start_y)
                draw.text((info_x, start_y), text_info, fill=(50, 50, 50), font=font_reg, anchor="ra")

                # 우측 하단 날짜
                if text_date:
                    date_y = start_y + size + line_spacing
                    draw.text((info_x, date_y), text_date, fill=(140, 140, 140), font=font_dat, anchor="ra")

                return canvas


            # 실행 및 출력
            base_canvas = add_border(image, width, height, thickness, padding)
            final_canvas = place_model(base_canvas, picture, width, height, thickness, padding, logo_file)

            st.image(final_canvas, caption=f"결과물: {uploaded_file.name}", use_container_width=True)

            buf = io.BytesIO()
            final_canvas.save(buf, format="JPEG", quality=95)
            st.download_button(
                label=f"{uploaded_file.name} 저장",
                data=buf.getvalue(),
                file_name=f"result_{uploaded_file.name}",
                key=unique_id
            )

        except Exception as e:
            st.error(f"⚠️ '{uploaded_file.name}' 처리 중 오류 발생: {e}")
            continue

        st.divider()

    # 사용 완료된 임시 파일 삭제
    for path in temp_file_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass