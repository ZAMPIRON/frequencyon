"""
Módulo de Reconhecimento Facial Nativo OpenCV (YuNet + SFace)
FrequencyON - Suporte a subpastas e múltiplas imagens por aluno.
"""

import cv2
import numpy as np
import os
import time
import urllib.request
from typing import Optional, Tuple, List

class FacialRecognitionService:
    def __init__(self, alunos_folder: str = "alunos_cadastrados"):
        self.alunos_folder = alunos_folder
        self.known_face_encodings: List[np.ndarray] = []
        self.known_face_names: List[str] = []
        self.known_face_ids: List[str] = []

        self.yunet_file = "face_detection_yunet_2023mar.onnx"
        self.sface_file = "face_recognition_sface_2021dec.onnx"
        self._garantir_modelos()

        # Limiar de detecção ajustado para 0.45 para melhorar precisão mobile
        self.detector = cv2.FaceDetectorYN.create(self.yunet_file, "", (320, 320), 0.45, 0.3, 5000)
        self.recognizer = cv2.FaceRecognizerSF.create(self.sface_file, "")

        self.recognition_cooldown = {}
        self.COOLDOWN_SECONDS = 300  # 5 minutos para registrar novamente no BD

        self.load_known_faces()

    def _garantir_modelos(self):
        """Baixa automaticamente os arquivos ONNX do OpenCV se não existirem."""
        if not os.path.exists(self.yunet_file):
            print("Downloading YuNet face detection model...")
            url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
            urllib.request.urlretrieve(url, self.yunet_file)

        if not os.path.exists(self.sface_file):
            print("Downloading SFace face recognition model...")
            url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
            urllib.request.urlretrieve(url, self.sface_file)

    def _extrair_encoding(self, image: np.ndarray) -> Optional[np.ndarray]:
        """Extrai o vetor numérico (embedding) do primeiro rosto encontrado na imagem."""
        if image is None:
            return None
        h, w, _ = image.shape
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(image)

        if faces is not None and len(faces) > 0:
            aligned_face = self.recognizer.alignCrop(image, faces[0])
            return self.recognizer.feature(aligned_face)
        return None

    def load_known_faces(self):
        """Carrega e codifica as fotos dos alunos (subpastas ou arquivos soltos)."""
        print("🔍 Carregando banco de faces dos alunos...")
        self.known_face_encodings.clear()
        self.known_face_names.clear()
        self.known_face_ids.clear()

        if not os.path.exists(self.alunos_folder):
            os.makedirs(self.alunos_folder)
            print(f"📁 Pasta '{self.alunos_folder}' criada.")
            return

        total_fotos = 0
        for item in os.listdir(self.alunos_folder):
            item_path = os.path.join(self.alunos_folder, item)

            # Caso 1: Subpasta por Aluno (ex: alunos_cadastrados/Joao_Silva/foto1.jpg)
            if os.path.isdir(item_path):
                aluno_nome = item.replace('_', ' ').title()
                aluno_id = item.lower().replace(' ', '_')
                fotos_carregadas = 0

                for filename in os.listdir(item_path):
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                        image_path = os.path.join(item_path, filename)
                        image = cv2.imread(image_path)
                        encoding = self._extrair_encoding(image)
                        if encoding is not None:
                            self.known_face_encodings.append(encoding)
                            self.known_face_names.append(aluno_nome)
                            self.known_face_ids.append(aluno_id)
                            fotos_carregadas += 1
                            total_fotos += 1

                if fotos_carregadas > 0:
                    print(f"  ✓ {aluno_nome} ({fotos_carregadas} foto(s) carregada(s))")

            # Caso 2: Imagem solta na raiz (ex: alunos_cadastrados/Maria_Oliveira.jpg)
            elif item.lower().endswith(('.jpg', '.jpeg', '.png')):
                image = cv2.imread(item_path)
                encoding = self._extrair_encoding(image)
                if encoding is not None:
                    aluno_nome = os.path.splitext(item)[0].replace('_', ' ').title()
                    aluno_id = aluno_nome.lower().replace(' ', '_')
                    self.known_face_encodings.append(encoding)
                    self.known_face_names.append(aluno_nome)
                    self.known_face_ids.append(aluno_id)
                    total_fotos += 1
                    print(f"  ✓ {aluno_nome} (foto avulsa)")

        unicos = len(set(self.known_face_ids))
        print(f"✅ Sucesso: {unicos} aluno(s) identificado(s) a partir de {total_fotos} foto(s).\n")

    def recognize_face(self, frame: np.ndarray) -> Optional[Tuple[str, str]]:
        """Compara o rosto da câmera com os vetores salvos e retorna (aluno_id, aluno_nome)."""
        if not self.known_face_encodings:
            return None

        frame_encoding = self._extrair_encoding(frame)
        if frame_encoding is None:
            return None

        best_score = -1.0
        best_match_index = -1

        for idx, known_encoding in enumerate(self.known_face_encodings):
            score = self.recognizer.match(frame_encoding, known_encoding, cv2.FaceRecognizerSF_FR_COSINE)
            if score > best_score:
                best_score = score
                best_match_index = idx

        # Limiar Cosine para o modelo SFace (0.363 é o padrão recomendado pela OpenCV)
        if best_score >= 0.363 and best_match_index != -1:
            return self.known_face_ids[best_match_index], self.known_face_names[best_match_index]

        return None

    def should_register_attendance(self, aluno_id: str) -> bool:
        """Controla o cooldown para não duplicar registros no banco a cada segundo."""
        current_time = time.time()
        if aluno_id in self.recognition_cooldown:
            if current_time - self.recognition_cooldown[aluno_id] < self.COOLDOWN_SECONDS:
                return False

        self.recognition_cooldown[aluno_id] = current_time
        return True