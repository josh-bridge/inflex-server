import datetime

import matplotlib.pyplot as plt
from PIL import Image
from matplotlib.colors import rgb_to_hsv, hsv_to_rgb
from sklearn.cluster import KMeans

import numpy as np
import cv2

from app.web.util import upload_colour_sample


def centroid_histogram(kmeans):
    # grab the number of different clusters and create a histogram
    # based on the number of pixels assigned to each cluster
    numLabels = np.arange(0, len(np.unique(kmeans.labels_)) + 1)
    (hist, _) = np.histogram(kmeans.labels_, bins=numLabels)

    # normalize the histogram, such that it sums to one
    hist = hist.astype("float")
    hist /= hist.sum()

    # return the histogram
    return hist


def plot_colors(hist, centroids):
    # initialize the bar chart representing the relative frequency
    # of each of the colors
    bar = np.zeros((50, 300, 3), dtype="uint8")
    startX = 0

    # loop over the percentage of each cluster and the color of
    # each cluster
    for (percent, color) in zip(hist, centroids):
        # plot the relative percentage of each cluster
        endX = startX + (percent * 300)
        cv2.rectangle(bar, (int(startX), 0), (int(endX), 50),
                      color.astype("uint8").tolist(), -1)
        startX = endX

    # return the bar chart
    return bar


def colour_sample(colour, height=100, width=100):
    blank_image = blank_array(height, width)

    blank_image[:, :] = (colour[0], colour[1], colour[2])

    img = Image.fromarray(blank_image)
    plt.imshow(img)
    plt.show()

    return img


def blank_array(height, width):
    return np.zeros((height, width, 3), np.uint8)


def sort_by_vibrance(hsv_colours):
    dimensions = (len(hsv_colours), 1)

    vibrances = np.reshape(hsv_colours[:, 1] * hsv_colours[:, 2], dimensions)

    vib_channel = np.append(hsv_colours, vibrances, axis=1)

    return hsv_colours[vib_channel[:, 3].argsort()[::-1]]


def rgb_json(rgb_colour):
    return {
        "red": int(rgb_colour[0]),
        "green": int(rgb_colour[1]),
        "blue": int(rgb_colour[2])
    }


# def norm_hsv(colour):
#     return np.array([colour[2], colour[1] * 100.0, colour[0] * 100.0]).astype(np.uint8)


def hsv_json(hsv_colour):
    return {
        "hue": float(hsv_colour[0]),
        "saturation": float(hsv_colour[1]),
        "value": float(hsv_colour[2])
    }


def get_dom_colours(hist, colours):
    dominant = []
    # cols = numpy.uint8(colours)
    hsv_colours = rgb_to_hsv(colours)
    most_vib_hsv = sort_by_vibrance(hsv_colours)
    most_vib = hsv_to_rgb(most_vib_hsv[0]).astype(np.uint8)

    # colour_sample(most_vib)

    for (percent, colour) in zip(hist, colours.astype(np.uint8)):
        hsv = rgb_to_hsv(colour)
        dominant.append(
            {
                "percent": int(percent * 100),
                "rgb": rgb_json(colour),
                "hsv": hsv_json(hsv)
            })

    vibrant = {
        "rgb": rgb_json(most_vib),
        "hsv": hsv_json(most_vib_hsv[0]),
        "sample": upload_colour_sample(rgb_json(most_vib))
    }

    return vibrant, dominant


def analyze(filterable):
    # load the image and convert it from BGR to RGB so that
    # we can dispaly it with matplotlib
    # start = datetime.datetime.now()

    # hsv_im = cv2.cvtColor(numpy.asarray(im), cv2.COLOR_RGB2HSV_FULL)
    # hue, sat, lig = split_channels(hsv_im)
    # neg_sat = ((0 - sat) + 255)
    # new_lol = cv2.cvtColor(merge_channels(hue, sat, lig), cv2.COLOR_HSV2RGB_FULL)
    # plt.imshow(new_lol, cmap='gray')
    # plt.show()
    # tst_out = Image.fromarray(new_lol)
    # tst_out.save("test_out.jpg", "jpeg")
    # im = filterable.resize((100, 100))  # optional, to reduce time
    # im = im.filter(ImageFilter.GaussianBlur(1))
    image = np.asarray(filterable.thumbnail((100, 100)))
    # image = filterable.as_array()
    # image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    # show our image
    # plt.figure()
    # plt.axis("off")
    # plt.imshow(image)
    # reshape the image to be a list of pixels
    image = image.reshape((image.shape[0] * image.shape[1], 3))
    # cluster the pixel intensities
    kmeans = KMeans(n_clusters=5)

    # run analysis
    kmeans.fit(image)

    # print((datetime.datetime.now() - start))
    # build a histogram of clusters and then create a figure
    # representing the number of pixels labeled to each color
    hist = centroid_histogram(kmeans)
    # bar = plot_colors(hist, kmeans.cluster_centers_)
    # show our color bart
    # plt.figure()
    # plt.axis("off")
    # plt.imshow(bar)
    # plt.show()
    return get_dom_colours(hist, kmeans.cluster_centers_)
    # return "", ""
