# daz_depthmap_processor
Reprocesses depthmaps produced by Daz down to 256 colour greymaps for use in Controlnet-depth

## overview
Daz's iRay depth canvases are produced as OpenEXR maps, and if rendered with no backdrop geometry can show a pinholing effect around the edges of objects. I originally wrote this tool to do two things - convert EXR maps into quantised 256 colour pngs and to allow me to truncate those maps at a given depth. This way I could add a backing plane primitive to my scene to avoid pinholing without having to also lose fidelity to "empty depth" between it and my scene. Over time it has grown to include some additional features.

This tool runs from the command line, and takes any number of exr depthmaps as command line arguments. It can run in both interactive and non-interactive modes, although some features are only available in the interactive mode.

There is a tutorial, available at [example.md](example.md).

## using the tool
### non-interactively
```
$ python format_depthmap.py input.exr
```
Reads in input.exr, allocates 256 grey levels across the full observed range of depths in the file, and then writes it to input.depth.png. Some relevant options are:
* `--depth_cutoff <value>` which will rewrite any point beyond this depth as being at that 'maximum depth', in turn reducing the spread for allocating grey levels. This can be expressed either as a bare integer, a float, or in the usual Python forms of scientific notation like 1.5e+38. If you specify an argument of 'histo' to this, the program will print a summary of observed depth in your file, which may be useful in setting your cutoff point.  See below for more information.
* `--mask` which will write an additional png file representing a black/white mask of area of the image that isn't at the maximum depth.
* `--noise` which replaces areas of the map at the maximum depth with random noise (you usually won't want this).
* `--region` which enables production of region maps for use with hako-mikan's [sd-webui-regional-prompter](https://github.com/hako-mikan/sd-webui-regional-prompter) (see below).
* `--compress_map` which gets its own section below.
### interactively
```
$ python format_depthmap.py --interactive depth.exr
```
Interactive mode gives you a simple shell to work with. In interactive mode, you break apart the observed depths into chunks known as "splits", and then allocate each split a number of grey levels to use. Splits covering relatively small gamuts of depth can be given large numbers of grey levels, or vice versa, allowing you to allocate maximum discriminatory power to areas like faces and hands. Splits with no levels render their contents as being at the maximum distance.

When interactive mode starts, it defaults to creating one split covering the entire depth gamut and with all 256 depth levels allocated to it. If a cutoff was specified on the command line, this is used to create a first split, which has zero levels allocated.

Interactive is unfortunately not very easy to use, but you can gain some guidance from the [tutorial](example.md). You can type '?' to see a list of commands, but the main ones to keep in mind include:
* `add <at depth>` break apart an existing split at the specified depth. This does not allocate any depth levels to the new split.
* `allocate <index> <grey levels>` allocate a number of grey levels to the split at a given index. This does not stop you from allocating too many levels (in which case your attempts to write a depth map will fail!) but will let you know how many are allocated each time you use it (this information also available with `totals`).
* `clearflag <index> <flagname>` remove a flag from a split.
* `compression` toggle map compression on or off. `compress` is an alias.
* `flag <index> <flagname> <flagvalue>` set an arbitrary flag on a split. Flags show in `show_splits` and can affect the operation of other parts of the program.
* `flag <index>` show flags for a given split.
* `getpixel <x> <y>` get the depth value at x,y - can be useful for determining the depth boundaries of a face or other feature.
* `histogram` show the histogram of the current depth map.
* `inspect <index>` provides useful information on the split at a given index.
* `move <from depth> <to depth>` move a start or endpoint of a split to a new depth. The specified from depth can't be the start of the first split or end of the last split, and you can't move a point outside the map or beyond the boundaries of a neighbouring split.
* `quit` move on to the next file, or if no more exist, exit. `exit` is an alias.
* `region <index> <region id>` assign a region ID to a split for use with `--region`. Please use integers only. A wrapper for the `flag` command.
* `remove <index>` remove the split at a given index. If you remove the split at index 0, the split at index 1 will extend to encompass that area. Otherwise, the split at (index - 1) will be extended to encompass that area. Perhaps better understood as merging.
* `rename <index> <name>` give a name to a split for ease of reference in `show_splits`. An wrapper for the `flag` command.
* `show_splits` print the list of existing splits, including their indexes and start and end points.
* `test <filename>` writes out a test image with each split painted in a single colour. Won't do anything unless splits have been tagged using the `flag` command and a tag of `test` (e.g. `flag 0 test red`).
* `write <filename>` writes a depthmap out - like with the input filenames, '.depth.png' or '.mask.png' is appended to the specified filename. If you omit the filename, it will use the name of the input file.

## what is map compression?
Imagine you have an image that includes many pixels at each of the following depth values - 10, 200, 250, and 350. The value of 200 would normally be mapped to a grey level by determining how far through the range of 10 to 350 it falls - ~55.88% of the way or so - and multiplying this by the number of available grey levels, with the final result being 143. When map compression is used, a different approach is taken - instead, the 256 levels are evenly spread between the four different observed depth levels, so a depth of 10 becomes 0, 200 becomes 85, 250 becomes 170, and 350 becomes 255. This method breaks apart the relativities between different depths, but may let you squeeze more 'detail' out of your maps if you have large areas of unused 'depth' in your scene. Map compression is off by default.

## what does the histogram tell me?
```
$ python format_depthmap.py --depth_cutoff histo depth.exr
** providing cutting histogram advice, but leaving depthmap unchanged
** - 00 - 00.88% - 189.8212127685547
** - 01 - 01.02% - 201.18017807006837
** - 02 - 00.97% - 212.53914337158204
** - 03 - 00.78% - 223.8981086730957
** - 04 - 02.10% - 235.25707397460937
** - 05 - 05.03% - 246.61603927612305
** - 06 - 04.53% - 257.9750045776367
** - 07 - 00.82% - 269.3339698791504
** - 08 - 00.06% - 280.69293518066405
** - 09 - 00.05% - 292.05190048217776
** - 10 - 00.04% - 303.4108657836914
** - 11 - 00.04% - 314.76983108520506
** - 12 - 00.03% - 326.12879638671876
** - 13 - 00.04% - 337.48776168823247
** - 14 - 00.04% - 348.8467269897461
** - 15 - 00.04% - 360.20569229125977
** - 16 - 00.05% - 371.5646575927734
** - 17 - 00.06% - 382.9236228942871
** - 18 - 00.08% - 394.2825881958008
** - 19 - 83.13% - 405.6415534973145
```
The histogram slices up the observed depths from the exr file into 20 buckets, numbered 0 to 19. For each one, it calculates how many pixels in the image, and provides that information as a percentage. The number to the right of the percentage is the depth that this bucket starts from. In this case, where the image has a backplane, you can guess that this is what is causing the large number of pixels in the final bucket, starting from 405.64. However, you can also see that there is not much use of the depths after the bucket starting at 280.69 - so this would be a good choice for a cutting depth.

## region maps
The program can also generate a region map for use with [sd-webui-regional-prompter](https://github.com/hako-mikan/sd-webui-regional-prompter), by flagging individual spans as having specific region IDs. An example can be seen in the third section of the [tutorial](example.md).

## comparing with other solutions

3D Universe [publishes a script](https://www.daz3d.com/basic-depth-map-maker-for-daz-studio) for Daz that also generates very good depth maps - for most people who don't want to do fine tweaking of grey allocations, you are probably better off just buying and using their product. The following graphic shows a comparison between generations for a relatively challenging pose, all of which use the same pose data and normal map. All three controlnet units are configured at 30% weight, ending at control step 50%.

|Original iRay Render|DWPose data|Normal map|
|-|-|-|
|![posetest_no_backplane](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/6c82e183-c6c7-4005-993c-f38054ce58b2)|![posenet](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/44ef0655-bb53-4278-b172-4e15a4e7ada7)|![posetest-nobackplane-normals](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/af0f0535-41e7-4799-bf34-cb5f99f0abf6)|

|No Depth Map|Basic Depth Map Maker|This tool, with no cuts or zones specified|This tool, cutoff specified, compression enabled|This tool, manually-specified depth zones\*|
|-|-|-|-|-|
||![posetest_dmm_no_backplane](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/57d1b358-bfb6-46ce-85f2-4ca42ece9c94)|![naive depth](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/da707cd9-e022-44c9-ae75-3b5c12aba8b7)|![with_cutoff depth](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/17c99ddc-9b50-471b-85cd-17a9dbe992e4)|![balancer depth](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/06d800ff-6913-4b20-b3b8-44f46d5ef36d)|
|![no-map render](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/60e27d20-28d3-423f-a647-dd8a987b4893)|![dmm render](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/7e593e8a-8929-4e4b-8a64-f3f375749cd6)|![naive render](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/115389b1-39cb-4e9a-9b62-e7711e611697)|![cut-compress render](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/698a5e9e-0110-4e68-8824-e0feed43bcc8)|![balancer render](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/afe5c6a9-5291-4713-8ba2-2a96c7345d8e)|

As you can see, the DMM tool works pretty well with very little fiddling around required.

\* - In this case, a split from the minimum to 306 with 64 levels, from 306 to 317 with 64 levels (the face), from 317 to 319.9 with 32 levels, from 319.9 to 321 with 64 levels (the hand), from 321 to 370 with 32 levels, and then a final split to the end with no levels.
