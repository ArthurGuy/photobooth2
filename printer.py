#!/usr/bin/env python

import cups
from time import sleep

conn = cups.Connection()
printers = conn.getPrinters()
for printer in printers:
    print printer, printers[printer]["device-uri"]

printer_name = 'cp400'

# print conn.getPrinterAttributes(name=printer_name, requested_attributes=['printer-state-message', 'printer-is-accepting-jobs'])

print conn.getJobs(requested_attributes=['job-printer-state-message', 'job-state'])

test_image = '/home/pi/photobooth/test.jpg'

job_id = conn.printFile(printer_name, test_image, "Photo Booth", {})
# Wait until the job finishes
print 'Printing'
while conn.getJobs().get(job_id, None):
    status = conn.getJobAttributes(job_id, requested_attributes=['job-printer-state-message', 'job-state'])
    if status['job-state'] == 5:
        print 'Processing'
    elif status['job-state'] == 4:
        # print 'Problem'
        print status['job-printer-state-message']
    elif status['job-state'] == 3:
        print 'Waiting in queue, printer on hold'
    else:
        print status['job-state']
    # print '.'
    sleep(5)

print 'Finished'

# job state
# 3 = pending
# 4 = pending-held
# 5 = processing
