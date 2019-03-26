#!/usr/bin/env python
import pika
import time
import datetime
import zlib

# start a connection with localhost
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# this is a queue named hello
channel.queue_declare(queue='hello')

# subscirbing callback func to queue, using the callback function to print message
# def callback(ch, method, properties, body):
#     print('received image of size: ' + str(len(body)))
#     with open('./img_received/outputimage' + str(time.time()) + '.jpg', 'wb') as f:
#     	f.write(zlib.decompress(body))

def callback(ch, method, properties, body):
	print('received message of', body)


channel.basic_consume(callback,
                      queue='hello',
                      no_ack=True)

    
print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()