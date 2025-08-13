# Simple example showing how to send and receive VISCA commands 
# to the HArrier IP.
# To install Valkka: https://valkka.readthedocs.io/en/latest/requirements.html

from valkka.onvif import OnVif, DeviceManagement
import time   

IP = "192.168.144.100"
PORT=8000

# The deviceio.wsdl included in Valkka is missing the 'Token' element 
# for SendReceiveSerialCommand(). 
# The class below uses https://www.onvif.org/ver10/deviceio.wsdl,
# which is correct.
class MyDeviceIO(OnVif):
    wsdl_file = "https://www.onvif.org/ver10/deviceio.wsdl"
    namespace = "http://www.onvif.org/ver10/deviceIO/wsdl"
    sub_xaddr = "DeviceIO"
    port      = "DeviceIOBinding"

if __name__ == '__main__':
   try:
      device_service = DeviceManagement(
      ip=IP,
      port=PORT,
      user="",
      password=""
      )

      deviceIO_service = MyDeviceIO(
        ip=IP,
        port=PORT,
        user="",
        password=""
      )

      deviceio_type_factory = deviceIO_service.zeep_client.type_factory("http://www.onvif.org/ver10/deviceIO/wsdl")

      ports = deviceIO_service.ws_client.GetSerialPorts()
      serial_token = ports[0].token

      zoom_tele = bytes.fromhex('81 01 04 07 02 FF')
      zoom_wide = bytes.fromhex('81 01 04 07 03 FF')

      print("Send zoom tele command")
      serial_data = deviceio_type_factory.SerialData(Binary=zoom_tele)
      resp = deviceIO_service.ws_client.SendReceiveSerialCommand(Token=serial_token, SerialData=serial_data, TimeOut='PT0M6S', DataLength='100', Delimiter='')
      print("Camera response: " + resp['Binary'].hex())

      time.sleep(3)

      print("Send zoom wide command")
      serial_data = deviceio_type_factory.SerialData(Binary=zoom_wide)
      resp = deviceIO_service.ws_client.SendReceiveSerialCommand(Token=serial_token, SerialData=serial_data, TimeOut='PT0M6S', DataLength='100', Delimiter='')
      print("Camera response: " + resp['Binary'].hex())

   except Exception as e:
      print(e)