#!/usr/bin/env python

import os
import time
import traceback
from time import sleep
import RPi.GPIO as GPIO
import picamera
import atexit
import sys
import pygame
from signal import alarm, signal, SIGALRM, SIGKILL
import PIL.Image
import gphoto2 as gp
import random
from subprocess import call, Popen

####################
# Variables Config #
####################
# Pin numbers - BCM labeling
button_led_pin = 4  # LED
status_led_pin = 21  # red LED
button_pin = 24  # pin for the start button
ring_light_low_pin = 17  # the ring light
ring_light_high_pin = 18  # the ring light

file_path = '/home/pi/Pictures/'  # path to save images
photo_grid_file_path = file_path + 'photo_grid/'

# Timings
num_pics_to_take = 2  # number of pics to be taken
countdown_seconds = 5  # On screen visual countdown
# capture_delay = 3  # delay between pics
time_to_display_instructions = 3  # number of seconds to display instruction screen
time_to_display_image_after_capture = 0
time_to_display_photo_grid_image = 4  # How long should the final combined image display for
time_to_display_finished_screen = 3  # The final finished graphic should display for this long

# widescreen monitor 1920 x 1080
# small booth monitor 1024 x 768
monitor_w = 1024
monitor_h = 768

# Image ratio 4 x 3

# The live preview image shown to users
preview_image_w = 800
preview_image_h = 600

# Preview screen should be centered on the screen
preview_window_x = (monitor_w - preview_image_w) / 2
preview_window_y = (monitor_h - preview_image_h) / 2

# full frame of the camera is 3280x2464
high_res_w = 3280  # width of high res image
high_res_h = 2464  # height of high res image

make_gif = False
gif_delay = 20  # How much time between frames in the animated gif

make_photo_grid_image = True

camera_iso = 400    # adjust for lighting issues. Normal is 100 or 200. Sort of dark is 400. Dark is 800 max.
					# available options: 100, 200, 320, 400, 500, 640, 800

success_messages = [
	"Looking good!",
	"Wow! That's the money shot!",
	"FIT!!! ;-)",
	"What a smile!",
	"Have you considered being a model?!",
	"Amazing work!",
	"You're smashing it!",
	"Great job!",
	"B.E.A.UTIFL!",
	"That just took my breath away!",
	"The camera loves you!"
]

#########################
# Variables that Change #
#########################
# Do not change these variables, as the code will change it anyway
transform_x = monitor_w  # how wide to scale the jpg when replaying
transfrom_y = monitor_h  # how high to scale the jpg when replaying
offset_x = 0  # how far off to left corner to display photos
offset_y = 0  # how far off to left corner to display photos
replay_delay = 1  # how much to wait in-between showing pics on-screen after taking
replay_cycles = 1  # how many times to show each photo on-screen after taking
slr_camera = 0  # Are we using a proper camera to take photos


##################
# Config & Setup #
##################
real_path = os.path.dirname(os.path.realpath(__file__))

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(button_led_pin, GPIO.OUT)
GPIO.output(button_led_pin, False)
GPIO.setup(status_led_pin, GPIO.OUT)
GPIO.output(status_led_pin, False)
GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(ring_light_low_pin, GPIO.OUT)
GPIO.setup(ring_light_high_pin, GPIO.OUT)
GPIO.output(ring_light_low_pin, False)
GPIO.output(ring_light_high_pin, False)


# initialize pygame
pygame.init()
pygame.display.set_mode((monitor_w, monitor_h))
screen = pygame.display.get_surface()
pygame.display.set_caption('Photo Booth')
pygame.mouse.set_visible(False)  # hide the mouse cursor
pygame.display.toggle_fullscreen()

# Load the background template
bgimage = PIL.Image.open(real_path + "/background.png")


#############
# Functions #
#############


def text_hollow(font, message, fontcolor):
	notcolor = [c^0xFF for c in fontcolor]
	base = font.render(message, 0, fontcolor, notcolor)
	size = base.get_width() + 2, base.get_height() + 2
	img = pygame.Surface(size, 16)
	img.fill(notcolor)
	base.set_colorkey(0)
	img.blit(base, (0, 0))
	img.blit(base, (2, 0))
	img.blit(base, (0, 2))
	img.blit(base, (2, 2))
	base.set_colorkey(0)
	base.set_palette_at(1, notcolor)
	img.blit(base, (1, 1))
	img.set_colorkey(notcolor)
	return img


def text_outline(font, message, fontcolor, outlinecolor):
	base = font.render(message, 0, fontcolor)
	outline = text_hollow(font, message, outlinecolor)
	img = pygame.Surface(outline.get_size(), 16)
	img.blit(base, (1, 1))
	img.blit(outline, (0, 0))
	img.set_colorkey(0)
	return img


def setup_pi_camera():
	camera = picamera.PiCamera(sensor_mode=2)
	camera.vflip = False
	camera.hflip = True  # flip for preview, showing users a mirror image
	camera.iso = camera_iso
	return camera


def detect_slr_camera():
	global slr_camera
	slr_context = gp.Context()
	slr_camera = gp.Camera()
	try:
		slr_camera.init(slr_context)
		slr_camera = 1
	except gp.GPhoto2Error as ex:
		slr_camera = 0

	if slr_camera:
		print "SLR Camera connected"
		GPIO.output(status_led_pin, True)
	else:
		print "NO SLR Camera connected"
		GPIO.output(status_led_pin, False)


# clean up running programs as needed when main program exits
def cleanup():
	pygame.quit()
	GPIO.cleanup()


atexit.register(cleanup)


# A function to handle keyboard/mouse/device input events    
def input(events):
	for event in events:  # Hit the ESC key to quit the slideshow.
		if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
			pygame.quit()


# set variables to properly display the image on screen at right ratio
def set_dimensions(img_w, img_h):
	# connect to global vars
	global transform_y, transform_x, offset_y, offset_x

	# based on output screen resolution, calculate how to display
	ratio_h = (monitor_w * img_h) / img_w

	if ratio_h < monitor_h:
		# Use horizontal black bars
		transform_y = ratio_h
		transform_x = monitor_w
		offset_y = (monitor_h - ratio_h) / 2
		offset_x = 0
	elif ratio_h > monitor_h:
		# Use vertical black bars
		transform_x = (monitor_h * img_w) / img_h
		transform_y = monitor_h
		offset_x = (monitor_w - transform_x) / 2
		offset_y = 0
	else:
		# No need for black bars as photo ratio equals screen ratio
		transform_x = monitor_w
		transform_y = monitor_h
		offset_y = offset_x = 0


# display one image on screen
def show_image(image_path):

	# clear the screen
	screen.fill((0, 0, 0))

	# load the image
	img = pygame.image.load(image_path)
	img = img.convert()  # convert to a simple object that's quicker to work with

	# set pixel dimensions based on image
	set_dimensions(img.get_width(), img.get_height())

	# rescale the image to fit the current display
	img = pygame.transform.scale(img, (transform_x * 1, transform_y * 1))
	screen.blit(img, (offset_x, offset_y))
	pygame.display.flip()


# display a blank screen
def clear_screen():
	screen.fill((0, 0, 0))
	pygame.display.flip()


def combine_pics(photo_list, save_filename):
	try:
		i = 0
		for photo_path in photo_list:
			i = i + 1
			image = PIL.Image.open(photo_path)
			if i == 1:
				bgimage.paste(image, (25, 25))
			if i == 2:
				bgimage.paste(image, (650, 25))
			if i == 3:
				bgimage.paste(image, (25, 500))
			if i == 4:
				bgimage.paste(image, (650, 500))

		bgimage.save(save_filename)
	except Exception, e:
		tb = sys.exc_info()[2]
		traceback.print_exception(e.__class__, e, tb)
		pygame.quit()


def display_header_text(message):
	font = pygame.font.Font(None, 90)
	white = 255, 255, 255
	black = 50, 50, 50

	text = text_outline(font, message, white, black)
	# text = font.render(message, 1, (127, 127, 127))
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


# Capture images from both cameras and display
def start_slr_image_test():
	if not slr_camera:
		return
	GPIO.output(button_led_pin, False)
	clear_screen()
	show_image(real_path + "/processing.png")

	print "Testing slr camera"
	image_folder = file_path + "testing/" + time.strftime("%Y-%m-%d-%H-%M-%S") + "/"
	if not os.path.exists(image_folder):
		os.makedirs(image_folder)
	capture_photo_on_slr(wait=True)
	download_photos_from_slr(image_folder)
	delete_photos_from_slr()
	for slr_photo in os.listdir(image_folder):
		show_image(image_folder + "/" + slr_photo)

	wait_for_x()

	setup_intro_display()


def start_pi_cam_image_test():
	GPIO.output(button_led_pin, False)
	clear_screen()
	show_image(real_path + "/processing.png")

	print "Testing pi camera"
	camera = setup_pi_camera()
	try:
		camera.resolution = (preview_image_w, preview_image_h)
		camera.start_preview(fullscreen=False, window=(preview_window_x, preview_window_y, preview_image_w, preview_image_h))

		wait_for_x()

		camera.stop_preview()
	finally:
		camera.close()

	setup_intro_display()


def start_cam_comparison_test():
	if not slr_camera:
		return
	GPIO.output(button_led_pin, False)
	clear_screen()
	show_image(real_path + "/processing.png")

	print "Checking camera"

	image_folder = file_path + "testing/" + time.strftime("%Y-%m-%d-%H-%M-%S") + "/"
	if not os.path.exists(image_folder):
		os.makedirs(image_folder)

	camera = setup_pi_camera()
	try:
		camera.hflip = False
		camera.resolution = (preview_image_w, preview_image_h)
		camera.start_preview(fullscreen=False, window=(0, 0, monitor_w/2, monitor_h/2))

		capture_photo_on_slr(wait=True)
		download_photos_from_slr(image_folder)
		delete_photos_from_slr()

		for slr_photo in os.listdir(image_folder):
			show_image(image_folder + "/" + slr_photo)

		wait_for_x()

		camera.stop_preview()
	except Exception, e:
		camera.stop_preview()
	finally:
		camera.close()

	setup_intro_display()


def setup_intro_display():
	show_image(real_path + "/intro.png")
	GPIO.output(button_led_pin, True)


def wait_for_x():
	while True:
		for event in pygame.event.get():
			if event.type == pygame.KEYDOWN:
				if event.key == pygame.K_x:
					return
		time.sleep(0.2)


def capture_photo_on_slr(wait=True):
	slr_image_capture_process = Popen(["gphoto2", "--capture-image"])
	wait_count = 0
	if wait is True:
		if not isinstance(slr_image_capture_process, (int, bool)):
			while slr_image_capture_process.poll() is None:
				wait_count += 1
				time.sleep(1)
				if wait_count >= 10:
					slr_image_capture_process.kill()
					raise Exception("Waited to long capturing photos fom slr camera")
	else:
		return slr_image_capture_process


def download_photos_from_slr(image_folder):
	slr_image_capture_process = Popen(["gphoto2", "--get-all-files"], cwd=image_folder)
	wait_count = 0
	if not isinstance(slr_image_capture_process, (int, bool)):
		while slr_image_capture_process.poll() is None:
			wait_count += 1
			time.sleep(1)
			if wait_count >= 30:
				slr_image_capture_process.kill()
				raise Exception("Waited to long downloading photos fom slr camera")
	print "Downloaded all images from slr camera"


def delete_photos_from_slr():
	slr_image_capture_process = Popen(["gphoto2", "--delete-all-files", "--recurse"])
	wait_count = 0
	if not isinstance(slr_image_capture_process, (int, bool)):
		while slr_image_capture_process.poll() is None:
			wait_count += 1
			time.sleep(1)
			if wait_count >= 10:
				slr_image_capture_process.kill()
				raise Exception("Waited to long deleting photos from slr camera")
	print "Deleted all images from slr camera"


# define the photo taking function for when the big button is pressed 
def start_photobooth():

	# Display the instructions screen and prep the camera
	
	print "Get Ready"
	GPIO.output(button_led_pin, False)
	show_image(real_path + "/instructions.png")

	# Keep the camera status updated
	detect_slr_camera()

	sleep(time_to_display_instructions)
	
	clear_screen()

	camera = setup_pi_camera()
		
	# Take the photos
	
	print "Taking pics"

	# Increase the brightness of the might
	GPIO.output(ring_light_low_pin, False)
	GPIO.output(ring_light_high_pin, True)

	base_file_name = time.strftime("%Y-%m-%d-%H-%M-%S")  # get the current time for the start of the filename
	image_folder = file_path + base_file_name
	os.mkdir(image_folder)

	pi_cam_image_folder = image_folder + '/pi-cam/'
	os.mkdir(pi_cam_image_folder)

	slr_image_folder = None
	if slr_camera:
		slr_image_folder = image_folder + '/slr/'
		os.mkdir(slr_image_folder)

	slr_image_capture_process = False

	try:
		for i in range(1, num_pics_to_take+1):
			camera.hflip = True  # preview a mirror image
			
			# display_header_text("Get ready")
			
			# Turn on the camera preview overlay
			camera.resolution = (preview_image_w, preview_image_h)
			camera.start_preview(fullscreen=False, window=(preview_window_x, preview_window_y, preview_image_w, preview_image_h))
			# Semi transparent image so the countdown text shows through
			camera.preview.alpha = 200

			# Allow time for the video preview to start before we display the countdown
			time.sleep(0.5)

			# Display the countdown on screen
			for countdown in range(countdown_seconds, 0, -1):
				display_countdown_number(countdown)
				time.sleep(1)
				clear_screen()
			
			camera.stop_preview()

			# Flash the screen white to simulate the image being taken
			screen.fill(pygame.Color("white"))
			pygame.display.flip()

			if slr_camera:
				slr_image_capture_process = Popen(["gphoto2", "--capture-image"])
				time.sleep(0.5)  # A few extra moments are needed to ensure the shutter goes while the screen is white

			# reset the camera to full res and flip the image before taking a shot
			camera.hflip = False
			camera.resolution = (high_res_w, high_res_h)
			filename = pi_cam_image_folder + str(i) + '.jpg'
			camera.capture(filename)
			print(filename)

			# Go back to a black screen
			screen.fill(pygame.Color("black"))
			pygame.display.flip()

			# show_image(filename)
			# time.sleep(capture_delay) # pause in-between shots
			
			clear_screen()

			show_image(filename)
			display_header_text(random.choice(success_messages))

			if slr_camera:
				# Wait for image capture to complete
				if not isinstance(slr_image_capture_process, (int, bool)):
					while slr_image_capture_process.poll() is None:
						time.sleep(1)

			if time_to_display_image_after_capture:
				time.sleep(time_to_display_image_after_capture)

			clear_screen()
				
			if i < num_pics_to_take:
				display_header_text("Get ready for the next one!")
				# time.sleep(2)
				# clear_screen()
	finally:
		camera.close()

	# Turn down the light brightness
	GPIO.output(ring_light_low_pin, True)
	GPIO.output(ring_light_high_pin, False)

	# Produce the combined images
	
	print "Creating an animated gif" 
	
	show_image(real_path + "/processing.png")

	slr_photo_list = []
	slr_photo_list_small = []
	if slr_camera:
		try:
			download_photos_from_slr(slr_image_folder)
			delete_photos_from_slr()

			# call(["gphoto2", "--get-all-files"], cwd=image_folder)
			print "Downloaded the following images:"
			for slr_photo in os.listdir(slr_image_folder):
				print slr_photo
				slr_photo_list.append(slr_image_folder + slr_photo)
				graphicsmagick = "gm convert -size 600x450 " + slr_image_folder + slr_photo + " -thumbnail 600x450 " + slr_image_folder + slr_photo + "-" + "-sm.jpg"
				os.system(graphicsmagick)
				slr_photo_list_small.append(slr_image_folder + slr_photo + "-" + "-sm.jpg")

		except Exception, e:
			print "Error downloading photos from camera"
			tb = sys.exc_info()[2]
			traceback.print_exception(e.__class__, e, tb)
	
	# Make a small version of the pi cam images and move file names into arrays
	pi_cam_photo_list = []
	pi_cam_photo_list_small = []
	for i in range(1, num_pics_to_take + 1):
		pi_cam_photo_list.append(file_path + base_file_name + "-" + str(i) + ".jpg")
		if not slr_camera:
			graphicsmagick = "gm convert -size 600x450 " + pi_cam_image_folder + str(i) + ".jpg -thumbnail 600x450 " + pi_cam_image_folder + str(i) + "-sm.jpg"
			os.system(graphicsmagick)
			pi_cam_photo_list_small.append(pi_cam_image_folder + str(i) + "-sm.jpg")
				
	if make_gif:
		graphicsmagick = "gm convert -delay " + str(gif_delay) + " " + file_path + base_file_name + "-*-sm.jpg " + file_path + base_file_name + ".gif"
		os.system(graphicsmagick)

	if make_photo_grid_image:
		if slr_camera:
			photo_list = slr_photo_list_small
		else:
			photo_list = pi_cam_photo_list_small

		filename = photo_grid_file_path + base_file_name + '.jpg'
		combine_pics(photo_list, filename)
		show_image(filename)
		time.sleep(time_to_display_photo_grid_image)

	# Delete the small images
	try:
		if slr_camera:
			for photo_path in slr_photo_list_small:
				os.remove(photo_path)
		else:
			for photo_path in pi_cam_photo_list_small:
				os.remove(photo_path)
	except Exception, e:
		print "Error deleting thumbnails"
		tb = sys.exc_info()[2]
		traceback.print_exception(e.__class__, e, tb)
		
	# Finished

	if time_to_display_finished_screen > 0:
		show_image(real_path + "/finished.png")
		time.sleep(time_to_display_finished_screen)

	print "Done"

	setup_intro_display()


def wait_for_start():
	# global pygame
	while True:
		channel = GPIO.wait_for_edge(button_pin, GPIO.FALLING, timeout=500)
		if channel is not None:
			# Button press
			return
		for event in pygame.event.get():			
			if event.type == pygame.KEYDOWN:
				if event.key == pygame.K_ESCAPE:
					pygame.quit()
				if event.key == pygame.K_DOWN:
					return
				if event.key == pygame.K_1:
					start_pi_cam_image_test()
				if event.key == pygame.K_2:
					start_slr_image_test()
				if event.key == pygame.K_3:
					start_cam_comparison_test()
		time.sleep(0.2)
	
################
# Main Program #
################


print "Photo booth app starting..."

detect_slr_camera()

# Ensure the camera is in a clean and empty state
if slr_camera:
	delete_photos_from_slr()

for x in range(0, 2):  # blink light to show the app is running
	GPIO.output(button_led_pin, True)
	sleep(0.25)
	GPIO.output(button_led_pin, False)
	sleep(0.25)

print "Photo booth app ready..."

setup_intro_display()

while True:
	input(pygame.event.get())
	
	wait_for_start()
	
	# GPIO.wait_for_edge(button_pin, GPIO.FALLING)
	# time.sleep(0.3) #debounce
	start_photobooth()
