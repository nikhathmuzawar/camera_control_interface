from fastapi import FastAPI, Request,  WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer
import uvicorn
from valkka.onvif import OnVif, DeviceManagement

IP = "192.168.144.100"
PORT = 8000
USER = ""
PASSWORD = ""

class MyDeviceIO(OnVif):
    wsdl_file = "https://www.onvif.org/ver10/deviceio.wsdl"
    namespace = "http://www.onvif.org/ver10/deviceIO/wsdl"
    sub_xaddr = "DeviceIO"
    port = "DeviceIOBinding"


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Init ONVIF services
device_service = DeviceManagement(ip=IP, port=PORT, user=USER, password=PASSWORD)
deviceIO_service = MyDeviceIO(ip=IP, port=PORT, user=USER, password=PASSWORD)
deviceio_type_factory = deviceIO_service.zeep_client.type_factory(
    "http://www.onvif.org/ver10/deviceIO/wsdl"
)
ports = deviceIO_service.ws_client.GetSerialPorts()
serial_token = ports[0].token


def send_visca_command(hex_str):
    serial_data = deviceio_type_factory.SerialData(Binary=bytes.fromhex(hex_str))
    resp = deviceIO_service.ws_client.SendReceiveSerialCommand(
        Token=serial_token,
        SerialData=serial_data,
        TimeOut="PT0M6S",
        DataLength="100",
        Delimiter="",
    )
    return resp["Binary"].hex()

ICR_COMMANDS = {
    "icr_off": "81 01 04 66 03 FF",
    "icr_night": "81 01 04 01 02 FF",
    "icr_day": "81 01 04 01 03 FF",
    "icr_auto": "81 01 04 51 02 FF",
    "icr_ext_in": "81 01 04 51 05 FF",
    "icr_burst_on": "81 01 04 72 02 FF",
    "icr_burst_off": "81 01 04 72 03 FF",
    "ir_detect_on": "81 01 04 6E 02 FF",
    "ir_detect_off": "81 01 04 6E 03 FF"
}

@app.post("/icr/{command}")
async def icr_command(command: str):
    if command not in ICR_COMMANDS:
        return {"status": "error", "message": "Unknown ICR command"}
    resp = send_visca_command(ICR_COMMANDS[command])
    return {"status": "ok", "resp": resp}


FOCUS_COMMANDS = {
    "stop_focus": "81 01 04 08 00 FF",
    "far_standard": "81 01 04 08 02 FF",
    "near_standard": "81 01 04 08 03 FF",
    "far_variable": "81 01 04 08 20 FF",   
    "near_variable": "81 01 04 08 30 FF",  
    "auto_focus": "81 01 04 38 02 FF",
    "manual_focus": "81 01 04 38 03 FF",
    "auto_manual_focus": "81 01 04 38 10 FF",
    "one_push_trigger": "81 01 04 18 01 FF",
    "infinity_focus": "81 01 04 18 02 FF",
    "normal_af_mode": "81 01 04 57 00 FF",
    "interval_af_mode": "81 01 04 57 01 FF",
    "zoom_trigger_af": "81 01 04 57 02 FF"
}

@app.post("/digital_zoom")
async def set_digital_zoom(request: Request):
    data = await request.json()
    on = data["on"]
    cmd = "81 01 04 06 02 FF" if on else "81 01 04 06 03 FF"
    resp = send_visca_command(cmd)
    return {"status": "ok", "resp": resp}


@app.post("/focus/{command}")
async def focus_command(command: str):
    if command not in FOCUS_COMMANDS:
        return {"status": "error", "message": "Unknown focus command"}
    resp = send_visca_command(FOCUS_COMMANDS[command])
    return {"status": "ok", "resp": resp}


@app.post("/zoom")
async def set_zoom(request: Request):
    data = await request.json()
    zoom_val = int(data["zoom"])
    p = (zoom_val >> 12) & 0x0F
    q = (zoom_val >> 8) & 0x0F
    r = (zoom_val >> 4) & 0x0F
    s = zoom_val & 0x0F

    cmd = f"81 01 04 47 0{p:X} 0{q:X} 0{r:X} 0{s:X} FF"
    resp = send_visca_command(cmd)
    return {"status": "ok", "resp": resp}


@app.post("/picture_flip")
async def set_picture_flip(request: Request):
    data = await request.json()
    on = data["on"]
    cmd = "81 01 04 66 02 FF" if on else "81 01 04 66 03 FF"
    resp = send_visca_command(cmd)
    return {"status": "ok", "resp": resp}


@app.post("/mirror_image")
async def set_mirror_image(request: Request):
    data = await request.json()
    on = data["on"]
    cmd = "81 01 04 61 02 FF" if on else "81 01 04 61 03 FF"
    resp = send_visca_command(cmd)
    return {"status": "ok", "resp": resp}


RTSP_URL = "rtsp://192.168.144.100:8554/quality_h264"

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html") as f:
        return f.read()

@app.post("/offer")
async def offer(request: Request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    pc = RTCPeerConnection()
    player = MediaPlayer(RTSP_URL, format="rtsp", options={
        "rtsp_transport": "tcp",
        "fflags": "nobuffer",
        "flags": "low_delay",
        "threads": "1",
        "framedrop": "1",
        "max_delay": "500000"
    })
    if player.video:
        pc.addTrack(player.video)
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return {
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    }

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)