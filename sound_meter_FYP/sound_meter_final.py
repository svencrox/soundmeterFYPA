#!/usr/bin/env python
import os, errno
import pyaudio
import spl_lib as spl
from scipy.signal import lfilter
import numpy
import time
import pika


CHUNKS = [4096, 4800]       # originally for CD quality is 4096 but if it fails then put in more
CHUNK = CHUNKS[1]
#CHUNK = 256
FORMAT = pyaudio.paInt16    # 16 bit
CHANNEL = 1    # 1 for mono. 2 for stereo
STATUS = "HELLO"

RATES = [44300, 48000] #mic rates
RATE = RATES[1]
#RATE = 44000

NUMERATOR, DENOMINATOR = spl.A_weighting(RATE)

# start a connection with localhost
credentials = pika.PlainCredentials('guest', 'guest')
connection = pika.BlockingConnection(pika.ConnectionParameters('172.17.9.74', 5672, '/', credentials))
channel = connection.channel()

# this is a queue named hello
channel.queue_declare('decibel')

def get_path(base, tail, head=''):
    return os.path.join(base, tail) if head == '' else get_path(head, get_path(base, tail)[1:])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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

def update_max_if_new_is_larger_than_max(new, max):
    print("update_max_if_new_is_larger_than_max called")
    if new > max:
        print("max observed")
        update_text(MAX_DECIBEL_FILE_PATH, 'MAX: {:.2f} dBA'.format(new))
        click('update_max_decibel')
        return new
    else:
        return max


def listen():
    old=0
    error_count=0
    min_decibel=100
    max_decibel=0
    print("Listening")
    while True:
        try:
            ## read() returns string which needs to convert into array.
            block = stream.read(CHUNK, exception_on_overflow = False)
        except IOError as e:
            error_count += 1
            print(" (%d) Error recording: %s" % (error_count, e))
        else:
            decoded_block = numpy.fromstring(block, 'Int16')
            y = lfilter(NUMERATOR, DENOMINATOR, decoded_block)
            new_decibel = 20*numpy.log10(spl.rms_flat(y))
            if is_meaningful(old, new_decibel):
                old = new_decibel
                channel.basic_publish(exchange='',
                          routing_key='decibel',
                          body=str(new_decibel))
                print('dB sent: ', str(new_decibel))
                # print('Decibel: {:+.2f} dB'.format(new_decibel))

                # print status according to decibel output
                #if (new_decibel < 40):
                #    STATUS = "LOW"
                #elif(new_decibel<=70 ):
                #    STATUS = "MEDIUM"
                #else:
                #    STATUS = "HIGH"
                #print(STATUS)
                time.sleep(2)


    stream.stop_stream()
    stream.close()
    pa.terminate()
    # close pika connection
    connection.close()



if __name__ == '__main__':
    listen()
