def logo(picture):
    camera_model = picture.get_camera().upper()
    logo_file = None
    if "LEICA" in camera_model:
        logo_file = "logos/leica.png"
    elif "NIKON" in camera_model:
        logo_file = "logos/nikon.png"
    elif "SONY" in camera_model:
        logo_file = "logos/sony.png"
    elif "CANON" in camera_model:
        logo_file = "logos/canon.png"
    elif "IPHONE" in camera_model or "IPAD" in camera_model:
        logo_file = "logos/apple.png"
    elif "SAMSUNG" in camera_model or "SM" in camera_model:
        logo_file = "logos/samsung.png"
    elif "FUJIFILM" in camera_model:
        logo_file = "logos/fujifilm.png"

    if not logo_file:
                exif_str = str(image._getexif()).upper()
                if "SONY" in exif_str or "ILCE" in exif_str or "ZV-" in exif_str:
                    logo_file = "logos/sony.png"

    return logo_file
