from io import BytesIO

import numpy
import requests
import skimage
from PIL import ImageEnhance, Image
from skimage import filters

DEFAULT_PREVIEW_SIZE = 500

DEFAULT_THUMB_SIZE = (256, 256)

BOOST_LOWER = [0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 1.0]

GOTHAM_ADJUST = [0, 0.047, 0.118, 0.251, 0.318, 0.392, 0.42,
                 0.439, 0.475, 0.561, 0.58, 0.627, 0.671, 0.733,
                 0.847, 0.925, 1]


def channel_adjust(channel, values):
    adjusted = numpy.interp(
        channel.flatten(),
        numpy.linspace(0, 1, len(values)),
        values)

    return adjusted.reshape(channel.shape)


def red_channel(array):
    return array[:, :, 0]


def green_channel(array):
    return array[:, :, 1]


def blue_channel(array):
    return array[:, :, 2]


def split_channels(image):
    red = image[:, :, 0]
    green = image[:, :, 1]
    blue = image[:, :, 2]

    return red, green, blue


def merge_channels(red, green, blue):
    return numpy.stack([red, green, blue], axis=2)


def float_to_uint8(array):
    return (array * 255 / numpy.max(array)).astype(numpy.uint8)


def increase_channel(channel, x):
    return numpy.clip(channel + x, 0, 1.0)


def decrease_channel(channel, x):
    return numpy.clip(channel - x, 0, 1.0)


def sharpen(array):
    blurred = filters.gaussian(array, sigma=10, multichannel=True)
    final = numpy.clip(array * 1.3 - blurred * 0.3, 0, 1.0)

    return final


def filterable_to_rgb(filterable):
    return split_channels(skimage.img_as_float(filterable.as_array()))


def square_portrait(height, width):
    top = numpy.ceil((height - width) / 2.)
    bottom = numpy.floor((width + height) / 2.)

    return 0, int(top), width, int(bottom)


def square_landscape(height, width):
    left = numpy.ceil((width - height) / 2.)
    right = numpy.floor((width + height) / 2.)

    return int(left), 0, int(right), height


def square_crop_coords(image):
    width, height = image.size

    if width < height:
        return square_portrait(height, width)

    if height < width:
        return square_landscape(height, width)

    return 0, 0, width, height


def preview_size(size, max_size):
    width, height = size

    if width < max_size and height < max_size:
        return size

    if width > height:
        return max_size, (height / (width / max_size))

    return (width / (height / max_size)), max_size


class Filterable:

    def __init__(self, pillow):
        self.pillow = pillow

    @classmethod
    def from_url(cls, url):
        response = requests.get(url=url, stream=True)
        response.raw.decode_content = True

        return cls(Image.open(response.raw))

    @classmethod
    def from_array(cls, opencv):
        return cls(Image.fromarray(opencv))

    def as_array(self):
        return numpy.array(self.pillow).copy()

    def thumbnail(self, size=DEFAULT_THUMB_SIZE):
        thumb = self.pillow.copy()
        thumb.thumbnail(size, Image.ANTIALIAS)

        return thumb

    def preview(self, max_size=DEFAULT_PREVIEW_SIZE):
        return self.thumbnail(preview_size(self.pillow.size, max_size))

    def square_thumb(self, size=DEFAULT_THUMB_SIZE):
        thumb = self.pillow.copy()
        square = thumb.crop(square_crop_coords(thumb))
        square.thumbnail(size, Image.ANTIALIAS)

        return square

    def as_bytes(self):
        file_obj = BytesIO()

        self.pillow.save(file_obj, 'jpeg')

        return file_obj

    def thumb_bytes(self, size=DEFAULT_THUMB_SIZE):
        return Filterable(self.thumbnail(size)).as_bytes()

    def preview_bytes(self, max_size=DEFAULT_PREVIEW_SIZE):
        return Filterable(self.preview(max_size)).as_bytes()

    def square_thumb_bytes(self, size=DEFAULT_THUMB_SIZE):
        return Filterable(self.square_thumb(size)).as_bytes()


class BaseFilter:

    # from mathplotlib import pyplot as plt
    # plt.imshow(formatted)
    # plt.show()

    @staticmethod
    def id():
        pass

    @staticmethod
    def name():
        pass

    @staticmethod
    def apply(filterable):
        pass


class BlackAndWhite(BaseFilter):

    @staticmethod
    def id():
        return "black_and_white"

    @staticmethod
    def name():
        return "Black and White"

    @staticmethod
    def apply(filterable):
        return Filterable(ImageEnhance.Color(filterable.pillow).enhance(0.0))


class Gotham(BaseFilter):

    @staticmethod
    def id():
        return "gotham"

    @staticmethod
    def name():
        return "Gotham"

    @staticmethod
    def apply(filterable):
        r, g, b = filterable_to_rgb(filterable)

        final = merge_channels(
            channel_adjust(r, BOOST_LOWER),
            g,
            increase_channel(b, 0.03))

        final[:, :, 2] = channel_adjust(blue_channel(final), GOTHAM_ADJUST)

        return Filterable.from_array(float_to_uint8(final))


class Bridge(BaseFilter):

    @staticmethod
    def id():
        return "bridge"

    @staticmethod
    def name():
        return "Bridge"

    @staticmethod
    def apply(filterable):
        r, g, b = filterable_to_rgb(filterable)

        r_lower = channel_adjust(r, BOOST_LOWER)

        final = merge_channels(
            channel_adjust(r_lower, GOTHAM_ADJUST),
            decrease_channel(g, 0.03),
            b)

        final = sharpen(final)

        return Filterable.from_array(float_to_uint8(final))


class Brighter(BaseFilter):

    @staticmethod
    def id():
        return "brighter"

    @staticmethod
    def name():
        return "Brighter"

    @staticmethod
    def apply(filterable):
        r, g, b = filterable_to_rgb(filterable)

        final = merge_channels(
            increase_channel(r, 0.2),
            increase_channel(g, 0.2),
            increase_channel(b, 0.2))

        return Filterable.from_array(float_to_uint8(final))
