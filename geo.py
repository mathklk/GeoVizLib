from PIL import Image, ImageDraw
import rasterio as rio
import numpy as np
from progress.bar import Bar
import os
import enum
import filetype


# Custom Error class for errors caused within this module
class GeoError(Exception):
    pass


class Format(enum.Enum):
    ASC = 1  # Ascii-Grid
    TIFF = 2  # GeoTIFF


class Geo:
    # # # # # # # # # #
    # Initialization  #
    # # # # # # # # # #

    def __init__(self, source_filename: str, file_format: Format = None):
        """
        Initializes the Geo-Object from either an Ascii-Grid or a GeoTIFF file
        :param source_filename: The name of the source file
        :param file_format: Specifiy a file format. If set to None, the format will be identified automatically.
        """
        if file_format is None:
            self._file_format = self._guess_filetype(source_filename)
        else:
            self._file_format = file_format

        # These values have to be filled in by the load-methods
        self._nodata_value = None
        self._file_nrows = None
        self._file_ncols = None
        self._file_cellsize = None
        self.array = None  # PUBLIC

        self._last_loaded_file = source_filename
        if self._file_format is Format.ASC:
            self.load_from_asc(source_filename)
        elif self._file_format is Format.TIFF:
            self.load_from_tif(source_filename)

        self._draw = None
        self._image = None

    def __str__(self):
        if self.array:
            print('<Geo-Class object created from ', self._last_loaded_file, '>', sep='')
        else:
            print('<Unitialized Geo-Class object (No data was loaded)>')

    def printstat(self):
        print('Data loaded from', self._last_loaded_file, 'as', self._file_format)
        print('Nodata Value:', self._nodata_value)
        print('Array size:', self._file_nrows, 'rows x', self._file_ncols, 'columns')
        print('Cellsize:', self._file_cellsize)
        print(f"{'A' if self._draw else 'No'} canvas is loaded.")


    @staticmethod
    def _guess_filetype(filename: str) -> Format:
        ext = filename.split('.')[-1].lower()
        g = filetype.guess(filename)
        if ext == 'tif' or (g and g.mime == 'image/tiff'):
            return Format.TIFF
        elif ext == 'asc':
            return Format.ASC
        else:
            raise GeoError('Unable to guess the format of the file \'' + str(filename) + '\'. Please specifiy a format manually.')

    # # # # # # # # #
    # Data Reading  #
    # # # # # # # # #

    def load_from_tif(self, tif_filename, nodata_value=np.float32(-3.4028235e+38), cellsize=1):
        """
        Loads an array from a GeoTIFF-file
        :param tif_filename: The file to read from
        :param nodata_value: The value that is used as a placeholder for 'no data' in the file
        :param cellsize: TODO
        :return:
        """

        if nodata_value is None:
            raise GeoError('The nodata-value is set to None. This is very likely incorrect.')

        self._file_cellsize = cellsize
        self._nodata_value = nodata_value
        print('Reading data (TIF)...')
        with rio.open(tif_filename) as im:
            self.array = im.read()[0]
            self._file_nrows = len(self.array)
            self._file_ncols = len(self.array[0])
        print(f'File \'{tif_filename}\' successfully read.')

    def load_from_asc(self, asc_filename):
        try:
            desc = Geo._read_asc_descriptor(asc_filename)
        except ValueError as e:
            raise GeoError(f"The file '{asc_filename}' has an invalid descriptor. Please overlook the descriptor manually.")

        self._nodata_value = desc['NODATA_VALUE']
        self._file_nrows = desc['NROWS']
        self._file_ncols = desc['NCOLS']
        self._file_cellsize = desc['CELLSIZE']
        # self._descriptor_len = desc['descriptor_len']
        self.array = self._read_asc_array(asc_filename, len(desc))
        print(f'File \'{asc_filename}\' successfully read.')

    @staticmethod
    def _read_asc_descriptor(filename):
        ret = {}
        with open(filename, 'r') as f:
            line = ''
            desc_len = -1
            while len(line) < 50:
                desc_len += 1
                line = f.readline()
                while '  ' in line:
                    line = line.replace('  ', ' ')
                kv = line.split(' ')
                ret[kv[0]] = int(kv[1])
        # ret['descriptor_len'] = desc_len
        return ret

    def _read_asc_array(self, filename, desc_len):
        def fail_float(x):
            try:
                ret = float(x)
            except:
                ret = self._nodata_value
            return ret

        data = np.array([[None] * self._file_ncols] * (self._file_nrows - 1))
        bar = Bar('Reading Data (ASC)', max=self._file_nrows)
        with open(filename) as f:
            for _ in range(desc_len):
                f.readline()

            for y in range(self._file_nrows):
                line = f.readline().strip()
                for x, v in enumerate([fail_float(x) for x in line.split(' ') if x]):
                    # print(y,x, v)
                    data[y, x] = v
                bar.next()
        bar.finish()
        return data

    # # # # # # # #
    # Data Saving #
    # # # # # # # #

    def save_as_asc(self, filename, auto_rename_filename: bool = True):
        """
        Exports the currently loaded array as an .asc-file.
        :param filename: The name of the new file
        :param custom_nodata_value: if set to something other than None, this will replace the current nodata-value
        :param auto_rename_filename: If the chosen filename already exists, the filename will be slightly modified. The manufacturer recommends to leave this as True
        :return:
        """

        while auto_rename_filename and os.path.isfile(filename):
            filename = '_' + filename

        custom_nodata_value: int = -9999

        with open(filename, 'a+') as f:
            f.write('NCOLS          ' + str(self._file_ncols))
            f.write('\nNROWS          ' + str(self._file_nrows))
            f.write('\nXLLCENTER      ' + str(-1))  # TODO
            f.write('\nYLLCENTER      ' + str(-1))
            f.write('\nCELLSIZE       ' + str(self._file_cellsize))
            f.write('\nNODATA_VALUE   ' + str(custom_nodata_value))

            bar = Bar('Saving', max=self._file_nrows)
            for row in self.array:
                f.write('\n')
                for current_value in row:
                    #print('[Current Value]\n', (current_value))
                    #print('[Nodata Value]', type(self._nodata_value))#, self._nodata_value, int(self._nodata_value))

                    if custom_nodata_value is not None and int(current_value) == int(self._nodata_value):
                        current_value = custom_nodata_value
                    f.write(str(int(current_value)))
                    f.write(' ')
                bar.next()
            print('File saved as \'' + filename + '\'')

    # # # # # # # # # # # # # # # #
    # Misc. Data Transformations  #
    # # # # # # # # # # # # # # # #

    def _update_array_size(self):
        self._file_nrows = len(self.array)
        self._file_ncols = len(self.array[0])

    def reduce_resolution(self, factor):
        """
        Reduces the arrays resolution by leaving only keeping {factor} amount of rows and columns
        :param factor:
        :return:
        """
        self.array = self.array[::factor, ::factor]
        self._update_array_size()


    # # # # # # # # # # # # # # # # #
    # Internal Methods for drawing  #
    # # # # # # # # # # # # # # # # #

    @staticmethod
    def _val_as_rgb(value, gradient_interval):
        """
        Überträgt den Wert 'value' aus dem Intervall [minimum, maximum] auf das RGB-Spektrum
        :param value: Diesen Wert übertragen
        :return: r, g, b
        """
        minimum, maximum = float(gradient_interval[0]), float(gradient_interval[1])
        ratio = 2 * (value - minimum) / (maximum - minimum)
        b = int(max(0, 255 * (1 - ratio)))
        r = int(max(0, 255 * (ratio - 1)))
        g = 255 - b - r
        return r, g, b


    def _replace_color(self, this_one, with_this_one):
        pixelarray = list(self._image.getdata())
        n_pixel = 0
        bar = Bar('Replacing Colors', max=self._file_nrows)
        for y, line in enumerate(self.array):
            for x, field in enumerate(line):
                if pixelarray[n_pixel] == this_one:
                    self._draw.point((x, y), with_this_one)
                n_pixel += 1
            bar.next()
        bar.finish()

    def _calc_value_range(self):
        lowest_value = 9999
        highest_value = -9999

        bar = Bar('Analysing', max=self._file_nrows)
        for y, line in enumerate(self.array):
            for x, field in enumerate(line):
                if field != self._nodata_value:
                    lowest_value = min(lowest_value, field)
                    highest_value = max(highest_value, field)
            bar.next()
        bar.finish()
        # self._value_range = (lowest_value, highest_value)
        return lowest_value, highest_value

    def _new_canvas(self, force_overwrite: bool = False):
        """
        Creates a new PIL canvas and saves it internally (self._canvas)
        :param force_overwrite:
        :return:
        """
        if self._image is None and not force_overwrite:
            #self._image = Image.new('RGBA', (self._file_ncols, self._file_nrows)) # replaced with shape
            self._image = Image.new('RGBA', self.array.shape)
            self._draw = ImageDraw.Draw(self._image)

    def _draw_text(self, text, xy=(0, 0)):
        self._draw.text(xy=xy, text=text)

    def _TEMPLATE(self):
        self._new_canvas()
        bar = Bar('Drawing', max=self._file_nrows)
        for y, line in enumerate(self.array):
            for x, field in enumerate(line):
                pass
                pass
                self._draw.point((x, y), fill=None)
            bar.next()
        bar.finish()

    # # # # # # # # #
    # Visualization #
    # # # # # # # # #

    def draw_rgb_gradient(self, core_interval: tuple = 'auto', nodata_color=(255, 255, 255)):
        """
        Utilizes the full RGB-spectrum to visualize the given data linearly
        :param core_interval: (lowest, highest) Give all resolution to this interval. 'auto' -> full range
        :param nodata_color:
        :return:
        """
        if core_interval == 'auto':
            core_interval = self._calc_value_range()

        self._new_canvas()
        bar = Bar('Drawing', max=self._file_nrows)
        for y, line in enumerate(self.array):
            for x, field in enumerate(line):
                if field == self._nodata_value:
                    fieldcolor = nodata_color
                else:
                    fieldcolor = Geo._val_as_rgb(field, core_interval)
                self._draw.point((x, y), fill=fieldcolor)
            bar.next()
        bar.finish()

    def draw_grayscale(self):
        """
        Draws the map as a grayscale image
        :return:
        """

        value_range = self._calc_value_range()

        self._new_canvas()
        bar = Bar('Drawing', max=self._file_nrows)
        for y, line in enumerate(self.array):
            for x, field in enumerate(line):
                if field != self._nodata_value:
                    linear_value = field / (value_range[1] - value_range[0])
                    value = int(linear_value * 255)
                    color = (value, value, value, 255)
                else:
                    # value = int(value_range[0])  # evtl = 0?
                    color = (0, 0, 0, 0)

                self._draw.point((x, y), fill=color)

            bar.next()
        bar.finish()

    def draw_sealevel_rain(self, height_above_sealevel, water_color=(132, 194, 251), land_color=(252, 255, 212)):
        """
        Creates a map where every spot lower than the given parameter is filled with water
        :param height_above_sealevel:
        :param water_color: RGB
        :param land_color: RGB
        :return:
        """
        self._new_canvas()
        bar = Bar('Drawing', max=self._file_nrows)

        for y, line in enumerate(self.array):
            for x, field in enumerate(line):
                if field < height_above_sealevel:
                    fieldcolor = water_color
                else:
                    fieldcolor = land_color
                self._draw.point((x, y), fill=fieldcolor)
            bar.next()
        bar.finish()

    def old_draw_sealevel_flood(self, height_above_sealevel: float, water_source_coord=(0, 0), water_color=(132, 194, 251, 255), land_color=(252, 255, 212, 255),
                            name_sealevel_at_top_left: bool = True):
        """
        Creates a map where a flood originating from water_source_coord is simulated.
        Internally all spots lower than height_above_sealevel are colored with a temporary color, then a floodfill drawing tool is applied
        only replacing the temporary color.
        :param height_above_sealevel: Cells must lie lower than this height
        :param water_source_coord: Cells must be connected to this coordinate
        :param water_color: RGBA
        :param land_color: RGBA
        :param name_sealevel_at_top_left: Adds the height_above_sealevel as a text in the top left corner
        :return:
        """
        self._new_canvas()
        tempcolor = (0, 255, 0, 255)
        bar = Bar('Sketching', max=self._file_nrows)
        for y, line in enumerate(self.array):
            for x, field in enumerate(line):
                if field < height_above_sealevel:
                    color = tempcolor
                else:
                    color = land_color
                self._draw.point((x, y), color)
            bar.next()
        bar.finish()

        bar = Bar('Flooding', max=1)
        #bar.next()
        ImageDraw.floodfill(self._image, water_source_coord, value=water_color)
        self._image.save('TEMPEXPORT.png')
        bar.next()
        bar.finish()


        if name_sealevel_at_top_left:
            self._draw_text(str(height_above_sealevel))

    def draw_sealevel_flood(self, height, water_source_coord_yx: tuple = (0, 0), water_color=(132, 194, 251), land_color=(252, 255, 212),
                            name_sealevel_at_top_left: bool = True):

        sourceheight = self.array[water_source_coord_yx[0], water_source_coord_yx[1]]
        if sourceheight > height:
            raise GeoError(f'Water source coord {water_source_coord_yx} is not below the height {height} ({sourceheight} > {height})')

        tempcolor = (0, 255, 0)

        # initialising everything with landcolor
        #img_array = np.zeros((self.array.shape[0], self.array.shape[1], 3), dtype=np.uint8)
        img_array = np.full((self.array.shape[0], self.array.shape[1], 3), land_color, dtype=np.uint8)

        print('array created, now calcing')

        # filling everything below height with a temporary colour
        is_below_array = self.array <= height
        del self.array
        self.array = None
        img_array[is_below_array, :] = np.array(tempcolor).reshape(1, 1, 3)
        print('image array created, now creating image')


        self._image = Image.fromarray(img_array, mode='RGB')
        del img_array
        del is_below_array

        #print('aborting before floodfill')
        #return

        #print('Color at selected source is', img_array[water_source_coord_yx[0], water_source_coord_yx[1]])
        # Flood-filling with water_color, starting at water_source_coord
        ImageDraw.floodfill(self._image, water_source_coord_yx, value=water_color)

        # replacing tempcolor with landcolor
        width = self._image.size[0]
        height = self._image.size[1]
        for i in range(0, width):  # process all pixels
            for j in range(0, height):
                data = self._image.getpixel((i, j))
                # print(data) #(255, 255, 255)
                if (data[0] == tempcolor[0] and data[1] == tempcolor[1] and data[2] == tempcolor[2]):
                    self._image.putpixel((i, j), land_color)


    def export(self, filename, filetype='auto'):
        if filetype == 'auto':
            filetype = filename.split('.')[-1].upper()
        self._image.save(filename, filetype)
        print('Image saved to ', filename)

    def avg_height(self):
        """
        The average height of all datapoints.
        :return:
        """
        heightsum = 0
        number_of_values = 0
        self._new_canvas()
        bar = Bar('Drawing', max=self._file_nrows)
        for y, line in enumerate(self.array):
            for x, field in enumerate(line):
                if field != self._nodata_value:
                    heightsum += field
                    number_of_values += 1
            bar.next()
        bar.finish()
        print("Number of data entries: " + str(number_of_values))
        print("Sum: " + str(heightsum))
        avg = heightsum / number_of_values
        print("-> Average: " + str(avg))
        return avg

    def export_to_obj(self, filename, height_multiplier: float = 1, nodata_replacement: float = 0):
        """
        Converts the dataset to a Wavefront-Obj file.
        :param filename: Export to this filename (automatic extension)
        :param height_multiplier: All heights will be multiplied by this factor.
        :param nodata_replacement: Grid cells with no data will be given this height value.
        :return:
        """
        if '.obj' not in filename:
            filename += '.obj'
        f = open(filename, 'w+')
        f.write('# Generated by a Python Script from "Zciurus-Alt-Del"\no Object.1\n\n# vertices')

        bar = Bar('Writing vertices', max=self._file_nrows)
        for y, line in enumerate(self.array):
            for x, field in enumerate(line):
                if field == self._nodata_value:
                    field = nodata_replacement
                else:
                    field *= height_multiplier
                txtline = f"\nv {x * self._file_cellsize} {field} {y * self._file_cellsize}"  # When describing a vertex in .obj, the second point is the height
                f.write(txtline)
            bar.next()
        bar.finish()
        f.write("\n\n# faces")

        num_of_cells = self._file_nrows * self._file_ncols
        bar = Bar('Writing faces', max=num_of_cells)
        for n in range(num_of_cells - self._file_ncols):  # omit last line
            if not n % self._file_ncols == 0:  # omit right column
                me = n
                right = n + 1
                bot = n + self._file_ncols
                botright = n + self._file_ncols + 1
                f.write(f"\nf {me} {right} {botright}")
                f.write(f"\nf {me} {botright} {bot}")
            bar.next()
        bar.finish()

        f.close()
        print('Exported to', filename)

    # # # # #
    # Misc. #
    # # # # #

    @staticmethod
    def images_to_gif(gifname: str, filenames, duration=100, loop=0):
        """
        Turns the given list of files into a GIF

        :param gifname: The name of the destination file
        :param filenames: List of the source filenames
        :param duration: in milliseconds. The duration per frame
        :param loop:
        :return:
        """
        imgfiles = [Image.open(x, 'r') for x in filenames]
        imgfiles[0].save(gifname, format='GIF', append_images=imgfiles[1:], save_all=True, duration=duration, loop=loop)
        print('Gif successfully saved as ', gifname)

    @staticmethod
    def image_dir_to_gif(gifname: str, dir: str, duration=100, loop=0):
        if dir[-1] != '/':
            dir += '/'

        files = [dir + x for x in os.listdir(dir)]
        Geo.images_to_gif(gifname, files, duration, loop)
