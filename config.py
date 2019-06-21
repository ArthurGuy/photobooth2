
#Config settings to change behavior of photo booth
monitor_w = 800    # width of the display monitor
monitor_h = 480    # height of the display monitor
file_path = '/home/pi/Pictures/' # path to save images
clear_on_startup = False # True will clear previously stored photos as the program launches. False will leave all previous photos.
debounce = 0.3 # how long to debounce the button. Add more time if the button triggers too many times.
post_online = False # True to upload images. False to store locally only.
