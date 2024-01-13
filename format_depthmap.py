import argparse
import array
import os
import random
import cmd

import Imath
import OpenEXR
from PIL import Image, ImageColor

from splitter_classes import SplitManager, MAX_SPLIT_LEVELS

FLOAT_PIXELTYPE = Imath.PixelType(Imath.PixelType.FLOAT)
HSV_BLACK = ImageColor.getrgb('hsv(0,0%,0%)')

def generate_hsv_sequence(steps = 360):
    hue_step = 180.0
    hues = []
    current_hue = 0.0
    for i in range(steps):
        hues.append(current_hue)
        # attempt to find another hue
        next_hue = current_hue
        while True:
            next_hue += hue_step
            if next_hue >= 360.0:
                hue_step /= 2.0
                next_hue = 0.0
            if next_hue not in hues:
                break
        current_hue = next_hue
    return [ImageColor.getrgb(f'hsv({h},50%,50%)') for h in hues]

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
        if args.interactive:
            process_interactive(args, filename, exr_dimensions, exr_array)
        else:
            process_automatic(args, filename, exr_dimensions, exr_array)

def make_histogram(exr_array, resolution = 0.05):
        slices = int(1.0/resolution)
        values = len(exr_array)
        min_d = min(exr_array)
        max_d = max(exr_array)
        step = (max_d - min_d)/slices
        results = []
        for i in range(slices):
            step_from = min_d + (i * step)
            step_to = min_d + ((i+1) * step) 
            if i == (slices - 1):
                matching = sum([1 for depth in exr_array if depth >= step_from and depth <= step_to])
            else:
                matching = sum([1 for depth in exr_array if depth >= step_from and depth < step_to])
            share = matching / values * 100.0
            results.append(f'** - {i:02} - {share:05.2f}% - {round(step_from,2)} to {round(step_to,2)}')
        return results

class DepthShell(cmd.Cmd):
    intro = 'Welcome to the interactive shell. Type help or ? to list commands.'
    prompt = '> '

    def prime(self, args, filename, exr_dimensions, exr_array):
        self._args = args
        self._filename = filename
        self._dimensions = exr_dimensions
        self._points = exr_array
        self._sm = SplitManager(min(self._points), max(self._points))

        if args.depth_cutoff not in ['histo', None]:
            cutoff_point = float(args.depth_cutoff)
            self._sm.addSplit(cutoff_point)
            self.do_rename('1 Cutoff')
        elif args.depth_cutoff == 'histo':
            self.do_histogram(None)

    def do_histogram(self, args):
        'Show the histogram of the loaded depthmap. HISTOGRAM'
        for line in make_histogram(self._points):
            print(line)

    def do_show_splits(self, args = None):
        'Show the current splits. SHOW_SPLITS'
        for index in range(self._sm.countSplits()):
            result, info = self._sm.information(index, self._points)
            if info == None:
                print(result)
                continue
            line = f" ** {index:03}: {info['start']} to {info['end']} - {info['levels']} levels assigned"
            message, flags = self._sm.getFlags(index)
            if flags:
                fdict = {k: self._sm.getFlag(index, k)[1] for k in flags}
                line += ' (' + ', '.join([f'{k}: {v}' for k,v in fdict.items()]) + ')'
            elif flags == []:
                line += ' (No Flags)'
            else:
                line += f'\n{message}'
            
            print(line)

    def do_allocate(self, args):
        'Allocate slices of the greymap to splits. ALLOCATE {index} {levels}'
        pieces = [int(x) for x in args.split(' ')]
        if len(pieces) == 2:
            result, valid = self._sm.allocateLevels(pieces[0], pieces[1])
            print(result)
        else:
            print('Error - ALLOCATE {index} {levels}')

    def do_compress(self, args):
        'Synonym for COMPRESSION'
        self.do_compression(args)
    def do_compression(self, args):
        'Toggle depthmap compression on or off. COMPRESSION'
        self._args.compress_map = not self._args.compress_map
        print(f'Map compression toggled, now: {self._args.compress_map}.')

    def do_totals(self, args):
        'Show the total number of grey levels that have been allocated.'
        message, valid = self._sm.totalLevels()
        print(message)
        if valid:
            print(f'Does not exceed maximum allocable levels, {MAX_SPLIT_LEVELS}.')
        else:
            print(f'Exceeds maximum allocable levels, {MAX_SPLIT_LEVELS}.')

    def do_flag(self, args):
        'Set or retrieve a flag on a split. FLAG {index} {flag} {value} or FLAG {index} {flag} or FLAG {index}'
        pieces = args.split(' ')
        index = int(pieces[0])
        if len(pieces) == 1:
            flags = self._sm.getFlags(index)[1]
            line = f' ** {index:03}: '
            if flags:
                line += ', '.join([f'{k}: {self._sm.getFlag(index, k)[1]}' for k in flags])
            else:
                line += 'no flags'
            print(line)
        elif len(pieces) == 2:
            result, value = self._sm.getFlag(index, pieces[1])
            if value == None:
                print(result)
            print(f'{index:03}: {pieces[1]} = {value}')
        elif len(pieces) == 3:
            self._sm.setFlag(index, pieces[1], pieces[2])
            self.do_flag(f'{index} {pieces[1]}')
        else:
            print('Error - FLAG {index} {flag} {value} or FLAG {index} {flag} or FLAG {index}')

    def do_clearflag(self, args):
        'Remove a flag from a split. CLEARFLAG {index} {flag}'
        pieces = args.split(' ')
        index = int(pieces[0])
        if len(pieces) == 2:
            result, value = self._sm.clearFlag(index, pieces[1])
            print(result)
        else:
            print('Error - CLEARFLAG {index} {flag}')

    def do_rename(self, args):
        'Rename splits for ease of referencing. Shorthand for FLAG {index} LABEL {name}. RENAME {index} {name}'
        pieces = args.split(' ')
        self.do_flag(f'{pieces[0]} LABEL {pieces[1]}')
    
    def do_region(self, args):
        'Allocate a split to a region. -1 is omitted. Shorthand for FLAG {index} REGION {region #}. REGION {index} {region #}'
        pieces = args.split(' ')
        self.do_flag(f'{pieces[0]} REGION {pieces[1]}')
   
    def do_split(self, args):
        'Synonym for ADD.'
        self.do_add(args)
    def do_add(self, args):
        'Add a split at a specified depth. ADD {depth}'
        insertion_point = float(args)
        if insertion_point < min(self._points):
            insertion_point = min(self._points) + 0.01
        if insertion_point > max(self._points):
            insertion_point = max(self._points) - 0.01
        message, newSplit = self._sm.addSplit(insertion_point)
        print(message)

    def do_move(self, args):
        'Move the start or endpoint of a split, with various restrictions. MOVE {from} {to}'
        pieces = [float(x) for x in args.split(' ')]
        if len(pieces) != 2:
            print('Error - MOVE {from} {to}')
        message, result = self._sm.moveSplit(pieces[0], pieces[1])
        print(message)

    def do_merge(self, args):
        'Synonym for REMOVE.'
        self.do_remove(args)
    def do_remove(self, args):
        'Remove a specified split. REMOVE {index}'
        removal_index = int(args)
        message, result = self._sm.removeSplit(removal_index)
        print(message)
   
    def do_getpixel(self, args):
        'Get the depth of a particular x y pixel in the depthmap. GET {x} {y}'
        pieces = [int(x) for x in args.split(' ')]
        offset = pieces[1] * self._dimensions[0] + pieces[0]
        print(f'Value at {pieces[0]}:{pieces[1]} (offset {offset}): {self._points[offset]}')

    def do_inspect(self, args):
        'Get information on a particular slice. INSPECT {index}'
        inspect_index = int(args)
        message, information = self._sm.information(inspect_index, self._points)
        if information == None:
            print(message)
        else:
            print(f'Split {inspect_index:03}:')
            for k,v in information.items():
                if k == 'points':
                    continue
                print(f' - {k}: {v}')           
            print('Histogram:')
            histo = make_histogram(information['points'])
            for line in histo:
                print(f' - {line}')

    def do_test(self, args):
        'Write a test map. Splits will be colored according to their TEST tag. TEST {filename} or just TEST'
        if args == '':
            args = self._filename
        write_file(self._args, args, self._dimensions, self._points, self._sm, test = True)

    def do_write(self, args):
        'Write a depthmap to disk. WRITE {filename} or just WRITE'
        if args == '':
            args = self._filename
        write_file(self._args, args, self._dimensions, self._points, self._sm)

    def do_exit(self, args):
        'Synonym for QUIT'
        return self.do_quit(args)
    def do_quit(self, args):
        'Exit the current file WITHOUT WRITING. QUIT'
        return True

def process_interactive(args, filename, exr_dimensions, exr_array):
    shell = DepthShell()
    shell.prime(args, filename, exr_dimensions, exr_array)
    shell.cmdloop()

def process_automatic(args, filename, exr_dimensions, exr_array):
    if args.depth_cutoff == None:
        depth_cutoff = None
    elif args.depth_cutoff == 'histo':
        print('** providing cutting histogram advice, but leaving depthmap unchanged')
        for line in make_histogram(exr_array):
            print(line)
        depth_cutoff = None
    else:
        depth_cutoff = float(args.depth_cutoff)
    if depth_cutoff:
        exr_array = [min(y, depth_cutoff) for y in exr_array]
    split_manager = SplitManager(min(exr_array), max(exr_array))
    write_file(args, filename, exr_dimensions, exr_array, split_manager)

def write_file(args, filename, dimensions, points, splitmanager, test = False):
    filename_stub = os.path.splitext(filename)[0]

    # map the points with the provided splitmanager
    mapping_results, mapping = splitmanager.makeMapping(points, args.compress_map)
    print(f'mapping status was: {mapping_results}')
    if(mapping_results != 'Success'):
        print('as the mapping process was unsuccessful, no files will be written')
        print('(did you allocate too many levels?)')
        return
    
    mapped = [mapping.get(y, MAX_SPLIT_LEVELS - 1) for y in points]

    # recolour the map using the TEST tag on the relevant splits
    if test:
        # invert and turn to rgb
        debug_pixels = [(255 - y) for y in mapped]
        debug_pixels = [(x,x,x) for x in debug_pixels]
        for index in range(len(points)):
            depth = points[index]
            message, owner = splitmanager.findSplitForDepth(depth)
            if owner != None:
                debug_colour = owner.getFlag('TEST', None)
                if debug_colour:
                    debug_pixels[index] = ImageColor.getrgb(debug_colour)
            else:
                print(message)
        debug_file = Image.new('RGB', dimensions)
        debug_file.putdata(debug_pixels)
        debug_file.save(f'{filename_stub}.test.png')
        # early exit
        return

    if args.regions:
        # invert and turn to rgb
        region_pixels = [(255 - y) for y in mapped]
        region_pixels = [(x,x,x) for x in region_pixels]
        regions = []
        for index in range(len(points)):
            depth = points[index]
            message, owner = splitmanager.findSplitForDepth(depth)
            if owner != None:
                region = int(owner.getFlag('REGION', -1))
                regions.append(region)
            else:
                print(message)
                regions.append(-1)
        
        if max(regions) > -1:
            hsv_values = generate_hsv_sequence(max(regions) + 1)
            for index in range(len(points)):
                region = regions[index]
                if region == -1 or region >= len(hsv_values):
                    continue
                region_pixels[index] = hsv_values[region]
        
        region_file = Image.new('RGB', dimensions)
        region_file.putdata(region_pixels)
        region_file.save(f'{filename_stub}.regions.png')

    if args.mask:
        maximal = max(mapped)
        mask = [0 if x == maximal else 255 for x in mapped]
        output_mask = Image.new('L', dimensions)
        output_mask.putdata(mask)
        output_mask.save(f'{filename_stub}.mask.png')

    if args.noise:
        mapped = [y if y < 255 else 255 - random.randint(0,255) for y in mapped]

    # invert
    inverted = [(255 - y) for y in mapped]

    output_image = Image.new('L', dimensions)
    output_image.putdata(inverted)
    output_image.save(f'{filename_stub}.depth.png')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('exrfile', nargs = '+', type = lambda x: is_valid_file(parser, x))
    parser.add_argument('--depth_cutoff', type = str, default = None)
    parser.add_argument('--compress_map', default = False, action = 'store_true')
    parser.add_argument('--interactive', default = False, action = 'store_true')
    parser.add_argument('--regions', default = False, action = 'store_true')
    parser.add_argument('--noise', default = False, action = 'store_true')
    parser.add_argument('--mask', default = False, action = 'store_true')
    args = parser.parse_args()
    main(args)