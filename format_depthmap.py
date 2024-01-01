import argparse
import array
import os
import random
import cmd

import Imath
import OpenEXR
from PIL import Image

FLOAT_PIXELTYPE = Imath.PixelType(Imath.PixelType.FLOAT)

from splitter_classes import SplitManager, MAX_SPLIT_LEVELS

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

def make_histogram(exr_array):
        values = len(exr_array)
        min_d = min(exr_array)
        max_d = max(exr_array)
        step = (max_d - min_d)/20
        results = []
        for i in range(20):
            step_from = min_d + (i * step)
            vm = len([x for x in exr_array if x >= min_d + (i * step) and x < min_d + ((i+1) * step)])
            results.append(f'** - {i:02} - {vm/values*100:05.2f}% - {step_from}')
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

    def do_show_splits(self, args = None):
        'Show the current splits.'
        for line in self._sm.show():
            print(line)

    def do_histogram(self, args):
        'Show the histogram of the loaded depthmap.'
        for line in make_histogram(self._points):
            print(line)

    def do_allocate(self, args):
        'Allocate slices of the greymap to splits. ALLOCATE {index} {levels}'
        pieces = [int(x) for x in args.split(' ')]
        self._sm.allocateLevels(pieces[0], pieces[1])
        self.do_show_splits()

    def do_rename(self, args):
        'Rename splits for ease of referencing. RENAME {index} {name}'
        pieces = args.split(' ')
        self._sm.renameSplit(int(pieces[0]), pieces[1])
        self.do_show_splits()

    def do_totals(self, args):
        'Show the total number of grey levels available for allocation.'
        totals = self._sm.totalLevels()
        print(f'Total allocated levels: {totals}.')

    def do_add(self, args):
        'Add a split at a specified depth. ADD {depth}'
        insertion_point = float(args)
        if insertion_point < min(self._points):
            insertion_point = min(self._points)
        if insertion_point > max(self._points):
            insertion_point = max(self._points)
        self._sm.addSplit(insertion_point)
        self.do_show_splits()
    
    def do_getpixel(self, args):
        'Get the depth of a particular x y pixel in the depthmap. GET {x} {y}'
        pieces = [int(x) for x in args.split(' ')]
        offset = pieces[1] * self._dimensions[0] + pieces[0]
        print(f'Value at {pieces[0]}:{pieces[1]} (offset {offset}): {self._points[offset]}')

    def do_inspect(self, args):
        'Get information on a particular slice. INSPECT {index}'
        inspect_index = int(args)
        pc = self._sm.inspectSplit(inspect_index, self._points)
        print(f"Split at index {inspect_index}: {pc['start']} to {pc['finish']} ({pc['levels']})")
        print(f" points: {pc['count']}")
        print(f" max   : {pc['max']}")
        print(f" min   : {pc['min']}")
        print('histogram:')
        histo = make_histogram(pc['points'])
        for line in histo:
            print(line)

    def do_remove(self, args):
        'Remove a specified split. REMOVE {index}'
        removal_index = int(args)
        self._sm.removeSplit(removal_index)
        self.do_show_splits()

    def do_compression(self, args):
        'Toggle depthmap compression on or off.'
        self._args.compress_map = not self._args.compress_map
        print(f'Map compression toggled, now: {self._args.compress_map}.')

    def do_write(self, args):
        'Write a depthmap to disk. WRITE {filename} or just WRITE'
        if args == '':
            args = self._filename
        results, mapping = self._sm.makeMapping(self._points, self._args.compress_map)
        print(f'mapping status: {results}')
        mapped = [mapping.get(y, MAX_SPLIT_LEVELS - 1) for y in self._points]
        write_file(self._args, args, self._dimensions, mapped)

    def do_quit(self, args):
        'Exit the current file WITHOUT WRITING.'
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
    results, mapping = split_manager.makeMapping(exr_array, args.compress_map)
    print(f'mapping status: {results}')
    mapped = [mapping.get(y, MAX_SPLIT_LEVELS - 1) for y in exr_array]
    write_file(args, filename, exr_dimensions, mapped)

def write_file(args, filename, dimensions, mapped):
    filename_stub = os.path.splitext(filename)[0]
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
    parser.add_argument('--noise', default = False, action = 'store_true')
    parser.add_argument('--mask', default = False, action = 'store_true')
    args = parser.parse_args()
    main(args)