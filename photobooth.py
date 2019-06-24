#!/usr/bin/env python

import os
import glob
import time
import traceback
from time import sleep
import RPi.GPIO as GPIO
import picamera # http://picamera.readthedocs.org/en/release-1.4/install2.html
import atexit
import sys
import socket
import pygame
import config # this is the config python file config.py
from signal import alarm, signal, SIGALRM, SIGKILL
import PIL.Image

########################
### Variables Config ###
########################
led_pin = 7 # LED 
btn_pin = 18 # pin for the start button

num_pics_to_take = 3 # number of pics to be taken
countdown_seconds = 4
capture_delay = 3 # delay between pics
prep_delay = 3 # number of seconds before step 1, after button press before countdown
gif_delay = 20 # How much time between frames in the animated gif
time_to_display_final_image = 5 # How long should the final combined image display for

monitor_w = 1920    # width of the display monitor
monitor_h = 1080    # height of the display monitor

# Image ratio 4 x 3

# The live preview image shown to users
preview_image_w = 800
preview_image_h = 600

# full frame of the camera is 3280x2464
# if you run into resource issues, try smaller, like 1920x1152. 
# or increase memory http://picamera.readthedocs.io/en/release-1.12/fov.html#hardware-limits
high_res_w = 3280 # width of high res image, if taken
high_res_h = 2464 # height of high res image, if taken

make_gifs = True    # True to make an animated gif. False to post 4 jpgs into one post.
camera_iso = 400    # adjust for lighting issues. Normal is 100 or 200. Sort of dark is 400. Dark is 800 max.
                    # available options: 100, 200, 320, 400, 500, 640, 800
	
#############################
### Variables that Change ###
#############################
# Do not change these variables, as the code will change it anyway
transform_x = monitor_w # how wide to scale the jpg when replaying
transfrom_y = monitor_h # how high to scale the jpg when replaying
offset_x = 0 # how far off to left corner to display photos
offset_y = 0 # how far off to left corner to display photos
replay_delay = 1 # how much to wait in-between showing pics on-screen after taking
replay_cycles = 1 # how many times to show each photo on-screen after taking

####################
### Other Config ###
####################
real_path = os.path.dirname(os.path.realpath(__file__))

# GPIO setup
GPIO.setmode(GPIO.BOARD)
GPIO.setup(led_pin,GPIO.OUT) # LED
GPIO.setup(btn_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.output(led_pin,False) #for some reason the pin turns on at the beginning of the program. Why?

# initialize pygame
pygame.init()
pygame.display.set_mode((monitor_w, monitor_h))
screen = pygame.display.get_surface()
pygame.display.set_caption('Photo Booth Pics')
pygame.mouse.set_visible(False) #hide the mouse cursor
pygame.display.toggle_fullscreen()

# Load the background template
bgimage = PIL.Image.open(real_path + "/background.png")

#################
### Functions ###
#################

# clean up running programs as needed when main program exits
def cleanup():
  print('Ended abruptly')
  pygame.quit()
  GPIO.cleanup()
atexit.register(cleanup)

# A function to handle keyboard/mouse/device input events    
def input(events):
    for event in events:  # Hit the ESC key to quit the slideshow.
        if (event.type == pygame.QUIT or
            (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE)):
            pygame.quit()


# set variables to properly display the image on screen at right ratio
def set_demensions(img_w, img_h):
    # connect to global vars
    global transform_y, transform_x, offset_y, offset_x

    # based on output screen resolution, calculate how to display
    ratio_h = (monitor_w * img_h) / img_w 

    if (ratio_h < monitor_h):
        #Use horizontal black bars
        #print "horizontal black bars"
        transform_y = ratio_h
        transform_x = monitor_w
        offset_y = (monitor_h - ratio_h) / 2
        offset_x = 0
    elif (ratio_h > monitor_h):
        #Use vertical black bars
        #print "vertical black bars"
        transform_x = (monitor_h * img_w) / img_h
        transform_y = monitor_h
        offset_x = (monitor_w - transform_x) / 2
        offset_y = 0
    else:
        #No need for black bars as photo ratio equals screen ratio
        #print "no black bars"
        transform_x = monitor_w
        transform_y = monitor_h
        offset_y = offset_x = 0

    # uncomment these lines to troubleshoot screen ratios
#     print str(img_w) + " x " + str(img_h)
#     print "ratio_h: "+ str(ratio_h)
#     print "transform_x: "+ str(transform_x)
#     print "transform_y: "+ str(transform_y)
#     print "offset_y: "+ str(offset_y)
#     print "offset_x: "+ str(offset_x)

# display one image on screen
def show_image(image_path):

	# clear the screen
	screen.fill((0,0,0))

	# load the image
	img = pygame.image.load(image_path)
	img = img.convert() 

	# set pixel dimensions based on image
	set_demensions(img.get_width(), img.get_height())

	# rescale the image to fit the current display
	img = pygame.transform.scale(img, (transform_x,transfrom_y))
	screen.blit(img,(offset_x,offset_y))
	pygame.display.flip()

# display a blank screen
def clear_screen():
	screen.fill( (0,0,0) )
	pygame.display.flip()

# display a group of images
def display_pics(base_file_name):
    for i in range(0, replay_cycles): #show pics a few times
		for i in range(1, num_pics_to_take+1): #show each pic
			show_image(config.file_path + base_file_name + "-" + str(i) + ".jpg")
			time.sleep(replay_delay) # pause

def combine_pics(base_file_name):
	try:
		for i in range(1, num_pics_to_take+1):
			image = PIL.Image.open(config.file_path + base_file_name + "-" + str(i) + "-sm.jpg")
			if i == 1:
				bgimage.paste(image, (25, 25))
			if i == 2:
				bgimage.paste(image, (650, 25))
			if i == 3:
				bgimage.paste(image, (25, 500))
			if i == 4:
				bgimage.paste(image, (650, 500))

		filename = config.file_path + base_file_name + '-combined.jpg'
		bgimage.save(filename)
		return filename
	except Exception, e:
		tb = sys.exc_info()[2]
		traceback.print_exception(e.__class__, e, tb)
		pygame.quit()

def display_header_text(text):
	font = pygame.font.Font(None, 100)
	text = font.render(text, 1, (127, 127, 127))
	textpos = text.get_rect()
	textpos.centerx = screen.get_rect().centerx
	textpos.centery = 60
	screen.blit(text, textpos)
	pygame.display.flip()
	
def display_countdown_number(number):
	font = pygame.font.Font(None, 800)
	text = font.render(str(number), 1, (127, 127, 127))
	textpos = text.get_rect()
	textpos.centerx = screen.get_rect().centerx
	textpos.centery = screen.get_rect().centery
	screen.blit(text, textpos)
	pygame.display.flip()

# define the photo taking function for when the big button is pressed 
def start_photobooth(): 

	input(pygame.event.get()) # press escape to exit pygame. Then press ctrl-c to exit python.

	################################# Begin Step 1 #################################
	
	print "Get Ready"
	GPIO.output(led_pin,False);
	show_image(real_path + "/instructions.png")
	sleep(prep_delay)
	
	clear_screen()
	
	camera = picamera.PiCamera(sensor_mode=2)
	camera.vflip = False
	camera.hflip = True # flip for preview, showing users a mirror image
	#camera.saturation = -100 # comment out this line if you want color images
	camera.iso = camera_iso
	
	#pixel_width = 0 # local variable declaration
	#pixel_height = 0 # local variable declaration
	
	preview_window_x = (monitor_w - preview_image_w) / 2
	preview_window_y = (monitor_h - preview_image_h) / 2
	
	
		
	################################# Take the photos #################################
	
	print "Taking pics"
	
	base_file_name = time.strftime("%H-%M-%S") #get the current date and time for the start of the filename
	

	try: # take the photos
		for i in range(1,num_pics_to_take+1):
			camera.hflip = True # preview a mirror image
			
			#display_header_text("Get ready")
			
			# Turn on the camera preview overlay
			camera.resolution = (preview_image_w, preview_image_h)
			camera.start_preview(fullscreen=False,window=(preview_window_x, preview_window_y, preview_image_w, preview_image_h))
			camera.preview.alpha = 200
			
			for countdown in range(countdown_seconds, 0, -1):
				display_countdown_number(countdown)
				time.sleep(1)
				clear_screen()
			
			GPIO.output(led_pin,True) #turn on the LED
			
			camera.stop_preview()
			
			screen.fill(pygame.Color("white"))
			pygame.display.flip()
			
			filename = config.file_path + base_file_name + '-' + str(i) + '.jpg'
			camera.hflip = False # flip back when taking photo
			camera.resolution = (high_res_w, high_res_h)
			camera.capture(filename)
			#camera.capture(filename, resize=(high_res_w, high_res_h))
			print(filename)
			
			screen.fill(pygame.Color("black"))
			pygame.display.flip()
			
			GPIO.output(led_pin,False) #turn off the LED
			
			#show_image(real_path + "/pose" + str(i) + ".png")
			#show_image(filename)
			#time.sleep(capture_delay) # pause in-between shots
			
			clear_screen()
			
			show_image(filename)
			display_header_text("You look great!")
			time.sleep(2)
			clear_screen()
				
			if i < num_pics_to_take:
				display_header_text("Get ready for the next one!")
				#time.sleep(2)
				#clear_screen()
	finally:
		camera.close()

		
	########################### Produce the combined images #################################
	
	input(pygame.event.get()) # press escape to exit pygame. Then press ctrl-c to exit python.
	
	print "Creating an animated gif" 
	
	show_image(real_path + "/processing.png")
	
	# Make a small version of the images
	for x in range(1, num_pics_to_take+1): #batch process all the images
		graphicsmagick = "gm convert -size 600x450 " + config.file_path + base_file_name + "-" + str(x) + ".jpg -thumbnail 600x450 " + config.file_path + base_file_name + "-" + str(x) + "-sm.jpg"
		os.system(graphicsmagick) #do the graphicsmagick action
	
	# Allow a moment for the small images to create before we use them
	time.sleep(1)
				
	if make_gifs: # make the gifs
		graphicsmagick = "gm convert -delay " + str(gif_delay) + " " + config.file_path + base_file_name + "-*-sm.jpg " + config.file_path + base_file_name + ".gif" 
		os.system(graphicsmagick) #make the .gif

	# Combine the images into a grid image
	filename = combine_pics(base_file_name)
	show_image(filename)
	time.sleep(time_to_display_final_image)
	
	# Delete the small images
	try:
		for x in range(1, num_pics_to_take + 1):
			os.remove(config.file_path + base_file_name + "-" + str(x) + "-sm.jpg")
	except Exception, e:
		print "Error deleting thmbnails"
		tb = sys.exc_info()[2]
		traceback.print_exception(e.__class__, e, tb)
		
	########################### Finished #################################
	
	input(pygame.event.get()) # press escape to exit pygame. Then press ctrl-c to exit python.
	
	#try:
	#	display_pics(base_file_name)
	#except Exception, e:
	#	tb = sys.exc_info()[2]
	#	traceback.print_exception(e.__class__, e, tb)
	#	pygame.quit()
		
	print "Done"
	
	#show_image(real_path + "/finished2.png")
	
	show_image(real_path + "/intro.png");
	GPIO.output(led_pin,True) #turn on the LED

def wait_for_start():
	global pygame
	while True:
		channel = GPIO.wait_for_edge(btn_pin, GPIO.FALLING, timeout=500)
		if channel is not None:
			# Button press
			return
	    	#input_state = GPIO.input(btn_pin)
	    	#if input_state == False:		
		#	return
		for event in pygame.event.get():			
			if event.type == pygame.KEYDOWN:
				if event.key == pygame.K_ESCAPE:
					pygame.quit()
				if event.key == pygame.K_DOWN:
					return
		time.sleep(0.2)
	
####################
### Main Program ###
####################


print "Photo booth app running..." 
for x in range(0, 2): #blink light to show the app is running
	GPIO.output(led_pin,True)
	sleep(0.25)
	GPIO.output(led_pin,False)
	sleep(0.25)

show_image(real_path + "/intro.png");

while True:
	GPIO.output(led_pin,True); #turn on the light showing users they can push the button
	input(pygame.event.get()) # press escape to exit pygame. Then press ctrl-c to exit python.
	
	wait_for_start()
	
	#GPIO.wait_for_edge(btn_pin, GPIO.FALLING)
	#time.sleep(config.debounce) #debounce
	start_photobooth()
