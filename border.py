def get_width(image):
    width = image.size[0]
    return width


def get_height(image):
    height = image.size[1]
    return height


def get_thickness(height):
    thickness = int(height * 0.03)
    return thickness


def get_padding(height):
    padding = int(height * 0.15)
    return padding