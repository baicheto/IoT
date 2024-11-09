#import necessary libraries
import Adafruit_DHT
import BlynkLib
import RPi.GPIO as GPIO
from BlynkTimer import BlynkTimer
import time

sensor = Adafruit_DHT.DHT11
pin = 17 #change the pin if you're using other
BlYNK_TOKEN = "change with your own unique token" 

blynk = BlynkLib.Blynk(BlYNK_TOKEN)

timer = BlynkTimer()

@blynk.on("connected")
def blynk_connected():
    print("Now you're connected to BLynk")
    time.sleep(5) #wait for 5s

#function to read the data from the DHT sensor
def data():
    humidity, temperature= Adafruit_DHT.read(sensor, pin)
    if humidity is not None and temperature is not None:
        print("Temperature = {0:0.1f}C | Humidity = {1:0.1f}%". format(temperature, humidity))
    else:
        print("Error occurred")
        print("Check connection")

    #assign the values to the virtual pins
    blynk.virtual_write(0, humidity)
    blynk.virtual_write(1, temperature)

timer.set_interval(5, data)

while True:
    blynk.run() #start blynk
    timer.run()