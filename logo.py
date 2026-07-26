def logo(picture):
    make = picture.exif.get("Make", "").upper()
    camera_model = picture.get_camera().upper()
    logo_file = None

    if "LEICA" in make or "LEICA" in camera_model:
        logo_file = "logos/leica.png"
    elif "NIKON" in make or "NIKON" in camera_model:
        logo_file = "logos/nikon.png"
    elif "SONY" in make or "SONY" in camera_model:
        logo_file = "logos/sony.png"
    elif "CANON" in make or "CANON" in camera_model:
        logo_file = "logos/canon.png"
    elif "APPLE" in make or "IPHONE" in camera_model or "IPAD" in camera_model:
        logo_file = "logos/apple.png"
    elif "SAMSUNG" in make or "SAMSUNG" in camera_model or "SM" in camera_model:
        logo_file = "logos/samsung.png"
    elif "FUJIFILM" in make or "FUJIFILM" in camera_model:
        logo_file = "logos/fujifilm.png"
    elif "OLYMPUS" in make or "OLYMPUS" in camera_model:
        logo_file = "logos/olympus.png"
    elif "RICOH" in make or "RICOH" in camera_model:
        logo_file = "logos/ricoh.png"

    if not logo_file:
        exif_str = str(picture.exif).upper()
        if "SONY" in exif_str or "ILCE" in exif_str or "ZV-" in exif_str:
            logo_file = "logos/sony.png"

    return logo_file