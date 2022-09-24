import RPi.GPIO as GPIO
import logging
from random import randint
from sys import exit
from time import sleep
from timeit import default_timer as timer
from traceback import print_exc

from rak811.rak811_v3 import Rak811, Rak811ResponseError
dev_EUI='60C5A8FFFE79945B'
APP_EUI='70B3D57694768202'
APP_KEY = '52BC0034AE92AA283D40BB4120B5A65F'
logging.basicConfig(level=logging.INFO)

led_pin=29
GPIO.setmode(GPIO.BOARD)
GPIO.setup(led_pin, GPIO.OUT)

abc_list = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']
def hex_to_dec(number_as_string):
    try:
        number=abc_list.index(number_as_string.lower())
        return number
    except:
        print('bad character')
        return -1
#converts hex to decimal, returns an int, takes a string or list of strings as input
def convert_hex_to_dec(number_as_list_of_strings):
    if type(number_as_list_of_strings) is not list:
        if type(number_as_list_of_strings) is str:
            number_as_list_of_strings = list(number_as_list_of_strings)
        else:
            print('bad input to convert_to_dec')
            return -1
    length_lst=len(number_as_list_of_strings)
    sum_number=0
    for i in range(0, length_lst):
        inv=length_lst-i-1
        #print('inv: {} with number {}'.format(i, number_as_list_of_strings[inv]))
        temp_num=hex_to_dec(number_as_list_of_strings[inv])
        if temp_num<0:
            return -1
        sum_number+=16**i * temp_num
    return sum_number

def convert_incoming_to_list(hex_as_string):
    temp_list=[]
    n=len(hex_as_string)/2
    n=int(n)
    for i in range(0, n):
        temp_string=hex_as_string[i*2:i*2+2]
        temp_list.append(convert_hex_to_dec(temp_string))
    return temp_list

def decode_price_list(this_data):
    prices_decoded_1000=convert_incoming_to_list(this_data)
    prices_decoded=[]
    for element in prices_decoded_1000:
        prices_decoded.append(element/10000)
    return prices_decoded

#sends back the number 26
def ping():
    message = int(26).to_bytes(1, 'big')
    print('sending {} to server'.format(str(message)))
    lora.send(message)


def get_temp():
    return 25

def send_temperatur():
    message = int(24).to_bytes(1, 'big')
    temperature=get_temp()
    message+= int(temperature).to_bytes(1, 'big')
    print('sending {} to server'.format(str(message)))
    lora.send(message)

def get_meter_data(day):
    filname='day'+str(day)+'.txt'
    with open(filname) as f:
        my_list = list(f)

    meter_list=[]
    #sending as watthour
    for measurement in my_list:
        current_number=float(measurement.strip('\n'))
        as_wh=int(current_number*1000)
        meter_list.append(as_wh)
    if len(meter_list)<24 or len(meter_list)>24:
        print('length meter list is {}'.format(len(meter_list)))
    return meter_list

def metering():
    message = int(25).to_bytes(1, 'big')
    meter_data=get_meter_data()
    message+= int(meter_data).to_bytes(2, 'big')
    print('sending {} to server'.format(str(message)))
    lora.send(message)

def metering_entire_day(day):
    one_day_of_data =get_meter_data(day)
    print('length of list entire day data: {}'.format(len(one_day_of_data)))
    message = int(30).to_bytes(1, 'big')
    message += int(day).to_bytes(2, 'big')
    for hourr in one_day_of_data:
        message+=int(hourr).to_bytes(2, 'big')
    print('sending {} to server'.format(str(message)))
    lora.send(message)
    return 0

def metering_hour(day, hourr):
    one_day_of_data =get_meter_data(day)
    message = int(31).to_bytes(1, 'big')
    message += int(day).to_bytes(2, 'big')
    message += int(hourr).to_bytes(1, 'big')
    message += int(one_day_of_data[hourr]).to_bytes(2, 'big')
    print('sending {} to server'.format(str(message)))
    lora.send(message)
    return 0

def fortyfour_bytes():
    message=int(600).to_bytes(30, 'big')
    lora.send(message)
    return 0

def demand_response(bool_status):
    if bool_status:
        #turn off led
        print('Initiating demand response')
        GPIO.output(led_pin, GPIO.LOW)
    else:
        #turn on led
        print('Ending demand response')
        GPIO.output(led_pin, GPIO.HIGH)
    return 0

lora = Rak811()


print("Setup")
# Ensure we are in LoRaWan mode / Class C
lora.set_config("lora:work_mode:0")
lora.set_config("lora:class:2")
# Select OTAA
lora.set_config("lora:join_mode:0")
# Select region
lora.set_config("lora:region:EU868")
# Set keys
lora.set_config(f"lora:app_eui:{APP_EUI}")
lora.set_config(f"lora:app_key:{APP_KEY}")
# Set data rate
# Note that DR is different from SF and depends on the region
# See: https://docs.exploratory.engineering/lora/dr_sf/
# Set Data Rate to 5 which is SF7/125kHz for EU868
#"lora:dr:0" for spread factor 12, "lora:dr:2" for spread factor 10
lora.set_config("lora:dr:5")

# Print config
for line in lora.get_config("lora:status"):
    print(f"    {line}")

print("Joining")
start_time = timer()
lora.join()
print("Joined in {:.2f} secs".format(timer() - start_time))

print("Sending initial Hello packet")
start_time = timer()
message = int(111).to_bytes(1, 'big')
lora.send(message)
print("Packet sent in {:.2f} secs".format(timer() - start_time))
print("Entering wait loop")

try:
    loop_param=1
    while loop_param:
        print("Waiting for downlinks...")
        try:
            lora.receive_p2p(60)
        except Rak811ResponseError as e:
            print("Error while waiting for downlink {}: {}".format(e.errno, e.strerror))
        while lora.nb_downlinks:
            data = lora.get_downlink()["data"]
            if data != b"":
                print("Downlink received", data.hex())
                try:
                    data_as_hex=data.hex()
                    to_do=data_as_hex[0:2]
                        #1 pings back
                    if to_do=='01':
                        ping()
                        print('sent ping response')
                    elif to_do=='02':
                        fortyfour_bytes()
                        print('sent 44 bytes')
                    elif to_do=='03':
                        send_temperatur()
                        print('sent temperature response')
                    elif to_do=='04':
                        loop_param=0
                        print('shutting down script')
                    elif to_do=='05':
                        demand_response(True)
                        print('start demand response')
                    elif to_do=='06':
                        demand_response(False)
                        print('end demand response')
                    elif to_do=='14': #metering with day
                        day=convert_hex_to_dec(data_as_hex[2:6])
                        metering_entire_day(day)
                        print('sent one day of metering')
                    elif to_do=='15': #metering with day and hour
                        day=convert_hex_to_dec(data_as_hex[2:6])
                        hourr=convert_hex_to_dec(data_as_hex[6:8])
                        metering_hour(day, hourr)
                        print('send one hour of metering')
                    elif to_do=='10':
                        message = int(32).to_bytes(1, 'big')
                        print('sending {} to server'.format(str(message)))
                        lora.send(message)
                    elif to_do=='fa':
                        list_of_prices=decode_price_list(data_as_hex[1:49])
                        print('Todays prices are: ', end='')
                        print(list_of_prices)
                    else:
                        print('not valid command')
                except Rak811ResponseError as e:
                    print("Error while sendind data {}: {}".format(e.errno, e.strerror))


except KeyboardInterrupt:
    print()
except Exception:
    print_exc()

print("Cleaning up")
lora.close()
exit(0)