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

