import spidev
import cherrypy
import time
from time import sleep
from datetime import datetime


class ADC(object):
    # By using MSB and LSB-mode the functions below read MCP3201
    def __init__(self, SPI_BUS, CE_PIN):
        """
        starts the device, takes SPI bus address (always 0 on new Raspberry Pi models)
        and sets the channel to either CE0 = 0 (GPIO pin BCM 8) or CE1 = 1 (GPIO pin BCM 7)
        """
        if SPI_BUS not in [0, 1]:
            raise ValueError('wrong SPI-bus: {0} setting (use 0 or 1)!'.format(SPI_BUS))
        if CE_PIN not in [0, 1]:
            raise ValueError('wrong CE-setting: {0} setting (use 0 for CE0 or 1 for CE1)!'.format(CE_PIN))
        self._spi = spidev.SpiDev()
        self._spi.open(SPI_BUS, CE_PIN)
        self._spi.max_speed_hz = 976000
        pass

    def ADC_MSB(self):
        """
        Reads 2 bytes (byte_0 and byte_1) and converts the output code from the MSB-mode:
        byte_0 holds two bits, the null bit, and the 5 MSB bits (B11-B07),
        byte_1 holds the remaning 7 MBS bits (B06-B00) and B01 from the LSB-mode, which has to be removed.
        """
        bytes_received = self._spi.xfer2([0x00, 0x00])

        MSB_1 = bytes_received[1]
        MSB_1 = MSB_1 >> 1  # shift right 1 bit to remove B01 from the LSB mode

        MSB_0 = bytes_received[0] & 0b00011111  # mask the 2 unknown bits and the null bit
        MSB_0 = MSB_0 << 7  # shift left 7 bits (i.e. the first MSB 5 bits of 12 bits)

        return MSB_0 + MSB_1

    def ADC_LSB(self):
        """
        Reads 4 bytes (byte_0 - byte_3) and converts the output code from LSB format mode:
        byte 1 holds B00 (shared by MSB- and LSB-modes) and B01,
        byte_2 holds the next 8 LSB bits (B03-B09), and
        byte 3, holds the remaining 2 LSB bits (B10-B11).
        """
        bytes_received = self._spi.xfer2([0x00, 0x00, 0x00, 0x00])

        LSB_0 = bytes_received[1] & 0b00000011  # mask the first 6 bits from the MSB mode
        LSB_0 = bin(LSB_0)[2:].zfill(2)  # converts to binary, cuts the "0b", include leading 0s

        LSB_1 = bytes_received[2]
        LSB_1 = bin(LSB_1)[2:].zfill(8)  # see above, include leading 0s (8 digits!)

        LSB_2 = bytes_received[3]
        LSB_2 = bin(LSB_2)[2:].zfill(8)
        LSB_2 = LSB_2[0:2]  # keep the first two digits

        LSB = LSB_0 + LSB_1 + LSB_2  # concatenate the three parts to the 12-digits string
        LSB = LSB[::-1]  # invert the resulting string
        return int(LSB, base=2)

    def convert_to_voltage(self, adc_output, VREF=3.3):  # VREF can be changed
        # From the digital output code analogue voltage is calculated

        return adc_output * (VREF / (2 ** 12 - 1))

    def convert_to_percentages(self, adc_output):
        """
        Analogue voltage is calculated to percentages
        """
        value_p = adc_output / 4095 * 100
        value = round(value_p, 2)  # round to the 2 symbolf after the decimal point

        # if-else statements to check in which renage the measurment falls
        # a message with the value and condition is created
        if value_p == 100:
            condition = "% - Pitch Black"
            output = str(value) + condition
            return output

        elif value_p >= 90 and value_p < 100:
            condition = "% - Twilight"
            output = str(value) + condition
            return output

        elif value_p >= 80 and value_p < 90:
            condition = "% - Moonlight"
            output = str(value) + condition
            return output

        elif value_p >= 70 and value_p < 80:
            condition = "% - Dawn"
            output = str(value) + condition
            return output

        elif value_p >= 60 and value_p < 70:
            condition = "% - Dim Light"
            output = str(value) + condition
            return output

        elif value_p >= 50 and value_p < 60:
            condition = "% - Soft Glow"
            output = str(value) + condition
            return output

        elif value_p >= 40 and value_p < 50:
            condition = "% - Moderate Light"
            output = str(value) + condition
            return output

        elif value_p >= 30 and value_p < 40:
            condition = "% - Bright Daylight"
            output = str(value) + condition
            return output

        elif value_p >= 20 and value_p < 30:
            condition = "% - Vibrant Light"
            output = str(value) + condition
            return output

        elif value_p >= 10 and value_p < 20:
            condition = "% - Intense Illumination"
            output = str(value) + condition
            return output

        elif value_p >= 0 and value_p < 10:
            condition = "% - Blazing Radiance"
            output = str(value) + condition
            return output

    # decorator
    @cherrypy.expose
    def index(self):  # this function creates a web page by using html
        ADC_output_code = self.ADC_MSB()
        ADC_percentages = self.convert_to_percentages(ADC_output_code)
        return """
               <!DOCTYPE html>
                <html lang="en">

                <head>
                    <title>Dashboard</title>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.1.0/css/bootstrap.min.css">
                    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
                    <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.0/umd/popper.min.js"></script>
                    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.1.0/js/bootstrap.min.js"></script>
                    <style>
                        .element-box {
                            border-radius: 10px;
                            border: 4px solid #fff192;
                            padding: 20px;
                        }

                        .card {
                            width: 500px;
                        }

                        .col {
                            margin: 10px;
                        }
                    </style>
                </head>

                <body>
                    <div class="container">
                        <br/>
                        <div class="card bg-info text-white card border-warning">
                            <div class="card-header">
                                <h3>Light Intensity 
                                </h3></div>
                             <div class="card-body">
                                <div class="row">
                                    <div class="col element-box">
                                        <h5>Percentage</h5>
                                        <p>""" + ADC_percentages + """</p>      
                                    </div>
                                </div>
                            </div>
                            <div class="card-footer"><p>""" + str(datetime.now()) + """</p></div>
                        </div>
                    </div>
                </body>

                </html>
               """


if __name__ == '__main__':
    SPI_bus = 0
    CE = 0
    ADC = ADC(SPI_bus, CE)

    cherrypy.config.update({'server.socket_host': '0.0.0.0'})
    cherrypy.quickstart(ADC)

    try:
        while True:
            ADC_output_code = ADC.ADC_MSB()
            ADC_voltage = ADC.convert_to_voltage(ADC_output_code)
            print("ADC output code (MSB-mode): %d" % ADC_output_code)
            print("ADC voltage: %0.2f V" % ADC_voltage)

            ADC_percentages = ADC.convert_to_percentages(ADC_output_code)

            # if-else statements to check in which renage the measurment falls, printed on the console
            if ADC_percentages == 100:
                print("Light intensity percentage: %0.2f%%" % ADC_percentages)
                print("Pitch Black")

            elif ADC_percentages >= 90 and ADC_percentages < 100:
                print("Light intensity percentage: %0.2f%%" % ADC_percentages)
                print("Twilight")

            elif ADC_percentages >= 80 and ADC_percentages < 90:
                print("Light intensity percentage: %0.2f%%" % ADC_percentages)
                print("Moonlight")

            elif ADC_percentages >= 70 and ADC_percentages < 80:
                print("Light intensity percentage: %0.2f%%" % ADC_percentages)
                print("Dawn")

            elif ADC_percentages >= 60 and ADC_percentages < 70:
                print("Light intensity percentage: %0.2f%%" % ADC_percentages)
                print("Dim Light")

            elif ADC_percentages >= 50 and ADC_percentages < 60:
                print("Light intensity percentage: %0.2f%%" % ADC_percentages)
                print("Soft Glow")

            elif ADC_percentages >= 40 and ADC_percentages < 50:
                print("Light intensity percentage: %0.2f%%" % ADC_percentages)
                print("Moderate Light")

            elif ADC_percentages >= 30 and ADC_percentages < 40:
                print("Light intensity percentage: %0.2f%%" % ADC_percentages)
                print("Bright Daylight")

            elif ADC_percentages >= 20 and ADC_percentages < 30:
                print("Light intensity percentage: %0.2f%%" % ADC_percentages)
                print("Vibrant Light")

            elif ADC_percentages >= 10 and ADC_percentages < 20:
                print("Light intensity percentage: %0.2f%%" % ADC_percentages)
                print("Intense Illumination")

            elif ADC_percentages >= 0 and ADC_percentages < 10:
                print("Light intensity percentage: %0.2f%%" % ADC_percentages)
                print("Blazing Radiance")

            print()
            sleep(5)  # wait for 5s

    except (KeyboardInterrupt):
        print("Exit")

    except:
        print("Error or exception occurred!")
        raise

    finally:
        print()