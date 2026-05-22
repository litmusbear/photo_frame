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
    elif "IPHONE" in camera_model:
        logo_file = "logos/apple.png"
    elif "SAMSUNG" in camera_model:
        logo_file = "logos/samsung.png"

    return logo_file