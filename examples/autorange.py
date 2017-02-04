'''

  2017-02-04
  An example of auto-ranging and IR compensated
  color temperature calculation.

  Author: Ductsoup
  Credit: Tony DiCola
  License: Public Domain

  I2C Bus
  =============================================
  0x29      TCS34725 - RGB Color Sensor

  GPIO
  =============================================
  17 TCS34725 LED (output)

'''

import time
import sys
from datetime import datetime

'''

Setup the TCS34725 and add automatic gain control. We don't need
the breakout board LED so let's just turn that off for now.

'''

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

TCS34725_LED = 17
GPIO.setup(TCS34725_LED, GPIO.OUT)
GPIO.output(TCS34725_LED, GPIO.LOW)

import Adafruit_TCS34725

tcs_agc_lst = {
  0:{'gain': Adafruit_TCS34725.TCS34725_GAIN_60X, 'time': Adafruit_TCS34725.TCS34725_INTEGRATIONTIME_700MS, 'againx': 60, 'min':     0, 'max': 47566},
  1:{'gain': Adafruit_TCS34725.TCS34725_GAIN_16X, 'time': Adafruit_TCS34725.TCS34725_INTEGRATIONTIME_154MS, 'againx': 16, 'min':  3171, 'max': 63422},
  2:{'gain': Adafruit_TCS34725.TCS34725_GAIN_4X,  'time': Adafruit_TCS34725.TCS34725_INTEGRATIONTIME_154MS, 'againx':  4, 'min': 15855, 'max': 63422},
  3:{'gain': Adafruit_TCS34725.TCS34725_GAIN_1X,  'time': Adafruit_TCS34725.TCS34725_INTEGRATIONTIME_2_4MS, 'againx':  1, 'min':   248, 'max':     0}
  }
tcs_agc_cur = 3

tcs = Adafruit_TCS34725.TCS34725(gain=tcs_agc_lst[tcs_agc_cur]['gain'], integration_time=tcs_agc_lst[tcs_agc_cur]['time'])
tcs.set_interrupt(False)

'''

Function to get the raw data using automatic gain control

'''

def tcs_agc_get_raw_data():
  global tcs_agc_cur, tcs_agc_lst, tcs
  while True:
    r, g, b, c = tcs.get_raw_data()
    if (tcs_agc_lst[tcs_agc_cur]['max'] > 0 and c > tcs_agc_lst[tcs_agc_cur]['max']):
      ''' This porridge is too hot '''
      tcs_agc_cur += 1
    elif (tcs_agc_lst[tcs_agc_cur]['min'] > 0 and c < tcs_agc_lst[tcs_agc_cur]['min']):
      ''' This porridge is too cold '''
      tcs_agc_cur -= 1
    else:
      ''' This porridge is just right '''
      break;
    ''' The range changed so give the device time to find it's happy place then try again '''
    tcs.set_gain(tcs_agc_lst[tcs_agc_cur]['gain'])
    tcs.set_integration_time(tcs_agc_lst[tcs_agc_cur]['time'])
    time.sleep(1.5 * Adafruit_TCS34725.INTEGRATION_TIME_DELAY[tcs_agc_lst[tcs_agc_cur]['time']])

  return (r, g, b, c)

'''

Function to calculate the IR compensated lux and ct values

'''

def tcs_DN40(r, g, b, c):
  global tcs_agc_cur, tcs_agc_lst

  ''' Magic numbers from the DN40 application note '''
  TCS34725_R_Coef = 0.136
  TCS34725_G_Coef = 1.000
  TCS34725_B_Coef = -0.444
  TCS34725_GA = 1.0
  TCS34725_DF = 310.0
  TCS34725_CT_Coef = 3810.0
  TCS34725_CT_Offset = 1391.0

  ir = 0
  if (r + g + b > c):
    ir = (r + g + b - c) / 2
  r_comp = r - ir;
  g_comp = g - ir;
  b_comp = b - ir;
  c_comp = c - ir;

  againx = tcs_agc_lst[tcs_agc_cur]['againx']
  atime = int(tcs_agc_lst[tcs_agc_cur]['time'])
  atime_ms = ((256 - atime) * 2.4)
  cpl = (atime_ms * againx) / (TCS34725_GA * TCS34725_DF)

  lux = (TCS34725_R_Coef * float(r_comp) + TCS34725_G_Coef * float(g_comp) + TCS34725_B_Coef * float(b_comp)) / cpl
  ct = None
  if (lux > 0):
    ct = TCS34725_CT_Coef * float(b_comp) / float(r_comp) + TCS34725_CT_Offset;

  return (lux, ct)

'''

Main loop

'''
while True:
    r, g, b, c = tcs_agc_get_raw_data()
    lux, ct = tcs_DN40(r, g, b, c)
    print('TCS: red={0} green={1} blue={2} clear={3} lux={4} ct={5}'.format(r, g, b, c, int(lux), int(ct)))

    time.sleep(15.0)

