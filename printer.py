#!/usr/bin/env python

import cups
from time import sleep

conn = cups.Connection()
printers = conn.getPrinters()
for printer in printers:
    print printer, printers[printer]["device-uri"]

printer_name = 'cp400'

test_image = '/home/pi/photobooth/test.jpg'

print_id = conn.printFile(printer_name, test_image, "Photo Booth", {})
# Wait until the job finishes
print 'Printing'
while conn.getJobs().get(print_id, None):
    print conn.getJobs().get(print_id, None)
    print '.'
    sleep(5)

print 'Finished'
