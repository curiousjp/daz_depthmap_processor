import argparse
import array
import os
import random
import sys

import Imath
import OpenEXR
from PIL import Image

FLOAT_PIXELTYPE = Imath.PixelType(Imath.PixelType.FLOAT)

# tool for processing exr canvases produced by the Daz renderer
# as a reminder, these can normally be found in 
#  C:\Users\<you>\Documents\DAZ 3D\Studio\Render Library\

def is_valid_file(p, a):
    if not os.path.exists(a):
        p.error(f'file {a} does not exist!')
    elif not a.endswith('.exr'):
        p.error(f'file {a} must end with .exr!')
    else:
        return a

def get_exr_data(fn):
    file_handle = OpenEXR.InputFile(fn)
    data_window = file_handle.header()['dataWindow']
    dimensions = (
        data_window.max.x - data_window.min.x + 1, 
        data_window.max.y - data_window.min.y + 1
    )
    depth_values = array.array('f', file_handle.channel('Y', FLOAT_PIXELTYPE)).tolist()
    return (dimensions, depth_values)

def main(args):
    for filename in args.exrfile:
        exr_dimensions, exr_array = get_exr_data(filename)
        
        if args.depth_cutoff == None:
            depth_cutoff = None
        elif args.depth_cutoff == 'histo':
            print('** providing cutting histogram advice, but leaving depthmap unchanged')
            values = exr_dimensions[0] * exr_dimensions[1]
            min_d = min(exr_array)
            max_d = max(exr_array)
            step = (max_d - min_d)/20
            for i in range(20):
                step_from = min_d + (i * step)
                vm = len([x for x in exr_array if x >= min_d + (i * step) and x < min_d + ((i+1) * step)])
                print(f'** - {i:02} - {vm/values*100:.2f}% - {step_from}')
            depth_cutoff = None
        else:
            depth_cutoff = float(args.depth_cutoff)
        if depth_cutoff:
            exr_array = [min(y, depth_cutoff) for y in exr_array]
        
        # we need to map the remaining depth values 
        if args.compress_map:
            y_values = sorted(list(set(exr_array)))
            y_value_count = len(y_values)
            print(f'** {y_value_count} distinct depth values found')
            if y_value_count < 255:
                mapped = [y_values.index(y) for y in exr_array]
            else:
                map_helper = {y_values[i]: int(i / (y_value_count-1) * 255) for i in range(y_value_count)}
                mapped = [map_helper[y] for y in exr_array]
        else:
            minimal = min(exr_array)
            maximal = max(exr_array)
            span = maximal - minimal
            mapped = [int((y - minimal) / span * 255.0) for y in exr_array]

        filename_stub = os.path.splitext(filename)[0]

        if args.mask:
            maximal = max(mapped)
            mask = [0 if x == maximal else 255 for x in mapped]
            output_mask = Image.new('L', exr_dimensions)
            output_mask.putdata(mask)
            output_mask.save(f'{filename_stub}.mask.png')

        if args.noise:
            mapped = [y if y < 255 else 255 - random.randint(0,255) for y in mapped]

        # invert
        inverted = [(255 - y) for y in mapped]

        output_image = Image.new('L', exr_dimensions)
        output_image.putdata(inverted)
        output_image.save(f'{filename_stub}.depth.png')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('exrfile', nargs = '+', type = lambda x: is_valid_file(parser, x))
    parser.add_argument('--depth_cutoff', type = str, default = None)
    parser.add_argument('--compress_map', default = False, action = 'store_true')
    parser.add_argument('--noise', default = False, action = 'store_true')
    parser.add_argument('--mask', default = False, action = 'store_true')
    args = parser.parse_args()
    main(args)