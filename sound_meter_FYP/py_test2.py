import os, errno
import pyaudio
import spl_lib as spl
from scipy.signal import lfilter
import numpy
import pika
import time
from time import sleep
#import sys
import random
import cloud4rpi
# start a connection with localhost
DEVICE_TOKEN = '419CxuErk7dkg1oeKGX2bV783'
DATA_SENDING_INTERVAL = 10  # secs
DIAG_SENDING_INTERVAL = 15 # secs
POLL_INTERVAL = 1.0  # 500 ms
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
# this is a queue named hello
channel.queue_declare(queue='hello')



CHUNKS = [8192, 9600]       # originally for CD quality is 4096 but if it fails then put in more
CHUNK = CHUNKS[1]
FORMAT = pyaudio.paInt16    # 16 bit
CHANNEL = 1    # 1 for mono. 2 for stereo
STATUS = "HELLO"

RATES = [44300, 48000] #mic rates
RATE = RATES[1]

NUMERATOR, DENOMINATOR = spl.A_weighting(RATE)

def get_path(base, tail, head=''):
    return os.path.join(base, tail) if head == '' else get_path(head, get_path(base, tail)[1:])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#HTML_PATH = get_path(BASE_DIR, 'html/main.html', 'file:///')
SINGLE_DECIBEL_FILE_PATH = get_path(BASE_DIR, 'decibel_data/single_decibel.txt')
MAX_DECIBEL_FILE_PATH = get_path(BASE_DIR, 'decibel_data/max_decibel.txt')

# MIC LISTENING
pa = pyaudio.PyAudio()

stream = pa.open(format = FORMAT,
                channels = CHANNEL,
                rate = RATE,
                input = True,
                frames_per_buffer = CHUNK)


def is_meaningful(old, new):
    return abs(old - new) > 3

def update_text(path, content):
    try:
        f = open(path, 'w')
    except IOError as e:
        print(e)
    else:
        f.write(content)
        f.close()

def click(id):
    driver.find_element_by_id(id).click()

# def open_html(path):
#     driver.get(path)

def update_max_if_new_is_larger_than_max(new, max):
    print("update_max_if_new_is_larger_than_max called")
    if new > max:
        print("max observed")
        update_text(MAX_DECIBEL_FILE_PATH, 'MAX: {:.2f} dBA'.format(new))
        click('update_max_decibel')
        return new
    else:
        return max

def listen_for_events():
    old=0
    error_count=0
    min_decibel=100
    max_decibel=0

    while True:
        try:
            ## read() returns string which needs to convert into array.
            block = stream.read(CHUNK)
        except IOError as e:
            error_count += 1
            print(" (%d) Error recording: %s" % (error_count, e))
        else:
            decoded_block = numpy.fromstring(block, 'Int16')
            y = lfilter(NUMERATOR, DENOMINATOR, decoded_block)
            new_decibel = 20*numpy.log10(spl.rms_flat(y))
            if is_meaningful(old, new_decibel):
                old = new_decibel
                print('Decibel: {:+.2f} dB'.format(new_decibel))
                # print status according to decibel output
                if (new_decibel < 40):
                    STATUS = "LOW"
                elif(new_decibel<=70 ):
                    STATUS = "MEDIUM"
                else:
                    STATUS = "HIGH"
                print(STATUS)
                return STATUS
                time.sleep(2)

            #sending hello world with routing key which refers to queue
            # channel.basic_publish(exchange='',
            #                       routing_key='hello',
            #                       body=STATUS)
            # print(" [x] Sent", STATUS)
            # time.sleep(5)

    stream.stop_stream()
    stream.close()
    pa.terminate()

# def listen(old=0, error_count=0, min_decibel=100, max_decibel=0):
#     print("Listening")
#     while True:
#         try:
#             ## read() returns string which needs to convert into array.
#             block = stream.read(CHUNK)
#         except IOError as e:
#             error_count += 1
#             print(" (%d) Error recording: %s" % (error_count, e))
#         else:
#             decoded_block = numpy.fromstring(block, 'Int16')
#             y = lfilter(NUMERATOR, DENOMINATOR, decoded_block)
#             new_decibel = 20*numpy.log10(spl.rms_flat(y))
#             if is_meaningful(old, new_decibel):
#                 old = new_decibel
#                 print('Decibel: {:+.2f} dB'.format(new_decibel))
#                 # print status according to decibel output
#                 if (new_decibel < 40):
#                     STATUS = "LOW"
#                 elif(new_decibel<=70 ):
#                     STATUS = "MEDIUM"
#                 else:
#                     STATUS = "HIGH"
#                 print(STATUS)
#                 time.sleep(2)

#             #sending hello world with routing key which refers to queue
#             # channel.basic_publish(exchange='',
#             #                       routing_key='hello',
#             #                       body=STATUS)
#             # print(" [x] Sent", STATUS)
#             # time.sleep(5)

#     stream.stop_stream()
#     stream.close()
#     pa.terminate()

def listen():
    variables = {
       
        'STATUS': {
            'type': 'string',
            'bind': listen_for_events
        }
    }

    
    device = cloud4rpi.connect(DEVICE_TOKEN)

    # Use the following 'device' declaration
    # to enable the MQTT traffic encryption (TLS).
    #
    # tls = {
    #     'ca_certs': '/etc/ssl/certs/ca-certificates.crt'
    # }
    # device = cloud4rpi.connect(DEVICE_TOKEN, tls_config=tls)

    try:
        device.declare(variables)
       

        device.publish_config()

        # Adds a 1 second delay to ensure device variables are created
        sleep(1)

        data_timer = 0
        diag_timer = 0

        while True:
            if data_timer <= 0:
                device.publish_data()
                data_timer = DATA_SENDING_INTERVAL

            if diag_timer <= 0:
                device.publish_diag()
                diag_timer = DIAG_SENDING_INTERVAL

            sleep(POLL_INTERVAL)
            diag_timer -= POLL_INTERVAL
            data_timer -= POLL_INTERVAL

    except KeyboardInterrupt:
        cloud4rpi.log.info('Keyboard interrupt received. Stopping...')

    except Exception as e:
        error = cloud4rpi.get_error_message(e)
        cloud4rpi.log.exception("ERROR! %s %s", error, sys.exc_info()[0])

    finally:
        sys.exit(0)


if __name__ == '__main__':
    listen()
