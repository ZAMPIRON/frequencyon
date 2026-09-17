import cv2

# Tente mudar para 1 ou 2 se o valor 0 abrir uma tela preta
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# Força uma resolução padrão leve
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print("❌ Não foi possível acessar a câmera!")
else:
    print("✅ Câmera acessada com sucesso. Pressione 'q' para sair.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Falha ao ler frame da câmera.")
            break
        cv2.imshow("Teste Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()