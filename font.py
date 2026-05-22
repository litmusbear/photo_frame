import PIL.ImageFont as ImageFont

FONT_PATH = "fonts/HelveticaNeue.ttc"
def font_size(padding):
    font_size = int(padding * 0.18)
    date_font_size = int(font_size * 0.65)
    return font_size, date_font_size

def set_font(padding):
    size = font_size(padding)[0]

    try:
        font = ImageFont.truetype(FONT_PATH, size, index=1)
    except:
        font = ImageFont.load_default()
    return font

def regular(padding):
    size = font_size(padding)[0]
    try:
        font_regular = ImageFont.truetype(FONT_PATH, size, index=0)
    except:
        font_regular= ImageFont.load_default()
    return font_regular

def date_font(padding):
    date_font_size = font_size(padding)[1]
    try:
        font_date = ImageFont.truetype(FONT_PATH, date_font_size, index=0)
    except:
        font_date = ImageFont.load_default()
    return font_date