import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
import spidev
from time import sleep


def send_email(subject, body):
    # change the email sender,receiver and password depending on what you are using
    email_sender = "youremail@mail.com"
    email_receiver = "youremail@mail.com"
    password = "yourpassword"

    msg = MIMEMultipart()
    msg['From'] = email_sender
    msg['To'] = email_receiver
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)  # change the server dependion on which mail you're using
        server.starttls()
        server.login(email_sender, password)
        text = msg.as_string()
        server.sendmail(email_sender, email_receiver, text)
        server.quit()
        print("The email was sent successfully.")

    except Exception as exception:
        print(f"Error occurred while sending email: {exception}")


class ADC(object):
    # By using MSB and LSB-mode the functions below read MCP3201
    def __init__(self, SPI_BUS, CE_PIN):
        """
        starts the device, takes SPI bus address (always 0 on new Raspberry Pi models)
        The channel is set to either CE0 = 0 (GPIO pin BCM 8) or CE1 = 1 (GPIO pin BCM 7)
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
        MSB_0 = MSB_0 << 7  # shift left 7 bits (the first MSB 5 bits of 12 bits)

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

        return value_p

    def convert_to_ppm(self, adc_output):
        """
        Analogue voltage is calculated to percentages and then
        converted to ppm (parts per million)
        """
        value_p = adc_output / 4095 * 100
        value_ppm = value_p * 4800 / 100

        return value_ppm


if __name__ == '__main__':
    SPI_bus = 0
    CE = 0
    ADC = ADC(SPI_bus, CE)
    account_sid = 'yoursid'  # change with your own unique sid
    auth_token = 'yourauthenticationtoken'  # change with your own unique token
    client = Client(account_sid, auth_token)

    try:
        while True:
            ADC_output_code = ADC.ADC_MSB()
            ADC_voltage = ADC.convert_to_voltage(ADC_output_code)
            ADC_percentages = ADC.convert_to_percentages(ADC_output_code)
            print("ADC output code (MSB-mode): %d" % ADC_output_code)
            print("ADC voltage: %0.2f V" % ADC_voltage)
            print("ADC percentage: %0.2f%%" % ADC_percentages)

            ADC_ppm = ADC.convert_to_ppm(ADC_output_code)

            # if-else statements to check the ppm range, based on that email and SMS will be sent
            if ADC_ppm == 5000:
                print("Gas ppm: %0.2f" % ADC_ppm)
                print("Headache, diziness and nausea in 45min; uncnsciousness in 2h!")

                email_subject = "Sensor data alert"
                email_body = "Sensor data: %0.2f ppm - Headache, diziness and nausea in 45min; uncnsciousness in 2h!" % ADC_ppm
                send_email(email_subject, email_body)

                message = client.messages.create(
                    body="Sensor data: %0.2f ppm - Immediately dangerous to life!" % ADC_ppm,
                    from_='yourtwilionumber',  # change the Twiolio number you're given
                    to='yourphonenumber'  # change with your phone number
                )
                print(message.sid)

            elif ADC_ppm >= 4521 and ADC_ppm < 5000:
                print("Gas ppm: %0.2f" % ADC_ppm)
                print("Headache, diziness and nausea in 45min; uncnsciousness in 2h!")

                email_subject = "Sensor data alert"
                email_body = "Sensor data: %0.2f ppm - Headache, diziness and nausea in 45min; uncnsciousness in 2h!" % ADC_ppm
                send_email(email_subject, email_body)

                message = client.messages.create(
                    body="Sensor data: %0.2f ppm - Headache, diziness and nausea in 45min; uncnsciousness in 2h!" % ADC_ppm,
                    from_='yourtwilionumber',
                    to='yourphonenumber'
                )
                print(message.sid)

            elif ADC_ppm >= 4041 and ADC_ppm < 4521:
                print("Gas ppm: %0.2f" % ADC_ppm)
                print("Headache, diziness and nausea in 45min; uncnsciousness in 2h!")

                email_subject = "Sensor data alert"
                email_body = "Sensor data: %0.2f ppm - Headache, diziness and nausea in 45min; uncnsciousness in 2h!" % ADC_ppm
                send_email(email_subject, email_body)

                message = client.messages.create(
                    body="Sensor data: %0.2f ppm - Headache, diziness and nausea in 45min; uncnsciousness in 2h!" % ADC_ppm,
                    from_='yourtwilionumber',
                    to='yourphonenumber'
                )
                print(message.sid)

            elif ADC_ppm >= 3561 and ADC_ppm < 4041:
                print("Gas ppm: %0.2f" % ADC_ppm)
                print("Headache and nausea after 1 to 2h. Life threatening after 3h!")

                email_subject = "Sensor data alert"
                email_body = "Sensor data: %0.2f ppm - Headache and nausea after 1 to 2h. Life threatening after 3h!" % ADC_ppm
                send_email(email_subject, email_body)

                message = client.messages.create(
                    body="Sensor data: %0.2f ppm - Headache and nausea after 1 to 2h. Life threatening after 3h!" % ADC_ppm,
                    from_='yourtwilionumber',
                    to='yourphonenumber'
                )
                print(message.sid)

            elif ADC_ppm >= 3081 and ADC_ppm < 3561:
                print("Gas ppm: %0.2f" % ADC_ppm)
                print("Headache and nausea after 1 to 2h. Life threatening after 3h!")

                email_subject = "Sensor data alert"
                email_body = "Sensor data: %0.2f ppm - Headache and nausea after 1 to 2h. Life threatening after 3h!" % ADC_ppm
                send_email(email_subject, email_body)

                message = client.messages.create(
                    body="Sensor data: %0.2f ppm - Headache and nausea after 1 to 2h. Life threatening after 3h!" % ADC_ppm,
                    from_='yourtwilionumber',
                    to='yourphonenumber'
                )
                print(message.sid)

            elif ADC_ppm >= 2601 and ADC_ppm < 3081:
                print("Gas ppm: %0.2f" % ADC_ppm)
                print("Headache and nausea after 1 to 2h. Life threatening after 3h!")

                email_subject = "Sensor data alert"
                email_body = "Sensor data: %0.2f ppm - Headache and nausea after 1 to 2h. Life threatening after 3h!" % ADC_ppm
                send_email(email_subject, email_body)

                message = client.messages.create(
                    body="Sensor data: %0.2f ppm - Headache and nausea after 1 to 2h. Life threatening after 3h!" % ADC_ppm,
                    from_='yourtwilionumber',
                    to='yourphonenumber'
                )
                print(message.sid)

            elif ADC_ppm >= 2121 and ADC_ppm < 2601:
                print("Gas ppm: %0.2f" % ADC_ppm)
                print("Headache and nausea after 1 to 2h. Life threatening after 3h!")

                email_subject = "Sensor data alert"
                email_body = "Sensor data: %0.2f ppm - Headache and nausea after 1 to 2h. Life threatening after 3h!" % ADC_ppm
                send_email(email_subject, email_body)

                message = client.messages.create(
                    body="Sensor data: %0.2f ppm - Headache and nausea after 1 to 2h. Life threatening after 3h!" % ADC_ppm,
                    from_='yourtwilionumber',
                    to='yourphonenumber'
                )
                print(message.sid)

            elif ADC_ppm >= 1641 and ADC_ppm < 2121:
                print("Gas ppm: %0.2f" % ADC_ppm)
                print("Should not be exposed. Possible headache in 2 to 3h!")

                email_subject = "Sensor data alert"
                email_body = "Sensor data: %0.2f ppm - Should not be exposed. Possible headache in 2 to 3h!" % ADC_ppm
                send_email(email_subject, email_body)

                message = client.messages.create(
                    body="Sensor data: %0.2f ppm - Should not be exposed. Possible headache in 2 to 3h!" % ADC_ppm,
                    from_='yourtwilionumber',
                    to='yourphonenumber'
                )
                print(message.sid)

            elif ADC_ppm >= 1161 and ADC_ppm < 1641:
                print("Gas ppm: %0.2f" % ADC_ppm)
                print("Should not be exposed. Possible headache in 2 to 3h!")

                email_subject = "Sensor data alert"
                email_body = "Sensor data: %0.2f ppm - Should not be exposed. Possible headache in 2 to 3h!" % ADC_ppm
                send_email(email_subject, email_body)

                message = client.messages.create(
                    body="Sensor data: %0.2f ppm - Should not be exposed. Possible headache in 2 to 3h!" % ADC_ppm,
                    from_='yourtwilionumber',
                    to='yourphonenumber'
                )
                print(message.sid)

            elif ADC_ppm >= 681 and ADC_ppm < 1161:
                print("Gas ppm: %0.2f" % ADC_ppm)
                print("Allowable for several hours")

                email_subject = "Sensor data alert"
                email_body = "Sensor data: %0.2f ppm - Allowable for several hours!" % ADC_ppm
                send_email(email_subject, email_body)

                message = client.messages.create(
                    body="Sensor data: %0.2f ppm - Allowable for several hours!" % ADC_ppm,
                    from_='yourtwilionumber',
                    to='yourphonenumber'
                )
                print(message.sid)

            elif ADC_ppm > 200 and ADC_ppm < 681:
                print("Gas ppm: %0.2f" % ADC_ppm)
                print("No adverse effects with 8h of exposure")

                email_subject = "Sensor data alert"
                email_body = "Sensor data: %0.2f ppm - No adverse effects with 8h of exposure!" % ADC_ppm
                send_email(email_subject, email_body)

                message = client.messages.create(
                    body="Sensor data: %0.2f ppm - No adverse effects with 8h of exposure!" % ADC_ppm,
                    from_='yourtwilionumber',
                    to='yourphonenumber'
                )
                print(message.sid)

            elif ADC_ppm == 200:
                print("Gas ppm: %0.2f" % ADC_ppm)
                print("Permissible exposure level")

                email_subject = "Sensor data alert"
                email_body = "Sensor data: %0.2f ppm - Permissible exposure level!" % ADC_ppm
                send_email(email_subject, email_body)

                message = client.messages.create(
                    body="Sensor data: %0.2f ppm - Permissible exposure level!" % ADC_ppm,
                    from_='yourtwilionumber',
                    to='yourphonenumber'
                )
                print(message.sid)

            print()
            sleep(5)  # wait for 5s

    except (KeyboardInterrupt):
        print("Exit")

    except:
        print("Error or exception occurred!")
        raise

    finally:
        print()