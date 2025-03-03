#!/usr/bin/env python

import cups
from time import sleep

conn = cups.Connection()
printers = conn.getPrinters()
for printer in printers:
    print printer, printers[printer]["device-uri"]

printer_name = 'cp400'

conn.enablePrinter(printer_name)

# print conn.getPrinterAttributes(name=printer_name, requested_attributes=['printer-state-message', 'printer-is-accepting-jobs'])

for job_id in conn.getJobs():
    status = conn.getJobAttributes(job_id, requested_attributes=['job-printer-state-message', 'job-state'])
    if status['job-state'] == 3:
        print job_id, 'Waiting to print'
    elif status['job-state'] == 4:
        print job_id, status['job-printer-state-message']
    elif status['job-state'] == 5:
        print job_id, 'Printing'

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
        print 'Waiting in queue'
    else:
        print status['job-state']
    # print '.'
    sleep(5)

print 'Finished'

# job state
# 3 = pending
# 4 = pending-held
# 5 = processing
