from PIL import Image
import numpy as np
# discard os 
import os
# better option
import subprocess
# using python thread to delay while image is getting converted to png
import threading

def crop_image(img, Output_path):
    
    """Crops image to content
    Args:
        img: (string) path to image
        output_path: (string) path to output image
    """

    old_im = Image.open(img).convert('L')
    img_data = np.asarray(old_im, dtype=np.uint8)
    nnz_inds = np.where(img_data!=255)
    if len(nnz_inds[0]) == 0:
        old_im.save(Output_path)
        return False

    y_min = np.min(nnz_inds[0])
    y_max = np.max(nnz_inds[0])
    x_min = np.min(nnz_inds[1])
    x_max = np.max(nnz_inds[1])
    old_im = old_im.crop((x_min, y_min, x_max+1, y_max+1))
    old_im.save(Output_path)
    return True

def get_new_size(old_size, buckets):
    """Computes new size from buckets
    Args:
        old_size: (width, height)
        buckets: list of sizes
    Returns:
        new_size: original size or first bucket in iter order that matches the
            size.
    """
    if buckets is None:
        return old_size
    else:
        w, h = old_size
        for (w_b, h_b) in buckets:
            if w_b >= w and h_b >= h:
                return w_b, h_b

        return old_size

def pad_image(img, output_path, pad_size = [8,8,8,8],  buckets=None):
    """Pads image with pad size and with buckets
    Args:
        img: (string) path to image
        output_path: (string) path to output image
        pad_size: list of 4 ints
        buckets: ascending ordered list of sizes, [(width, height), ...]
    """
    top, left, bottom, right = pad_size
    old_im = Image.open(img)
    old_size = (old_im.size[0] + left + right, old_im.size[1] + top  + bottom)
    new_size = get_new_size(old_size, buckets)
    new_im = Image.new("RGB", new_size, (255,255,255))
    new_im.paste(old_im, (left, top))
    new_im.save(output_path)

def conv(img, output_path, pad_size=[8,8,8,8], buckets=None):
    top, left, bottom, right = pad_size
    return top, left, bottom, right

def downsample_image(img, output_path, ratio=2):

    """Downsample image by ratio"""
    
    assert ratio>=1, ratio
    if ratio == 1:
        return True
    old_im = Image.open(img)
    old_size = old_im.size
    new_size = (int(old_size[0]/ratio), int(old_size[1]/ratio))

    new_im = old_im.resize(new_size, Image.LANCZOS)
    new_im.save(output_path)
    return True

class pdf_2_png:

    def __init__(self, file_name):
        self.pdf_file_name = file_name
        self.img_file_name = 'static\\images\\result'
        self.density = 300
        self.quality = 300
        self.down_ratio = 2
        self.command = None
        self.delay = 1
        self.colorspace = 'RGB'
        # self.file_path = None

        self.create_command()
        self.run()
        # self.thread = threading.Timer(self.delay, self.preprocess_img)
        self.preprocess_img()

    def create_command(self):
        self.command = "magick convert -density {} -quality {} -colorspace {} {} {}".format(self.density, self.quality, self.colorspace, "{}.pdf".format(self.pdf_file_name), "{}.png".format(self.img_file_name))
        return self.command

    def run(self):
        subprocess.call(self.command, shell=True)

    def preprocess_img(self):
        self.file_path = self.img_file_name + ".png"
        crop_image(self.file_path, self.file_path)
        pad_image(self.file_path, self.file_path)
        downsample_image(self.file_path, self.file_path, self.down_ratio)

    def get_img_filename(self):
        return self.img_file_name + '.png'

if __name__ == "__main__":
    obj = pdf_2_png('sake\\temp')
    print(obj.get_img_filename())