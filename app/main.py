from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
import cv2
import face_recognition
import numpy as np
import threading
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# URL do DVR
# dvr_url = 'rtsp://admin:jp121415@192.168.0.243:554/cam/realmonitor?channel=2&subtype=0'
dvr_url = 'rtsp://192.168.0.53:8554/live.sdp'

# Lista de pessoas na blacklist
blacklist = []
detected_people = []  # Lista para armazenar pessoas detectadas

# Modelo para adicionar pessoa na blacklist
class BlacklistPerson(BaseModel):
    name: str
    image_path: str

# Carrega e codifica uma imagem para adicionar à blacklist
def load_and_encode_image(image_path: str):
    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)
    if encodings:
        return encodings[0]
    else:
        raise Exception("Não foi possível detectar um rosto na imagem.")

# Função para capturar vídeo e realizar o reconhecimento em tempo real
def process_video():
    video_capture = cv2.VideoCapture(dvr_url)

    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Erro ao acessar o DVR.")
            break
        
        rgb_frame = frame[:, :, ::-1]
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for face_encoding in face_encodings:
            for person in blacklist:
                matches = face_recognition.compare_faces([person["face_encoding"]], face_encoding)
                if True in matches:
                    print(f"Alerta: {person['name']} detectado!")
                    detected_people.append(person["name"])  # Armazena o nome na lista de detectados

    video_capture.release()

# Endpoint para adicionar uma pessoa à blacklist
@app.post("/blacklist")
async def add_to_blacklist(person: BlacklistPerson):
    try:
        face_encoding = load_and_encode_image(person.image_path)
        blacklist.append({"name": person.name, "face_encoding": face_encoding})
        return {"message": f"{person.name} adicionada à blacklist."}
    except Exception as e:
        return {"error": str(e)}

# Endpoint para iniciar o reconhecimento facial em tempo real
@app.post("/start-recognition")
async def start_recognition(background_tasks: BackgroundTasks):
    if not hasattr(start_recognition, 'is_running') or not start_recognition.is_running:
        start_recognition.is_running = True
        threading.Thread(target=process_video, daemon=True).start()
        return {"message": "Reconhecimento facial em tempo real iniciado."}
    else:
        return {"message": "Reconhecimento facial já está em execução."}

# Endpoint para consultar pessoas detectadas
@app.get("/detected")
async def get_detected_people():
    return {"detected_people": detected_people}

# Endpoint para servir o HTML com a transmissão ao vivo
@app.get("/", response_class=HTMLResponse)
async def get_video_stream():
    return """
    <html>
        <head>
            <title>Transmissão de Vídeo</title>
        </head>
        <body>
            <h1>Transmissão de Vídeo ao Vivo</h1>
            <img src="/video_feed" alt="Video Feed">
            <h2>Pessoas Detectadas:</h2>
            <ul id="detected-list"></ul>
            <script>
                setInterval(async () => {
                    const response = await fetch('/detected');
                    const data = await response.json();
                    const list = document.getElementById('detected-list');
                    list.innerHTML = '';
                    data.detected_people.forEach(name => {
                        const li = document.createElement('li');
                        li.textContent = name;
                        list.appendChild(li);
                    });
                }, 1000); // Atualiza a lista a cada 1 segundo
            </script>
        </body>
    </html>
    """

# Endpoint para fornecer o fluxo de vídeo
@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

def generate_frames():
    video_capture = cv2.VideoCapture(dvr_url)
    
    while True:
        success, frame = video_capture.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    video_capture.release()
