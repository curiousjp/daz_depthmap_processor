# Structuring Stable Diffusion output with Daz3D, ControlNet and Regional Prompting

This file discusses a workflow (with some variations) for taking scenes posed in Daz3D and "rendering" them in the A1111 Stable Diffusion front-end. The goal for the process is to compensate for the general lack of emphasis on composition in the training of Stable Diffusion merges.

The workflow has several steps and variations. I will demonstrate them with three examples.

## Example one - the absolute basics
### Step one - posing
Prerequisites:
* Daz studio and the Genesis 8 essentials library.
* A working A1111 installation and basic understanding of how to use it.
* The ControlNet extension installed, along with models for depth, normals, and pose data. A preprocessor for pose data is also required.
* Comfort running Python programs from the command line if you'll be using daz_depthmap_processor.


Here, I have posed a simple scene with a character and prop, and some minor background geometry to serve as a backstop and prevent any pinholing along the edges of our depth map. We are going to draw a picture of a magician conjuring with an orb of energy.

![image](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/6f700052-54a0-4427-aef8-57003bfe1a43)

Once I have the scene set up, I render my image and produce a depth map and a normal map for it. To do this, set your rendering engine to NVIDIA Iray, and in the Render Settings pane, go to the Advanced tab, you then the tab marked "Canvases". Turn canvases on, and create three of them. Set their types to "Beauty", "Depth" and "Normal". I tend to render quite large - if you start with a large render you can always resize it later to make it smaller, but if you go the other way, you will always lose detail.

As an alternative to creating a depth map using the canvas system, there is a commercial product that generates depth maps from Daz scenes. You can buy it on the Daz store [here](https://www.daz3d.com/basic-depth-map-maker-for-daz-studio). This would allow you to skip over the next step. As a second alternative, you can create your depth map using the canvas system, but process your depth map using Photoshop instead of daz_depthmap_processor. You can find tutorials on how to do this online.

### Step two - processing the depth map with daz_depthmap_processor
In our render output folder, we will have a subfolder holding the canvases, and in there, a file with a name like "simple_example-Canvas2-Depth.exr". Before you can use this file with ControlNet, you need to convert it to a greyscale depth map. Because a greyscale depth map only holds 256 levels of colour, we have to "quantise" our original and lose some detail in the process.

If you keep your render library and daz_depthmap_processor far away from one another, you may wish to copy the render and the exr files to the same folder as daz_depthmap_processor. I'll do this, and then run daz_depthmap_processor and request a depth histogram of the image to get a sense of what the data looks like.
```
$ python format_depthmap.py  --depth_cutoff histo simple_example-Canvas2-Depth.exr
** providing cutting histogram advice, but leaving depthmap unchanged
** - 00 - 07.76% - 177.35 to 198.89
** - 01 - 15.21% - 198.89 to 220.42
** - 02 - 00.10% - 220.42 to 241.95
** - 03 - 00.05% - 241.95 to 263.49
** - 04 - 00.04% - 263.49 to 285.02
** - 05 - 00.03% - 285.02 to 306.56
** - 06 - 00.03% - 306.56 to 328.09
** - 07 - 00.03% - 328.09 to 349.62
** - 08 - 00.03% - 349.62 to 371.16
** - 09 - 00.03% - 371.16 to 392.69
** - 10 - 00.03% - 392.69 to 414.23
** - 11 - 00.03% - 414.23 to 435.76
** - 12 - 00.02% - 435.76 to 457.29
** - 13 - 00.03% - 457.29 to 478.83
** - 14 - 00.03% - 478.83 to 500.36
** - 15 - 00.04% - 500.36 to 521.9
** - 16 - 00.04% - 521.9 to 543.43
** - 17 - 00.05% - 543.43 to 564.96
** - 18 - 00.07% - 564.96 to 586.5
** - 19 - 76.35% - 586.5 to 608.03
mapping status was: Success
```
We can see here that the bulk of the pixels are in the 586.5 to 608.03 range, which will be the backstop plane, but that there's also a large dropoff in pixel count after 220.42. This is likely to be the deepest element of the foreground character. To make sure we preserve the greatest number of grey levels available for our character during quantisation, we will truncate the depth map at around this point, and set everything after it to black.
```
$ python format_depthmap.py --depth_cutoff 220.42 simple_example-Canvas2-Depth.exr
mapping status was: Success
```
After each run of the program, it has written out a depthmap for us as "simple_example-Canvas2-Depth.depth.png". Feel free to rename it.
### Step three - converting the normal map
The normal map can be converted with any image processing tool that can read EXR - Gimp and Photoshop can both do the job. However, from the command line, ImageMagick's `convert` also works well: `convert simple_example-Canvas3-Normal.exr simple_example.normal.png`.

### Step four - generating the pose data, setting up our ControlNets, and rendering a result
From here, things are fairly straightforward. In ControlNet, generate pose data from the rendered image (I suggest using dw_openpose_full for this), and then do any required clean-up in the internal editor. I find it useful to save the generated pose information (from ControlNet's download image button) once you're happy with it.

At this point, the products we have in our workflow include these four images - I have resized these, but each would normally be the same size as our render, 1200x1200.

![montage-small](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/0857ac94-12d0-4d6e-9b56-3420dafa5310)

Load each of the pose, depth, and normal images into a relevant ControlNet unit, with the appropriate model - I use control_v11p_sd15_openpose, t2iadapter_depth_sd14v1, and control_v11p_sd15_normalbae respectively. If you only have two ControlNet units available you may need to enable a third in your A1111 settings screen. 

For each ControlNet unit, I start with a control weight of 0.3 and an ending control step of 0.5, with a 'balanced' control mode and tweak from there. Higher strength or a later end-step will make your generation more conformant, but unless you modeled background geometry in step one, this will eventually lead to your characters appearing in front of a featureless flat sheet.

This is also the time to fill in your prompt and try out some generations. You can also consider whether to use Hires Fix or ADetailer - if you bring the renders out at a fairly high resolution (with a lot of face pixels) and with the relevant parts of the depth map being well defined, this may not be necessary.

In this case, after a bit of tweaking, these were some of the results I produced:

![result-montage](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/f765f389-dc76-4c4d-bbc5-891fe0216e0c)

## Example two - manipulating the depth map and using regional prompting
Prerequisites:
* As above, plus.
* An image editor, such as Gimp.
* The sd-webui-regional-prompter add-on installed in A1111.

As discussed above, one downside of the ControlNet depthmap models is that they seem to have been conditioned on 256 level greyscale depthmaps, so compared to the depthmap formats like OpenEXR (which use floating point numbers), there is some loss of precision. As we saw above, daz_depthmap_processor can work out the range of available depths in an image, truncate them if necessary, and then divide what's left into 256 equal slices, but there will be times where we want to focus that addressable depth into particular areas of the picture that are most important, like faces or hands.

In this example, we will model a person looking into a magic mirror that shows them as they might be in another world. Because Daz doesn't have a way to represent "portals" or mirrors with geometry that will be captured in the depth map, we have composed our scene with an individual at a desk, some simple geometry to represent the mirror frame, and a mirrored copy of the first figure to be the reflection. After positioning the camera, these elements were moved around until they felt "right", and the mirrored figure was adjusted slightly to look at the camera.

![image](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/e1c25f9d-ef0b-408d-b267-b69f6baef80e)

This example picks up at the point where we start to manipulate the depth map to hide some geometry in the scene - the elbow and hand that pokes out around the "edge" of the mirror. For this example, we won't be using a normal map, because it would be too difficult to modify in the way we want.

### Processing the depth map, interactively
daz_depthmap_processor has an interactive mode for adjusting how it quantises the EXR depthmap. The interactive mode works by inserting "splits" into the full range of depth values, resizing those splits, and assigning them a share of the available 256 depth levels. Splits have a start and end depth, and "contain" pixels with a depth greater than or equal to their start value and less than their end value. (There are some small exceptions to do with the very end of range when drawing a histogram of a split's content.)

In this case, I am going to create five splits in our depth map. 
* The first one will contain the first individual, "A", the one looking into the mirror. They will receive a large share of levels.
* The second will contain the area of the desk between the person and the mirror. It will only receive a few depth levels.
* The third will contain the mirror frame. It will get a moderate number of depth levels.
* The fourth will contain the other person, "B", looking out from the mirror. They will also receive a large share of levels.
* The fifth and final split will contain the background. It will get whatever levels are left over.

Unlike a proper 3D model, the splits aren't limited to specific objects in the scene - if part of the desk overlaps (deskwise) with a high resolution object like "A", it will also be mapped in high resolution. Generally this doesn't seem to cause any problems. To use interactive mode, I start daz_depthmap_processor like this:
```
$ python format_depthmap.py --interactive mirrors-Canvas2-Depth.exr
Welcome to the interactive shell. Type help or ? to list commands.
>
```
The first thing I want to do is create a split, but before I can do that I need to get a sense of the existing values in the file. I can do this with the `show_splits` command.
```
> show_splits
 ** 000: 93.46874237060547 to 281.48592163085937 - 256 levels assigned (label: Default)
>
```
I'll try creating a split at 100, and see if the 93.4 to 100 split captures the first individual. I can test it by assigning that split a testing colour with `flag`, and then using the `test` command to write out a test picture. You can use normal CSS colour names for this flag.
```
> add 100
Success
> show_splits
 ** 000: 93.46874237060547 to 100.0 - 256 levels assigned (label: Default)
 ** 001: 100.0 to 281.48592163085937 - 0 levels assigned (No Flags)
> flag 0 test red
000: test = red
> test
mapping status was: Success
```
A new file is created alongside my depthmap, called mirrors-Canvas2-Depth.test.png. It looks like this (resized):

![testsmall](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/570dbe24-9073-41c6-ba9a-139115f4b203)

It seems like our new red split isn't pushing far enough into the map, so I'm going to use the "move" command to shift its endpoint. (Move can only be used on a depth corresponding to the start or end of a split, and there are a number of restrictions on what can be moved and where - e.g. you can't move the end of a split past the end of the depth map, or past the end of the next split - there are commands for removing, or effectively merging, splits.)
```
> move 100 120
Success
> test
mapping status was: Success
```
This looks better, but still not quite right. I add some more splits and keep tweaking them to get this:

![testsmall](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/fb2146b8-679b-4a4d-ae54-932167f5cdf5)

After some more time spent moving the starts and ends of the splits, I get something I'm happy with:
```
> show_splits
 ** 000: 93.46874237060547 to 132.0 - 256 levels assigned (label: Default, test: red, offset: 0)
 ** 001: 132.0 to 153.8 - 0 levels assigned (offset: 256, test: blue)
 ** 002: 153.8 to 170.0 - 0 levels assigned (test: green, offset: 256)
 ** 003: 170.0 to 210.0 - 0 levels assigned (test: yellow, offset: 256)
 ** 004: 210.0 to 281.48592163085937 - 0 levels assigned (test: cyan, offset: 256)
```
![test-multi-small](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/600dd156-ef9f-4b04-9d72-17d5baf35557)

Now it's time to allocate the grey levels to each split and write my depth map:
```
> allocate 0 90
90 levels allocated.
> allocate 1 4
94 levels allocated.
> allocate 2 60
154 levels allocated.
> allocate 3 90
244 levels allocated.
> allocate 4 12
256 levels allocated.
> show_splits
 ** 000: 93.46874237060547 to 132.0 - 90 levels assigned (label: Default, test: red, offset: 0)
 ** 001: 132.0 to 153.8 - 4 levels assigned (offset: 256, test: blue)
 ** 002: 153.8 to 170.0 - 60 levels assigned (test: green, offset: 256)
 ** 003: 170.0 to 210.0 - 90 levels assigned (test: yellow, offset: 256)
 ** 004: 210.0 to 281.48592163085937 - 12 levels assigned (test: cyan, offset: 256)
> write
mapping status was: Success
```
### Manipulating the depth map
Next, I open the depth map in [Gimp](https://www.gimp.org/), although any modern image editor with layer support should work. I convert the image to RGB colour, and begin to make some changes. The first thing I want to do is overpaint the areas where the reflection in the mirror 'sticks out' from its edges to match the background colour behind them.

The main trick when working with depth maps is to use the Fuzzy Select Tool (aka the "Magic Wand") with a threshold of zero, allowing you to grab all the connected pixels at the same depth. In Gimp, you can click and drag left and right to expand or contract the threshold as you select, allowing you to conveniently grab large areas of connected geometry. Once you have the area you want selected, switch to or create another layer and then use the Bucket Fill tool in its "fill entire selection" mode to hard colour your selection. Once I'd finished cleaning up, my revised depth map looked like this:

![tampered-montage](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/1d16e7d1-9676-4d5b-9052-1b394c836c08)
### Painting the region masks
I now want to use colours to mask out all the separate "entities" in the image. Each area I separate in this way can receive its own prompt in the final generation.

This is mostly done using the Fuzzy Select and Bucket tools as described above, dropping each area onto its own layer, painting it in with solid colour, and adding or removing paint until it looks right. The colours you use here matter, because the addon we'll be using, [sd-webui-regional-prompter](https://github.com/hako-mikan/sd-webui-regional-prompter) uses colour to match each point in the map with the appropriate prompt. The relationship between prompt numbers and colours is described in the sd-webui-regional-prompter help, but looks like this:

|Prompt #|Hue|Saturation|Value|
|--------|---|----------|-----|
|0|0|50%|50%|
|1|180|50%|50%|
|2|90|50%|50%|
|3|270|50%|50%|
|4|45|50%|50%|
|5|135|50%|50%|
|6|225|50%|50%|
|7|315|50%|50%|
|8|22.5|50%|50%|
|9|_etc_|_etc_|_etc_|

Once I have the basics of the layers set up, I will generally go through them, expand each one by a one pixel radius, and re-fill it to avoid 'seams' between the layers. Then I stack them in the correct order, with the nearest layers being at the top. Once I had finished, they looked like this:

![tampered-region-small](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/9682f34c-84cd-4297-be1f-f0f15e4f9688)
### Prompting
This time, I only run two ControlNet units - one each for pose and depth. Depth is set up like normal using our modified depth map, but in this case, Pose needed a lot of manual work as it couldn't make sense of the nearest figure. I also modified the pose to ignore the hands and right forearm of the figure in the mirror.

Once that was done, I turn on Regional Prompting, and set the mode to "Mask". You'll want to then drag and drop your image showing the combined regions to the area at the bottom right marked "Upload mask here cus gradio". You can test your mask is using the right colours by setting the region slider to 0, and then clicking "Draw region + show mask" button, which will show you the addon's interpretation of what is in each region, and then advance the slider to the next region. Set the resolution to match your generation size, and then I recommend setting your other options to base ratio: 0.2, and "use base prompt". Which generation mode you use is mostly to do with LORA compatibility, which is too complex to discuss here - see the addon's [documentation](https://github.com/hako-mikan/sd-webui-regional-prompter) for more details. In short, however, you may get faster results using attention than latent, and you may want to stick to using embeddings rather than LORA.

Now you can start trying various prompts out. Use BREAK to separate the prompt for each region, and remember that your first prompt will be the "base" prompt that is applied to each area at the "base ratio" strength.
```
a perfect anime illustration, beautiful, masterpiece, best quality, extremely detailed face, perfect lighting,
BREAK
1girl, brown hair, t-shirt, casual, facing away, updo, looking at mirror, (hands:-1)
BREAK
(white desk, desk:1.3), paperwork, calculator, pen, folder, clutter, photo \(object\),
BREAK
mirror, frame
BREAK
1girl, (witch), cloak, earrings, brown hair, short hair, looking at another, green eyes, bright, saturated colors, (modest), (cleavage, cleavage cutout:-0.5)
BREAK
(style-sylvamagic, starry sky, moon, plants, castle, fantasy),
BREAK,
(style-sylvamagic, starry sky, moon, plants, castle, fantasy),
BREAK
(apartment, large room, carpet, cozy, spacious, painting, furniture, television, window),
```
![results-two-montage](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/e435ab16-4f9f-498f-af1c-133d0a90ca37)
## Example three - automatic regional masking
If all the entities in your render are well separated in terms of depth from one another, you can actually get daz_depthmap_processor to draw the region mask for you. In this scene, we have a subject in the foreground on a flat plane, some ruins geometry behind him, and then in the far background a backstop plane. 

![image](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/3ebf1976-716f-4121-bf82-bb01ceb35acb)

Starting the daz_depth_processor with `--region` and then providing integer region numbers in the "region" flag for splits will result in an additional ".regions.png" file being written alongside the depth map:
```
$ python format_depthmap.py --interactive --region ruin_scene-Canvas2-Depth.exr
Welcome to the interactive shell. Type help or ? to list commands.
> histogram
** - 00 - 20.31% - 355.43 to 458.92
** - 01 - 36.53% - 458.92 to 562.41
** - 02 - 04.65% - 562.41 to 665.9
** - 03 - 03.60% - 665.9 to 769.39
** - 04 - 02.37% - 769.39 to 872.88
** - 05 - 01.18% - 872.88 to 976.37
** - 06 - 01.03% - 976.37 to 1079.86
** - 07 - 02.36% - 1079.86 to 1183.35
** - 08 - 01.99% - 1183.35 to 1286.83
** - 09 - 01.21% - 1286.83 to 1390.32
** - 10 - 04.02% - 1390.32 to 1493.81
** - 11 - 00.40% - 1493.81 to 1597.3
** - 12 - 00.80% - 1597.3 to 1700.79
** - 13 - 00.63% - 1700.79 to 1804.28
** - 14 - 01.12% - 1804.28 to 1907.77
** - 15 - 03.68% - 1907.77 to 2011.26
** - 16 - 00.53% - 2011.26 to 2114.75
** - 17 - 01.02% - 2114.75 to 2218.23
** - 18 - 03.24% - 2218.23 to 2321.72
** - 19 - 09.33% - 2321.72 to 2425.21
> add 2321.72
Success
> add 562.41
Success
> show_splits
 ** 000: 355.4339904785156 to 562.41 - 256 levels assigned (label: Default)
 ** 001: 562.41 to 2321.72 - 0 levels assigned (No Flags)
 ** 002: 2321.72 to 2425.221669921875 - 0 levels assigned (No Flags)
> flag 0 test red
000: test = red
> flag 1 test green
001: test = green
> flag 2 test blue
002: test = blue
> test
mapping status was: Success
> move 562.41 355.43
Error - will not move the start of split 1 past the beginning of split 0 - are you trying to delete a split?
> move 562.41 458.92
Success
> test
mapping status was: Success
> move 458.92 450
Success
> test
mapping status was: Success
> show_splits
 ** 000: 355.4339904785156 to 450.0 - 256 levels assigned (label: Default, test: red, offset: 0)
 ** 001: 450.0 to 2321.72 - 0 levels assigned (test: green, offset: 256)
 ** 002: 2321.72 to 2425.221669921875 - 0 levels assigned (test: blue, offset: 256)
> allocate 0 220
220 levels allocated.
> allocate 1 30
250 levels allocated.
> allocate 2 6
256 levels allocated.
> flag 0 region 0
000: region = 0
> flag 1 region 1
001: region = 1
> flag 2 region 2
002: region = 2
> show_splits
 ** 000: 355.4339904785156 to 450.0 - 220 levels assigned (label: Default, test: red, offset: 0, region: 0)
 ** 001: 450.0 to 2321.72 - 30 levels assigned (test: green, offset: 256, region: 1)
 ** 002: 2321.72 to 2425.221669921875 - 6 levels assigned (test: blue, offset: 256, region: 2)
> write
mapping status was: Success
```
The resulting depth and region maps look like this:

![ruin-montage](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/dc65b3b7-cadf-4749-9119-0b8e1225a335)

And as an example, some quick generations from these (alongside the normal map and pose data):

![output-montage](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/86e1f89e-8fac-4ced-9e1c-836282587e85)
