# daz_depthmap_processor
Reprocesses depthmaps produced by Daz for use in Controlnet

## overview

Generally, I render Controlnet subjects against a flat polygon backdrop or inside a cube to avoid "bleeding" at the edge of the shapes. Because of this, the depthmaps (which only allow for 256 depth levels) must sacrifice detail during the normalisation process to ensure this "back wall" is included at the maximum distance. 

This tool lets you instead pick a cutting distance, and provides a few additional features. The only required argument is one or more exr files (a requirement for an .exr extension is enforced for these).  For an input file of input.exr, you will receive a file named input.depth.png.

## --depth_cutoff

The main argument. If left unspecified, no depth cutting is performed. If specified as a string like `python format_depthmap.py --depth_cutoff 280.69`, all values in the depthmap will be clamped to this maximum before normalisation takes place.

--depth_cutoff can also be specified as 'histo'. This produces a short summary of pixel mass in each of twenty depth buckets for your image, and can help you select an appropriate cutoff. For example:

```
$ python format_depthmap.py --depth_cutoff histo depth.exr
** providing cutting histogram advice, but leaving depthmap unchanged
** - 00 - 0.88% - 189.8212127685547
** - 01 - 1.02% - 201.18017807006837
** - 02 - 0.97% - 212.53914337158204
** - 03 - 0.78% - 223.8981086730957
** - 04 - 2.10% - 235.25707397460937
** - 05 - 5.03% - 246.61603927612305
** - 06 - 4.53% - 257.9750045776367
** - 07 - 0.82% - 269.3339698791504
** - 08 - 0.06% - 280.69293518066405
** - 09 - 0.05% - 292.05190048217776
** - 10 - 0.04% - 303.4108657836914
** - 11 - 0.04% - 314.76983108520506
** - 12 - 0.03% - 326.12879638671876
** - 13 - 0.04% - 337.48776168823247
** - 14 - 0.04% - 348.8467269897461
** - 15 - 0.04% - 360.20569229125977
** - 16 - 0.05% - 371.5646575927734
** - 17 - 0.06% - 382.9236228942871
** - 18 - 0.08% - 394.2825881958008
** - 19 - 83.13% - 405.6415534973145
```
Note the sharp dropoff between buckets seven and eight, indicating that 280.69 is a reasonable point to cut. 'histo' does not itself modify the depthmap prior to normalisation.

## --compress_map

A depth map can be 'sparse' where there are distances between the nearest and furthest points which are not used by any pixel in the map. This empty space still has to be fitted into the 0-255 level final depth map, which may then require you to lose detail at other points by collapsing neighboring depth levels together. --compress_map removes these empty spaces, meaning better representation of fine detail, but a potential loss in the distance relationship degree between different parts of the image. I tend to find the tradeoff worth it.

## --noise

If selected, replaces ares of maximum depth in the final map with white noise. Can sometimes help in obtaining a non-flat background out of A111, but you are probably better masking instead.

## --mask

If selected, generates a two tone mask separating maximum mapped depth from everything else. (This is done before applying noise, if necessary.) The file will be saved in input.mask.png.

## examples
### original iray rendering
![surfer](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/3ced6491-47b6-494f-a5ed-1b5565a47e3e)
### with no arguments
```
$ python format_depthmap.py surfer-depth.exr
```
![surfers-defaults](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/f2fbfe0e-9335-4139-8be7-0968496cfb8c)
### histo and cut to remove second surfer
```
$ python format_depthmap.py surfer-depth.exr --depth_cutoff=histo
** providing cutting histogram advice, but leaving depthmap unchanged
** - 00 - 18.14% - 286.2854309082031
** - 01 - 7.13% - 303.82092437744143
** - 02 - 0.11% - 321.3564178466797
** - 03 - 0.06% - 338.891911315918
** - 04 - 0.04% - 356.4274047851562
** - 05 - 0.03% - 373.96289825439453
** - 06 - 0.03% - 391.49839172363284
** - 07 - 0.03% - 409.03388519287114
** - 08 - 0.03% - 426.5693786621094
** - 09 - 0.02% - 444.10487213134763
** - 10 - 1.76% - 461.64036560058594
** - 11 - 6.39% - 479.17585906982424
** - 12 - 1.99% - 496.71135253906255
** - 13 - 0.11% - 514.2468460083007
** - 14 - 0.09% - 531.7823394775392
** - 15 - 0.08% - 549.3178329467773
** - 16 - 0.08% - 566.8533264160156
** - 17 - 0.10% - 584.388819885254
** - 18 - 0.13% - 601.9243133544921
** - 19 - 1.62% - 619.4598068237306
$ python format_depthmap.py surfer-depth.exr --depth_cutoff=321.35
```
![surfers-cut](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/30c8b42b-c447-4699-9080-7bd81c90a82c)
### mask
```
$ python format_depthmap.py surfer-depth.exr --depth_cutoff=321.35 --mask
```
![surfer-depth mask](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/698fdc71-3db3-46fa-9aa1-f3098e9fa6dc)
### noise
```
$ python format_depthmap.py surfer-depth.exr --depth_cutoff=321.35 --noise
```
![surfers-noise](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/9068c7bd-9c09-4fe6-ad56-d3616b1e495f)
### diffusion generation
The following generations use _only_ t2iadaptor-depth, omitting hires fix, use of a normal map, openpose keypoints, or adetailer for the faces or hands.
![composite](https://github.com/curiousjp/daz_depthmap_processor/assets/48515264/c26b802a-891a-4edf-9a86-b16bba4e1924)
