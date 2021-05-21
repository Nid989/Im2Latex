from dataset.dataset import test_transform
import cv2
import pandas as pd
from PIL import ImageGrab
from PIL import Image
import os
import sys
import argparse
import logging
import yaml
import re

import numpy as np
import torch
from torchvision import transforms
from munch import Munch
from transformers import PreTrainedTokenizerFast
from timm.models.resnetv2 import ResNetV2
from timm.models.layers import StdConv2dSame

from dataset.latex2png import tex2pil
from models import get_model
from utils import *

last_pic = None

def minmax_size(img, max_dimensions):
    ratios = [a/b for a, b in zip(img.size, max_dimensions)]
    if any([r > 1 for r in ratios]):
        size = np.array(img.size)//max(ratios)
        img = img.resize(size.astype(int), Image.BILINEAR)
    return img

def initialize(arguments):
    with open(arguments['config'], 'r') as f:
        params = yaml.load(f, Loader=yaml.FullLoader)
    args = Munch(params)
    # args.update(**vars(arguments))
    args.update(arguments)
    args.wandb = False
    args.device = 'cuda' if torch.cuda.is_available() and not args.no_cuda else 'cpu'

    model = get_model(args)
    model.load_state_dict(torch.load(args.checkpoint, map_location=args.device))

    if 'image_resizer.pth' in os.listdir(os.path.dirname(args.checkpoint)) and not arguments['no_resize']:
        image_resizer = ResNetV2(layers=[2, 3, 3], num_classes=22, global_pool='avg', in_chans=1, drop_rate=.05,
                                 preact=True, stem_type='same', conv_layer=StdConv2dSame).to(args.device)
        image_resizer.load_state_dict(torch.load(os.path.join(os.path.dirname(args.checkpoint), 'image_resizer.pth'), map_location=args.device))
        image_resizer.eval()
    else:
        image_resizer = None
    tokenizer = PreTrainedTokenizerFast(tokenizer_file=args.tokenizer)
    return args, model, image_resizer, tokenizer


def call_model(args, model, image_resizer, tokenizer):
    global last_pic
    encoder, decoder = model.encoder, model.decoder
    if args.file:
        img = Image.open(args.file)
    else:
        img = ImageGrab.grabclipboard()
    if img is None:
        if last_pic is None:
            print('Copy an image into the clipboard.')
            return
        else:
            img = last_pic
    else:
        last_pic = img.copy()
    img = minmax_size(pad(img), args.max_dimensions)
    if image_resizer is not None and not args.no_resize:
        with torch.no_grad():
            input_image = pad(img).convert('RGB').copy()
            r, w = 1, img.size[0]
            for i in range(10):
                img = minmax_size(input_image.resize((w, int(input_image.size[1]*r)), Image.BILINEAR if r > 1 else Image.LANCZOS), args.max_dimensions)
                t = test_transform(image=np.array(pad(img).convert('RGB')))['image'][:1].unsqueeze(0)
                w = image_resizer(t.to(args.device)).argmax(-1).item()*32
                if (w/img.size[0] == 1):
                    break
                r *= w/img.size[0]
    else:
        img = np.array(pad(img).convert('RGB'))
        t = test_transform(image=img)['image'][:1].unsqueeze(0)
    # print("processing... \n")
    im = t.to(args.device)

    with torch.no_grad():
        model.eval()
        device = args.device
        encoded = encoder(im.to(device))
        dec = decoder.generate(torch.LongTensor([args.bos_token])[:, None].to(device), args.max_seq_len,
                               eos_token=args.eos_token, context=encoded.detach(), temperature=args.temperature)
        pred = post_process(token2str(dec, tokenizer)[0])
    # print(pred, '\n')
    df = pd.DataFrame([pred])
    df.to_clipboard(index=False, header=False)
    if args.show or args.katex:
        try:
            if args.katex:
                raise ValueError
            tex2pil([f'$${pred}$$'])[0].show()
        except Exception as e:
            # render using katex
            import webbrowser
            from urllib.parse import quote
            url = 'https://katex.org/?data=' + \
                quote('{"displayMode":true,"leqno":false,"fleqn":false,"throwOnError":true,"errorColor":"#cc0000",\
"strict":"warn","output":"htmlAndMathml","trust":false,"code":"%s"}' % pred.replace('\\', '\\\\'))
            webbrowser.open(url)
    return pred

def predict_tex():
    args = {'checkpoint': 'checkpoints/weights.pth', 'config': 'settings/config.yaml', 'file': '.\\temp.png', 'katex': False, 'no_cuda': False, 'no_resize': False, 'show': False, 'temperature': 0.333}

    args, *objs = initialize(args)
    
    try:
        pred = call_model(args, *objs)
        return pred
    except: 
        return 'Images not recognized'


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Use model', add_help=False)
    parser.add_argument('-t', '--temperature', type=float, default=.333, help='Softmax sampling frequency')
    parser.add_argument('-c', '--config', type=str, default='settings/config.yaml')
    parser.add_argument('-m', '--checkpoint', type=str, default='checkpoints/weights.pth')
    parser.add_argument('-s', '--show', action='store_true', help='Show the rendered predicted latex code')
    parser.add_argument('-f', '--file', type=str, default=None, help='Predict LaTeX code from image file instead of clipboard')
    parser.add_argument('-k', '--katex', action='store_true', help='Render the latex code in the browser')
    parser.add_argument('--no-cuda', action='store_true', help='Compute on CPU')
    parser.add_argument('--no-resize', action='store_true', help='Resize the image beforehand')
    args = parser.parse_args()
    logging.getLogger().setLevel(logging.FATAL)
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    latexocr_path = os.path.dirname(sys.argv[0])
    if latexocr_path != '':
        sys.path.insert(0, latexocr_path)
        os.chdir(latexocr_path)

    args, *objs = initialize(args)
    while True:
        instructions = input('Predict LaTeX code for image ("?"/"h" for help). ')
        possible_file = instructions.strip()
        ins = possible_file.lower()
        if ins == 'x':
            break
        elif ins in ['?', 'h', 'help']:
            print('''pix2tex help:

Usage:
    On Windows and macOS you can copy the image into memory and just press ENTER to get a prediction.
    Alternatively you can paste the image file path here and submit.

    You might get a different prediction every time you submit the same image. If the result you got was close you
    can just predict the same image by pressing ENTER again. If that still does not work you can change the temperature
    or you have to take another picture with another resolution (e.g. zoom out and take a screenshot with lower resolution). 

    Press "x" to close the program.
    You can interrupt the model if it takes too long by pressing Ctrl+C.

Visualization:
    You can either render the code into a png using XeLaTeX (see README) to get an image file back.
    This is slow and requires a working installation of XeLaTeX. To activate type 'show' or set the flag --show
    Alternatively you can render the expression in the browser using katex.org. Type 'katex' or set --katex

Settings:
    to toggle one of these settings: 'show', 'katex', 'no_resize' just type it into the console
    Change the temperature (default=0.333) type: "t=0.XX" to set a new temperature.
                ''')
            continue
        elif ins in ['show', 'katex', 'no_resize']:
            setattr(args, ins, not getattr(args, ins, False))
            print('set %s to %s' % (ins, getattr(args, ins)))
            continue
        elif os.path.isfile(possible_file):
            args.file = possible_file
        else:
            t = re.match(r't=([\.\d]+)', ins)
            if t is not None:
                t = t.groups()[0]
                args.temperature = float(t)+1e-8
                print('new temperature: T=%.3f' % args.temperature)
                continue
        try:
            print(args)
            call_model(args, *objs)
        except KeyboardInterrupt:
            pass
        args.file = None
