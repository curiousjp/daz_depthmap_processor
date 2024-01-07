# Structuring Stable Diffusion output with Daz3D, ControlNet and Regional Prompting

This post discusses a workflow (with some variations) for taking scenes posed in Daz3D and "rendering" them in the A1111 Stable Diffusion front-end. The goal for the process is to compensate for the general lack of emphasis on composition in the training of Stable Diffusion merges.

The workflow has several steps. I will demonstrate them with three examples of increasing complexity.

## Example one - the absolute basics
### Step one - posing
Here, I have posed a simple scene with a character and prop, and some minor background geometry to serve as a backstop and prevent any pinholing along the edges of our depth map. We are going to draw a picture of a magician conjuring with an orb of energy.

![image](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/6f700052-54a0-4427-aef8-57003bfe1a43)

Once I have the scene set up, I render my image and produce a depth map and a normal map for it. To do this, set your rendering engine to NVIDIA Iray, and in the Render Settings pane, under the Advanced tab, you can find a second tab marked "Canvases". Turn canvases on, and create three canvases. Set their types to "Beauty", "Depth" and "Normal". I tend to render quite large - you can resize your inputs to Stable Diffusion later if you render large, but you can't recover that detail later if you want to go the other way.

As an alternative to creating a depth map using the canvas system, there is a commercial product that generates depth maps from Daz scenes, which can be found [here](https://www.daz3d.com/basic-depth-map-maker-for-daz-studio). This will allow you to skip over the next step.

### Step two - processing the depth map
In our output folder, we will have a canvas folder and a file with a name like "simple_example-Canvas2-Depth.exr". You can copy this to wherever you've put the script files for daz_depthmap_processor. Note - you can also reprocess the depth map in Photoshop, tutorials for which are available online.

In this case, I'll run the processor and request a depth histogram of the image.
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

We can see here that the bulk of the pixels are in the 586.5 to 608.03 range, which will include the backstop plane, but that there's also a large dropoff in pixel count after 220.42. This is likely to be the deepest element of the foreground character. To make sure we have the greatest number of grey levels available for our character, we will truncate the depth map at around this point, and set everything after it to black.
```
$ python format_depthmap.py --depth_cutoff 220.42 simple_example-Canvas2-Depth.exr
mapping status was: Success
```

### Step three - converting the normal map
The normal map can be converted with any image processing tool that can read EXR. From the command line, ImageMagick's `convert` works well: `convert simple_example-Canvas3-Normal.exr simple_example.normal.png`.

### Step four - generating the pose data, setting up, and rendering a result
From here, things are fairly straightforward. In ControlNet, generate pose data from the rendered image (I suggest using dw_openpose_full for this), and then do any required clean-up in the internal editor (I tweaked the points in the left hand slightly). I find it useful to save the generated pose information once you're happy with it.

At this point, the products we have in our workflow include these four images - I have resized these down, but each would normally be 1200x1200.
![montage-small](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/0857ac94-12d0-4d6e-9b56-3420dafa5310)

Load each of the pose, depth, and normal images into a relevant ControlNet unit, with the appropriate model - I use control_v11p_sd15_openpose, t2iadapter_depth_sd14v1, and control_v11p_sd15_normalbae respectively. For each unit, I start with a control weight of 0.3 and an ending control step of 0.5, with a 'balanced' control mode and tweak from there. Higher strength or a later end-step will make your generation more conformant, but unless you modeled background geometry in step one, this will eventually lead to your characters appearing in front of a featureless flat sheet.

This is also the time to fill in your prompt and attempt some generations. You can also think about whether to use Hires Fix or ADetailer - if you bring the renders out at a fairly high resolution (with a lot of face pixels) and with the relevant parts of the depth map being well defined, this may not be necessary.

In this case, after a bit of tweaking, these were some of the results I produced:
![result-montage](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/f765f389-dc76-4c4d-bbc5-891fe0216e0c)

## Example two - manipulating the depth map and using regional prompting
One of the downsides of the ControlNet depthmap models is that they appear to have been conditioned using 256 level greyscale depthmaps - only 256 different levels of depth can be differentiated by them. By contrast, depthmap formats like OpenEXR are limited only by the precision of floating point numbers. As we saw above, software can work out the range of available depths in an image and then divide this up into 256 equal blocks, but there will be times where we want to focus that addressable depth into particular areas of the picture that are most important, like faces.

In this example, we are modelling a person looking into a magic mirror. Because Daz doesn't have a way to represent "portals", we have composed our scene with an individual at a desk, some simple geometry to represent the mirror frame, and a mirrored copy of the first figure to be the reflection. After positioning the camera, these elements were moved around until they felt "right", and the mirrored figure was adjusted slightly to look at the camera.

![image](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/e1c25f9d-ef0b-408d-b267-b69f6baef80e)

This example picks up at the point where we are manipulating the depth map. For this example, we won't be using a normal map, because we're actually going to repaint the depth map slightly to hide some items in the scene.

### Processing the depth map, interactively
The interactive mode works by inserting "splits" into the full range of depth values, resizing those splits, and assigning them a share of the available 256 depth levels. Splits contain their start value, but not their end value.

In this case, I am going to create five splits. 
* The first one will contain our first individual, the one looking into the mirror. They will receive a large share of levels.
* The second will contain the area between the person and the mirror. It will only receive a few depth levels.
* The third will contain the mirror frame. It will get a moderate number of depth levels.
* The fourth will contain the other person, looking out from the mirror. They will also receive a large share of levels.
* The fifth and final split will contain the background.

I start the depthmap processor like this:
```
$ python format_depthmap.py --interactive mirrors-Canvas2-Depth.exr
Welcome to the interactive shell. Type help or ? to list commands.
>
```

The first thing I want to do is create my first split, but before I can do that I need to get a sense of the existing values in the file. I can do this with the `show_splits` command.
```
> show_splits
 ** 000: 93.46874237060547 to 281.48592163085937 - 256 levels assigned (label: Default)
>
```

I'll try creating a split at 100, and see if the 93.4 to 100 split captures the first individual. I can test it by assigning it a testing colour with `flag`, and then using the `test` command. You can use normal CSS colour names for this flag.
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

Our new red split isn't pushing far enough into the map, so I'm going to use the "move" command to shift its endpoint. (Move can only be used on a depth corresponding to the start or end of a split, and there are a number of restrictions on what can be moved and where - e.g. you can't move the end of a split past the end of the depth map, or past the end of the next split.)
```
> move 100 120
Success
> test
mapping status was: Success
```
This is better, but still not quite right. I add some more splits and keep tweaking it.

![testsmall](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/fb2146b8-679b-4a4d-ae54-932167f5cdf5)

I keep moving the starts and ends of the splits, and eventually I get something I'm happy with:
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
Next, I open the depth map in [Gimp](https://www.gimp.org/), although any modern image editor with layer support should work fine. I convert the image to RGB colour depth, and begin to make some changes. The first thing I want to do is overpaint the areas where the reflection in the mirror 'sticks out' from its edges.

The main trick when working with depth maps is to use the Fuzzy Select Tool (aka the "Magic Wand") with a threshold of zero, allowing you to grab all the connected pixels at the same depth. In Gimp, specifically, you can click and drag left and right to expand or contract the threshold as you select, allowing you to grab large areas of connected geometry. Once you have the area you want selected, switch to another layer and use the Bucket Fill tool in its "fill entire selection" mode to hard colour your selection. Once I'd finished, my revised depth map looked like this:

![tampered-montage](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/1d16e7d1-9676-4d5b-9052-1b394c836c08)

### Painting the regions
I now want to use colours to mask out all the separate "entities" of the image. Each area I separate in this way can receive its own prompt in the resutling generation.

This is mostly done using the Fuzzy Select and Bucket tools as described above, dropping each area onto its own layer and then painting it in with solid colour. The colours you use here matter, because the addon we'll be using, [sd-webui-regional-prompter](https://github.com/hako-mikan/sd-webui-regional-prompter) uses colour to match up each point in the image with the appropriate prompt. The relationship looks like this:

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

Once I have the basics of the layers set up, I will generally go through them, expand each one by a one pixel radius, and re-fill it to avoid 'seams' between the layers.

When I had finished painting and stacking my layers, they looked like this:

![tampered-region-small](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/9682f34c-84cd-4297-be1f-f0f15e4f9688)

### Prompting
This time, I only run two ControlNet units - pose and depth. Depth is set up like normal, but in this case, Pose needed a lot of manual work as it completely blanked on the nearest figure. I also told it to ignore the hands and right forearm of the figure in the mirror.

Once that's done, turn on Regional Prompting, and set the mode to "Mask". You'll want to then drag and drop your combined regions map to the area at the bottom right marked "Upload mask here cus gradio". You can test your mask by setting the region slider to 0, and then clicking "Draw region + show mask" to show you a representation of how the addon is reading your file, and to move on to the next region.  I recommend setting your options to be Generation mode: latent, Base ratio: 0.2, and "use base prompt". Generation mode is mostly to do with LORA compatibility, which is too complex to discuss here - see the addon's [documentation](https://github.com/hako-mikan/sd-webui-regional-prompter) for more details.

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





