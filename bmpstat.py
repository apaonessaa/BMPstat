import math

class ValueNotInExcludeEnd(Exception):
    def __init__(self, message, x, start, end):
        super().__init__(message)
        self.x = x
        self.start = start
        self.end = end

    def __str__(self):
        return f"ValueNotInExcludeEnd@{self.args[0]}: {self.x} not in [{self.start}, {self.end})"

class BMPstat(object):
    raw_image: bytearray=[]

    def __init__(self, raw_image):
        self.raw_image = bytearray(raw_image)

    def set_raw_image(self, raw_image):
        self.raw_image = bytearray(raw_image)
            
    def get_raw_image(self):
        return bytes(self.raw_image)

    def get_offset(self):
        """
        bitmap image data (pixel array) offset
        [+] start offset:     10 bytes
        [+] size:             4 bytes
        """
        return int.from_bytes(self.raw_image[10:14], byteorder='little')

    def get_size(self):
        """
        bitmap image width & height (signed integer)
        [+] start offset:     18 bytes
        [+] size:             4 bytes
        """
        width = int.from_bytes(self.raw_image[18:22], byteorder='little')
        height = int.from_bytes(self.raw_image[22:26], byteorder='little')
        return width, height

    def get_bpp(self):
        """
        bitmap image bpp (bits per pixel)
        [+] start offset:     28 bytes
        [+] size:             2 bytes
        """
        bpp = int.from_bytes(self.raw_image[28:30], byteorder='little')
        return bpp
    
    def get_Bpp(self):
        """
        bitmap image Bpp (Bytes per pixel)
        Note: 1, 4 o 8 bits per pixel
        """
        bpp = self.get_bpp()
        return max(1, bpp // 8)
    
    def get_rowsize_bpp(self):
        """
        bitmap image row size in BITS
        [+] width, image width expressed in pixels
        [+] bpp, bits per pixel
        """
        width, _ = self.get_size()
        bpp = self.get_bpp()
        return bpp * width
    
    def get_rowsize(self):
        """
        bitmap image row size in BYTES
        """
        row_size_bpp = self.get_rowsize_bpp()
        return math.ceil(row_size_bpp / 8)

    def get_eff_rowsize(self):
        """
        Effective rowsize [data + padding]
        """
        return self.get_rowsize() + self.get_padding() 

    def get_payload_size(self):
        """
        bitmap image size in pixel, pixel array size
        rawdata + padding
        """
        rowsize = self.get_eff_rowsize() # BYTES
        _, height = self.get_size()
        return height * rowsize # BYTES
    
    def get_payload(self):
        """
        bitmap image data (pixel array), bytearray format
        [+] start offset:     10 bytes
        [+] size:             4 bytes
        """
        start = self.get_offset()
        payload_size = self.get_payload_size()
        return self.raw_image[start:start+payload_size]
    
    def set_payload(self, payload: bytearray):
        """
        bitmap image data (pixel array), bytearray format
        [+] start offset:     10 bytes
        [+] size:             4 bytes
        """
        start = self.get_offset()
        payload_size = self.get_payload_size()
        if len(payload) != payload_size:
            raise ValueError('Error')
        self.raw_image[start:start+payload_size] = payload
    
    def get_padding(self):
        """
        # Padding
        Bitmap pixel data is stored in rows (also known as strides or scan lines).
        Each row's size must be a multiple of 4 bytes (a 32-bit DWORD).
        If the row's raw data is not already a multiple of 4 bytes, padding bytes are added at the end.
        Maximum padding size: 3 bytes (since a full 4-byte padding block is unnecessary).

        Example: 
          - 24-bit BMP (Bpp = 3 bytes per pixel), Width = 1 pixel
          - Raw row size = 1 * 3 = 3 bytes (not a multiple of 4)
          - (1) Compute remainder: 3 bytes % 4 = 3
          - (2) Compute padding: 4 - 3 = 1
          - (3) Apply final mod 4 to ensure padding is never 4: (4 - 3) % 4 = 1
          - Final row structure: [3 bytes pixel data] + [1 byte padding]

        General steps:
          (1) Compute raw row size: width * Bpp
          (2) Compute required padding: 4 - (raw row size % 4)
          (3) Apply mod 4 to prevent a full 4-byte padding block (unnecessary)

        If the row size is already a multiple of 4, the formula ensures padding = 0.
        """
        width, _ = self.get_size()
        Bpp = self.get_Bpp()
        row_padding = (4 - (width * Bpp) % 4)  
        return row_padding % 4 # BYTES

    def check_width_w_padding(self, w):
        width, _ = self.get_size()
        padding = 1 if self.get_payload_size() > 0 else 0
        if w < 0 or w >= width + padding:
            raise ValueNotInExcludeEnd("Width value out of bounds, the padding is included", w, 0, width+padding)

    def check_width(self, w):
        width, _ = self.get_size()
        if w < 0 or w >= width:
            raise ValueNotInExcludeEnd("Width value out of bounds", w, 0, width)

    def check_height(self, h):
        _, height = self.get_size()
        if h < 0 or h >= height:
            raise ValueNotInExcludeEnd("Height value out of bounds", h, 0, height)

    def check_layer(self, layer):
        Bpp = self.get_Bpp()
        if layer >= Bpp:
            raise ValueNotInExcludeEnd("Layer value out of bounds", layer, 0, Bpp)

    def check_sublayer(self, sublayer):
        bpp = self.get_bpp()
        if sublayer >= bpp:
            raise ValueNotInExcludeEnd("Sublayer value out of bounds", sublayer, 0, bpp)

    def set_one(self, i: int, j: int, layer: int, sublayer: int):
        """
        Sets the specific bit (sublayer) to 1 in a pixel (i, j, layer).

        sublayer: [0,1,2,3,4,5,6,7]
        """
        self.check_sublayer(sublayer)
        def bitmask(offset):
            mask = 1 << sublayer
            self.raw_image[offset] |= mask
        return self.apply_bitmask(i, j, layer, bitmask)

    def set_zero(self, i: int, j: int, layer: int, sublayer: int):
        """
        Sets the specific bit (sublayer) to 0 in a pixel (i, j, layer).

        sublayer: [0,1,2,3,4,5,6,7]
        """
        self.check_sublayer(sublayer)
        def bitmask(offset):  
            mask = 0xFF ^ (1 << sublayer)
            self.raw_image[offset] &= mask
        return self.apply_bitmask(i, j, layer, bitmask)

    def get_pixel_offset(self, i: int, j: int):
        width, height = self.get_size()
        if i<0 or i>=width:
            raise ValueNotInExcludeEnd(f"Pixel({i},{j}) the i is out of range", i, 0, width)
        if j<0 or j>=height:
            raise ValueNotInExcludeEnd(f"Pixel({i},{j}) the j is out of range", j, 0, height)
        """
            Base offset of BMP payload: self.get_offset()
            Which row? j*eff_rowsize
            Which pixel of the current row? i*Bpp
        """
        return self.get_offset() + j*self.get_eff_rowsize() + i*self.get_Bpp()

    def apply_bitmask(self, i: int, j: int, layer: int, bitmask):
        """
        Apply a mask to bits of specific pixel (i,j) and layer/channel (RGB)
        """
        self.check_width(i)
        self.check_height(j)
        self.check_layer(layer)
        """
            Which layer RGB? layer
            Which sublayer [0,1,2,3,4,5,6,7] to modify? How to modify? bitmask  
        """
        offset = self.get_pixel_offset(i,j) + layer
        bitmask(offset)
        return self
