#!/usr/bin/env python

import cups
from time import sleep

conn = cups.Connection()
printers = conn.getPrinters()
for printer in printers:
    print printer, printers[printer]["device-uri"]

printer_name = 'cp400'

conn.getPrinterAttributes(name=printer_name)

test_image = '/home/pi/photobooth/test.jpg'

job_id = conn.printFile(printer_name, test_image, "Photo Booth", {})
# Wait until the job finishes
print 'Printing'
while conn.getJobs().get(job_id, None):
    # print conn.getJobAttributes(job_id, requested_attributes=)
    print '.'
    sleep(5)

print 'Finished'
