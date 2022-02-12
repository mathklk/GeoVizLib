# GeoVizLib

A Python library with multiple methods to visualize and analyse geographical data.

Currently only the grid-ASCII format (.asc) is supported, but I am working on GeoTIFF support.

Methods to visualize currently include:
- Convert height data to RGB-Range image (`.draw_rgb_gradient()`)
- Convert height data to grayscale image (`.draw_grayscale()`)
- Simulate a higher sealevel (`.draw_sealevel()` and `.draw_realwater()`)
- Convert the height data to a 3D file (Wavefront-Obj) (`.generate_obj()`)

# Installation

To install the required libraries, type `pip install -r requirements.txt`.
To use this class, place the `Geo.py` file in your project folder and import it. That's it!

# Usage
To use the methods, greate a `Geo` object and initialize it with your grid-Ascii-file.
```
from Geo import Geo

germany = Geo('dgm1000_gk3.asc')
```
Now you can apply different types of visualization and data analysis.

# Examples

## Average height
```
from Geo import Geo

germany = Geo('dgm1000_gk3.asc')

print(germany.avg_height())

-> 253.97040630685345
```
## RGB Gradient
```
from Geo import Geo

germany = Geo('dgm1000_gk3.asc')
germany.draw_rgb_gradient()
germany.export('germany_rgb_gradient.png')
```
Note that **all** methods starting with **draw** require to be exported with `.export()`

![germany_rgb_gradient.png](https://i.imgur.com/CgV0B29.png)

## Export to 3D Model
```
from Geo import Geo

germany = Geo('dgm1000_gk3.asc')
germany.generate_obj('germany_3d_model.obj', 5, -9000)
```

![germany_3d_model](https://i.imgur.com/al5MOeS.jpg)

## What if the sealevel would rise?
```
from Geo import Geo

germany = Geo('dgm1000_gk3.asc')
germany.draw_realwater(500)
germany.export('germany_sealevel500.png')
```

![germany_sealevel500](https://i.imgur.com/ADoWTiR.png)

# Resources

Here are some websites where you can download geographical data for free (for private use)

## Germany

[BKG](https://gdz.bkg.bund.de/index.php/default/catalog/product/view/id/756/s/digitales-gelandemodell-gitterweite-200-m-dgm200/category/8/?___store=default)


## Europe

[Copernicus](https://land.copernicus.eu/imagery-in-situ/eu-dem/eu-dem-v1.1?tab=mapview)

