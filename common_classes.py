'''
Copyright (C) 2014 CG Cookie
http://cgcookie.com
hello@cgcookie.com

Created by Jonathan Denning, Jonathan Williamson, and Patrick Moore

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

# Add the current __file__ path to the search path
import sys, os
sys.path.append(os.path.dirname(__file__))

import math
import copy
import time
import bpy, bmesh, blf, bgl
from bpy.props import EnumProperty, StringProperty,BoolProperty, IntProperty, FloatVectorProperty, FloatProperty
from bpy.types import Operator, AddonPreferences
from bpy_extras.view3d_utils import location_3d_to_region_2d, region_2d_to_vector_3d, region_2d_to_location_3d
from mathutils import Vector
from mathutils.geometry import intersect_line_plane, intersect_point_line

import common_utilities
import common_drawing


class MenuSearchPopup(object):
    def __init__(self,context,x,y, items):
        
        #the top center of the menu
        #which will fill in belwo
        self.x = x
        self.y = y
        
        self.text_size = 18
        self.text_dpi = 72
        
        self.input_string = ''
        self.max_str_len = 20
        self.items = items
        
        self.filter_items = []
        self.filter_item_index = 0
        self.max_filter_items = 6
        
        self.output = None
        
        #settings
        self.border = 10
        self.spacer = 5
        
        #establish width/box height etc
        bigdimX=bigdimY=0
        large_text = 'A' * self.max_str_len
        #find the biggest word in the menu and base the size of all buttons on that word
        blf.size(0, self.text_size, self.text_dpi)
        dimension = blf.dimensions(0, large_text)
    
        if dimension[0]>bigdimX:
            bigdimX = dimension[0]
        if dimension[1]>bigdimY:
            bigdimY = dimension[1]
                
        
        self.box_height = bigdimY
        self.width = bigdimX + 2 * self.border
        self.height = self.border + bigdimY + 2 * self.spacer + self.border
        
    def search_items(self):
        self.filter_items = []
        if not len(self.input_string):
            return
        
        for menu_item in self.items:
            if menu_item.startswith(self.input_string.lower()):
                self.filter_items.append(menu_item)
                continue
            
            if menu_item in self.input_string.lower():
                self.filter_items.append(menu_item)
                continue
        
    def modal_input_event(self,eventd):
        
        letter = eventd['type']
        
        alphabet_lower = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z',' ']
        alphabet = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z', ' ']
        actions = {'DEL', 'BACK_SPACE','NUMPAD_PLUS', 'NUMPAD_MINUS', 'DOWN_ARROW', 'UP_ARROW'}
        
        if letter in actions and eventd['press']:
            if letter in {'DEL', 'BACK_SPACE'}:
                if len(self.input_string):
                    self.input_string = self.input_string[:-1]
                    self.search_items()
                    
            if letter == 'DOWN_ARROW':
                if self.filter_item_index < len(self.filter_items) - 1:
                    self.filter_item_index += 1
                    
            if letter == 'UP_ARROW':
                if self.filter_item_index > 0:
                    self.filter_item_index -= 1
                    
            if letter == 'NUMPAD_PLUS':
                self.text_size += 1
                
            if letter == 'NUMPAD_MINUS':
                if self.text_size > 12:
                    self.text_size -= 1
                
        if letter in alphabet and len(self.input_string) < self.max_str_len and eventd['press']:
            if eventd['shift']:
                self.input_string += letter
                
            else:
                ind = alphabet.index(letter)
                self.input_string += alphabet_lower[ind]
                
            self.search_items()
            
        if letter == 'SPACE' and eventd['press']:
            self.input_string += ' '
            self.search_items()
                
    def pick_mouse(self,mouse_x,mouse_y):
        
        left = self.x - self.width/2
        right = left + self.width
        bottom = self.y - self.height
        top = self.y
        
        if not mouse_x < right and mouse_x > left:
            return
        
        if not mouse_y < top and mouse_y > bottom:
            return
        
        #work our way down from top
        items_top = self.y - self.border - self.box_height - 3 * self.spacer
        dist = items_top - mouse_y
        
        if dist < 0:
            return
        
        ind = math.floor(dist/(self.box_height + 2 * self.spacer))
        self.filter_item_index = ind
        return True
    
    def draw(self,context):
        txt_color = (.7,1,.7,1)
        bg_color = (.1, .1, .1, .7)
        search_color = (.2, .2, .2, 1)
        border_color = (.05, .05, .05, 1)
        highlight_color = (0,.3, 1, .8)
        
        #establish width
        bigdimX=bigdimY=0
        large_text = 'A' * self.max_str_len
        #find the biggest word in the menu and base the size of all buttons on that word
        blf.size(0, self.text_size, self.text_dpi)
        dimension = blf.dimensions(0, large_text)
    
        if dimension[0]>bigdimX:
            bigdimX = dimension[0]
        if dimension[1]>bigdimY:
            bigdimY = dimension[1]
                
        
        self.box_height = bigdimY
        self.width = bigdimX + 2 * self.border
        
        if self.input_string == 'all':
            n_items = len(self.items)
            self.filter_items = self.items
        else:
            n_items = min([len(self.filter_items), self.max_filter_items])
        
        if n_items == 0:
            self.height = self.border + bigdimY + 2 * self.spacer + self.border
        else:
            self.height = self.border + bigdimY + 2*self.spacer + n_items*(2*self.spacer + bigdimY) + self.border
        
        left = self.x - self.width/2
        right = left + self.width
        bottom = self.y - self.height
        top = self.y
        
        left_text = left + self.border
        bottom_text = bottom + self.border
        
        #draw the whole menu bacground
        outline = common_drawing.round_box(left, bottom, left +self.width, bottom + self.height, (self.box_height + 2 * self.spacer)/6)
        common_drawing.draw_outline_or_region('GL_POLYGON', outline, bg_color)
        common_drawing.draw_outline_or_region('GL_LINE_LOOP', outline, border_color)
        
        #draw the search box
        s_box = common_drawing.round_box(left + self.border, top - self.border - bigdimY - 2 * self.spacer, right - self.border, top - self.border, (self.box_height + 2 * self.spacer)/6)
        common_drawing.draw_outline_or_region('GL_POLYGON', s_box, search_color)
        common_drawing.draw_outline_or_region('GL_LINE_LOOP', s_box, border_color)
        
        blf.size(0, self.text_size, self.text_dpi)
        
        if len(self.input_string):
            txt_x = left_text + self.spacer
            txt_y = top - self.border - self.spacer - bigdimY
            blf.position(0,txt_x, txt_y, 0)
            bgl.glColor4f(*txt_color)
            blf.draw(0, self.input_string)
            
        if len(self.filter_items):
            for i, txt in enumerate(self.filter_items):
                if i > self.max_filter_items-1 and not self.input_string == 'all':
                    return
                txt_x = left_text + self.spacer
                txt_y = top - self.border - bigdimY - 2*self.spacer - (i+1) * (bigdimY + 2 * self.spacer)
                if i == self.filter_item_index:
                    box = [(left_text, txt_y - self.spacer),(left_text + bigdimX , txt_y-self.spacer),(left_text + bigdimX, txt_y + bigdimY + self.spacer),(left_text, txt_y + bigdimY + self.spacer)]
                    common_drawing.draw_outline_or_region('GL_POLYGON', box, highlight_color)
                    
                blf.position(0,txt_x, txt_y, 0)
                bgl.glColor4f(*txt_color)
                blf.draw(0, common_utilities.capitalize_all(txt))
        
class SketchBrush(object):
    def __init__(self,context,settings, x,y,pixel_radius, ob, n_samples = 15):
        
        self.settings = settings  #should be input from user prefs
        
        self.ob = ob
        self.pxl_rad = pixel_radius
        self.world_width = None
        self.n_sampl = n_samples
        
        self.x = x
        self.y = y
        
        self.init_x = x
        self.init_y = y
        
        self.mouse_circle  = []
        self.preview_circle = []
        self.sample_points = []
        self.world_sample_points = []
        
        self.right_handed = True
        self.screen_hand_reverse = False
        

    def update_mouse_move_hover(self,context, mouse_x, mouse_y):
        #update the location
        self.x = mouse_x
        self.y = mouse_y
        
        #don't think i need this
        self.init_x = self.x
        self.init_y = self.y
        
    def make_circles(self):
        self.mouse_circle = common_utilities.simple_circle(self.x, self.y, self.pxl_rad, 20)
        self.mouse_circle.append(self.mouse_circle[0])
        self.sample_points = common_utilities.simple_circle(self.x, self.y, self.pxl_rad, self.n_sampl)
        
    def get_brush_world_size(self,context):
        region = context.region  
        rv3d = context.space_data.region_3d
        center = (self.x,self.y)
        wrld_mx = self.ob.matrix_world
        
        vec, center_ray = common_utilities.ray_cast_region2d(region, rv3d, center, self.ob, self.settings)
        vec.normalize()
        widths = []
        self.world_sample_points = []
        
        if center_ray[2] != -1:
            for pt in self.sample_points:
                V, ray = common_utilities.ray_cast_region2d(region, rv3d, pt, self.ob, self.settings)
                if ray[2] != -1:
                    widths.append((wrld_mx * ray[0] - wrld_mx * center_ray[0]).length)
                    self.world_sample_points.append(wrld_mx * ray[0])
            
            l = len(widths)
            if l:
                # take median and correct for the view being parallel to the surface normal
                widths.sort()
                w = widths[int(l/2)+1] if l%2==1 else (widths[int(l/2)-1]+widths[int(l/2)+1])/2
                #self.world_width = w * abs(vec.dot(center_ray[1].normalized()))

            else:
                #defalt quad size in case we don't get to raycast succesfully
                #self.world_width = self.ob.dimensions.length * 1/self.settings.density_factor
                pass
                
            w = common_utilities.ray_cast_world_size(region, rv3d, center, self.pxl_rad, self.ob, self.settings)
            #self.world_width = w if w and w < float('inf') else self.ob.dimensions.length * 1/self.settings.density_factor
            #print(w)
            
        
        
    def brush_pix_size_init(self,context,x,y):
        
        if self.right_handed:
            new_x = self.x + self.pxl_rad
            if new_x > context.region.width:
                new_x = self.x - self.pxl_rad
                self.screen_hand_reverse = True
        else:
            new_x = self.x - self.pxl_rad
            if new_x < 0:
                new_x = self.x + self.pxl_rad
                self.screen_hand_reverse = True

        #NOTE.  Widget coordinates are in area space.
        #cursor warp takes coordinates in window space!
        #need to check that this works with t panel, n panel etc.
        context.window.cursor_warp(context.region.x + new_x, context.region.y + self.y)
        
        
    def brush_pix_size_interact(self,mouse_x,mouse_y, precise = False):
        #this handles right handedness and reflecting for screen
        side_factor = (-1 + 2 * self.right_handed) * (1 - 2 * self.screen_hand_reverse)
        
        #this will always be the corect sign wrt to change in radius
        rad_diff = side_factor * (mouse_x - (self.init_x + side_factor * self.pxl_rad))
        if precise:
            rad_diff *= .1
            
        if rad_diff < 0:
            rad_diff =  self.pxl_rad*(math.exp(rad_diff/self.pxl_rad) - 1)

        self.new_rad = self.pxl_rad + rad_diff    
        self.preview_circle = common_utilities.simple_circle(self.x, self.y, self.new_rad, 20)
        self.preview_circle.append(self.preview_circle[0])
        
        
    def brush_pix_size_confirm(self, context):
        if self.new_rad:
            self.pxl_rad = self.new_rad
            self.new_rad = None
            self.screen_hand_reverse = False
            self.preview_circle = []
            
            self.make_circles()
            self.get_brush_world_size(context)
            
            #put the mouse back
            context.window.cursor_warp(context.region.x + self.x, context.region.y + self.y)
            
    def brush_pix_size_cancel(self, context):
        self.preview_circle = []
        self.new_rad = None
        self.screen_hand_reverse = False
        context.window.cursor_warp(context.region.x + self.init_x, context.region.y + self.init_y)
    
    def brush_pix_size_pressure(self, mouse_x, mouse_y, pressure):
        'assume pressure from -1 to 1 with 0 being the midpoint'
        
        print('not implemented')
    
    def draw(self, context, color=(.7,.1,.8,.8), linewidth=2, color_size=(.8,.8,.8,.8)):
        #TODO color and size
        
        #draw the circle
        if self.mouse_circle != []:
            common_drawing.draw_polyline_from_points(context, self.mouse_circle, color, linewidth, "GL_LINE_SMOOTH")
        
        #draw the sample points which are raycast
        if self.world_sample_points != []:
            #TODO color and size
            #common_drawing.draw_3d_points(context, self.world_sample_points, (1,1,1,1), 3)
            pass
    
        #draw the preview circle if changing brush size
        if self.preview_circle != []:
            common_drawing.draw_polyline_from_points(context, self.preview_circle, color_size, linewidth, "GL_LINE_SMOOTH")
            
