from board import SCL, SDA
from PIL import Image, ImageDraw, ImageFont
import busio
import adafruit_ssd1306
import asyncio
import time

import sys
import os
folder = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath("%s/.." % folder))
flip_display = 1



class display:
    bulb_state  = []
    brightness = []
    max_bulbs = 4
    im_bulb_resized = []

    def __init__(self, bulbs_n, display_time = 1):
        self.i2c               = busio.I2C(SCL, SDA)
        self.display_time      = display_time
        self.disp              = adafruit_ssd1306.SSD1306_I2C(128, 32, self.i2c)
        self.max_bulbs         = bulbs_n
        self.update_display      = 0
        self.last_displayed_bulb = 10
        self.last_bulb_state     = 10
        self.last_brightness     = 101
        self.image             = Image.new('1', (self.disp.width, self.disp.height))
        self.image_detail      = Image.new('1', (self.disp.width, self.disp.height))
        self.draw              = ImageDraw.Draw(self.image)
        self.draw_detail       = ImageDraw.Draw(self.image_detail)
        self.im_bulb           = [Image.open(folder+"/bulb_off.png"), Image.open(folder+"/bulb_on_25.png"),
            Image.open(folder+"/bulb_on_50.png"), Image.open(folder+"/bulb_on_75.png"), Image.open(folder+"/bulb_on_full.png")]

        self.disp.fill(0)
        self.disp.show()

        #convert to 1 bit image
        for x in range(0,len(self.im_bulb)):
            self.im_bulb[x] = self.im_bulb[x].convert('1')

        #create nagtive images
        for a in range(len(self.im_bulb)):
            for x in range(0, self.im_bulb[a].width):
                for y in range(0, self.im_bulb[0].height):
                    self.im_bulb[a].putpixel((x,y), not(self.im_bulb[a].getpixel((x,y))))

        #resize image
        self.new_size   = int((128.0 / self.max_bulbs))
        self.new_size_y = int(((self.new_size / 32.0) * self.im_bulb[0].height) + 0.5)
        for x in self.im_bulb:
            self.im_bulb_resized.append(x.resize((self.new_size, self.new_size)))

        #calc font size
        font_size = self.disp.height - self.new_size_y
        self.font = ImageFont.truetype(folder+"/arial.ttf", font_size)

        self.font_detail = ImageFont.truetype(folder+"/arial.ttf", 14)

        #paste bulbs into 32*128 image and init state variables
        self.width = 0
        for x in range(0, self.max_bulbs):
            self.bulb_state.append(0)
            self.brightness.append(0)
            self.image.paste(self.im_bulb_resized[0], (self.width, 0))
            self.width += self.new_size

    #update display
    def update(self):
        if flip_display:
            self.disp.image(self.image.rotate(180))
        else:
            self.disp.image(self.image)
        self.disp.show()

    #set bulb stat
    def set_status(self, bulb, status, dimmer, bulb_name):
            brightness = int((dimmer+1)/(255/100))
            self.brightness[bulb] = brightness
            if status:                                                         #on
                if self.brightness[bulb] <= 25:
                    self.bulb_state[bulb]  = 1
                elif self.brightness[bulb] > 25 and self.brightness[bulb] <= 50:
                    self.bulb_state[bulb]  = 2
                elif self.brightness[bulb] > 50 and self.brightness[bulb] <= 75:
                    self.bulb_state[bulb]  = 3
                else:
                    self.bulb_state[bulb]  = 4
            else:
                self.bulb_state[bulb] = 0
            self.draw_text(bulb)
            self.paste_bulb(bulb)
            self.updated_bulb = bulb
            self.updated_bulb_name = bulb_name
            self.update_display = 1
  

    #draw status text to image
    def draw_text(self, bulb):
        text  = "off"
        if self.bulb_state[bulb]:
            text = ("%d%%" % self.brightness[bulb])
        text_size  = self.draw.textsize(text, self.font)
        x_offset   = int((self.new_size/2 - text_size[0]/2)+0.5)
        self.draw.rectangle((self.new_size * bulb, self.new_size, self.new_size * bulb + self.new_size, self.disp.height), outline=0, fill=0)
        self.draw.text((bulb * self.new_size + x_offset, self.new_size_y), text, font=self.font, fill=255)

    def paste_bulb(self, bulb):
        self.image.paste(self.im_bulb_resized[self.bulb_state[bulb]], (bulb*self.new_size, 0))


    def show_details(self, bulb, bulb_name, brightness):
            if(bulb != self.last_displayed_bulb or brightness != self.last_brightness or self.bulb_state[bulb] != self.last_bulb_state):
                self.draw_detail.rectangle((0,0, 128, 32), outline=0, fill=0) 
                self.disp.image(self.image_detail)                             
                self.disp.show()
                self.image_detail.paste(self.im_bulb[self.bulb_state[bulb]], (0, 0))        #paste state image
                text = "%s" % bulb_name
                self.draw_detail.text((32, 0), text, font=self.font_detail, fill=255)
                text = "%d%%" % brightness
                if self.bulb_state[bulb] == 0:
                    text = "off"
                self.draw_detail.text((32, 13), text, font=self.font_detail, fill=255)
                if flip_display:
                    self.disp.image(self.image_detail.rotate(180))
                else:
                    self.disp.image(self.image_detail)
                self.disp.show()
                self.last_brightness = brightness
                self.last_displayed_bulb = bulb
                self.last_bulb_state = self.bulb_state[bulb]  
    
    def controler(self):       
        if self.update_display == 1:
            self.show_details(self.updated_bulb, self.updated_bulb_name, self.brightness[self.updated_bulb])
            self.start_time = time.perf_counter()
            self.update_display = 2
        elif self.update_display == 2:
            if(time.perf_counter() - self.start_time) > self.display_time:
                self.update()
                self.update_display = 0

