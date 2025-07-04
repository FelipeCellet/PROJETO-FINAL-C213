import customtkinter as ctk
import tkinter as tk
from paho.mqtt.client import Client

# === CONFIG ===
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

BROKER = "test.mosquitto.org"
TOPICO_RECEBER = "elevador/altura"
TOPICO_ENVIAR = "elevador/setpoint"
TOPICO_EMERGENCIA = "elevador/emergencia"
TOPICO_RESET = "elevador/emergencia/reset"

mapeamento_andares = {
    'T': 4, '1': 8, '2': 11,
    '3': 14, '4': 17, '5': 20,
    '6': 23, '7': 26, '8': 29
}

ultima_altura = None
setpoint_atual = None
botoes = {}
fila_andares = []
emergencia_ativa = False
piscar_estado = [False]

cronometro_ativo = False
segundos_passados = 0

def atualizar_cronometro():
    global segundos_passados
    if cronometro_ativo:
        segundos_passados += 1
        minutos = segundos_passados // 60
        segundos = segundos_passados % 60
        tempo_var.set(f"{minutos:02}:{segundos:02}")
        app.after(1000, atualizar_cronometro)

def piscar_botoes_emergencia():
    if not emergencia_ativa:
        for nome in botoes:
            if nome in fila_andares:
                botoes[nome].configure(border_color="red", fg_color="#ffe6e6")
            else:
                botoes[nome].configure(border_color="#888", fg_color="#dddddd")
        return
    cor = "red" if piscar_estado[0] else "#888"
    for botao in botoes.values():
        botao.configure(border_color=cor)
    piscar_estado[0] = not piscar_estado[0]
    app.after(500, piscar_botoes_emergencia)

def processar_proximo_da_fila():
    global setpoint_atual, cronometro_ativo, segundos_passados
    if fila_andares:
        nome = fila_andares[0]
        altura = mapeamento_andares[nome]
        setpoint_atual = altura
        client.publish(TOPICO_ENVIAR, str(altura), retain=True)
        cronometro_ativo = True
        segundos_passados = 0
        atualizar_cronometro()

def on_connect(client, userdata, flags, rc):
    client.subscribe(TOPICO_RECEBER)

def on_message(client, userdata, msg):
    global ultima_altura, setpoint_atual, cronometro_ativo
    try:
        altura_atual = float(msg.payload.decode())
        ultima_altura = altura_atual

        andar_atual = "-"
        for nome, altura in mapeamento_andares.items():
            if abs(altura_atual - altura) <= 1.0:
                andar_atual = nome
                break

        andar_var.set(f"{andar_atual}")

        if setpoint_atual is None or abs(altura_atual - setpoint_atual) < 0.5:
            movimento = "⏹️ PARADO"
            movimento_cor = "gray"
        elif altura_atual < setpoint_atual:
            movimento = "⬆️ SUBINDO"
            movimento_cor = "#007acc"
        else:
            movimento = "⬇️ DESCENDO"
            movimento_cor = "#e53935"

        movimento_var.set(movimento)
        movimento_label.configure(text_color=movimento_cor)
        direcao_label.configure(text=movimento.split()[0])

        if setpoint_atual is not None and abs(altura_atual - setpoint_atual) < 0.5:
            cronometro_ativo = False

            # Reset visual do botão do andar atendido
            for nome, altura in mapeamento_andares.items():
                if altura == setpoint_atual:
                    botoes[nome].configure(border_color="#888", fg_color="#dddddd")
                    break

            if fila_andares:
                fila_andares.pop(0)
                processar_proximo_da_fila()
            else:
                setpoint_atual = None

    except Exception as e:
        print("Erro:", e)

def enviar_setpoint(nome_andar):
    global fila_andares
    if nome_andar in mapeamento_andares and nome_andar not in fila_andares:
        fila_andares.append(nome_andar)
        botoes[nome_andar].configure(border_color="red", fg_color="#ffe6e6")
        if setpoint_atual is None:
            processar_proximo_da_fila()

def acionar_emergencia():
    global setpoint_atual, cronometro_ativo, emergencia_ativa
    setpoint_atual = None
    cronometro_ativo = False
    emergencia_ativa = True
    print("[INTERFACE] EMERGÊNCIA ACIONADA!")
    andar_var.set("-")
    movimento_var.set("🚨 EMERGÊNCIA")
    movimento_label.configure(text_color="red")
    direcao_label.configure(text="⛔")
    client.publish(TOPICO_EMERGENCIA, "true")
    piscar_botoes_emergencia()

def resetar_emergencia():
    global emergencia_ativa
    emergencia_ativa = False
    print("[INTERFACE] RESET enviado.")
    client.publish(TOPICO_RESET, "true")
    if fila_andares and setpoint_atual is None:
        processar_proximo_da_fila()

# MQTT setup
client = Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, 1883)
client.loop_start()

# INTERFACE
app = ctk.CTk()
app.title("Painel Villarta Estilizado")
app.geometry("320x700")
app.configure(fg_color="#f5f5f5")

andar_var = tk.StringVar(value="-")
movimento_var = tk.StringVar(value="⏹️ PARADO")
tempo_var = tk.StringVar(value="00:00")

ctk.CTkLabel(app, text="VILLARTA", font=("Segoe UI Black", 24), text_color="#222").pack(pady=(20, 0))
ctk.CTkLabel(app, text="elevadores", font=("Segoe UI", 14), text_color="#888").pack()
ctk.CTkLabel(app, text="CAPACIDADE 975kg\n13 PASSAGEIROS", font=("Times New Roman", 13), text_color="#333").pack(pady=10)

ctk.CTkLabel(app, text="Andar atual", font=("Segoe UI", 14), text_color="#444").pack(pady=(10, 2))
ctk.CTkLabel(app, textvariable=andar_var, font=("Segoe UI Black", 48), text_color="#003366").pack()

ctk.CTkLabel(app, text="Tempo da viagem", font=("Segoe UI", 14), text_color="#444").pack(pady=(10, 0))
ctk.CTkLabel(app, textvariable=tempo_var, font=("Segoe UI Black", 24), text_color="#555").pack(pady=(0, 10))

icones_frame = ctk.CTkFrame(app, fg_color="#f5f5f5")
icones_frame.pack(pady=10)



botao_alarme = ctk.CTkButton(icones_frame, text="🔔", font=("Segoe UI", 20),
                             width=40, height=40, corner_radius=20,
                             fg_color="#eeeeee", hover_color="#cccccc",
                             text_color="black", command=acionar_emergencia)
botao_alarme.grid(row=0, column=1, padx=5)

botao_reset = ctk.CTkButton(icones_frame, text="🔓", font=("Segoe UI", 20),
                            width=40, height=40, corner_radius=20,
                            fg_color="#eeeeee", hover_color="#cccccc",
                            text_color="black", command=resetar_emergencia)
botao_reset.grid(row=0, column=2, padx=5)

direcao_label = ctk.CTkLabel(icones_frame, text="⏹️", font=("Segoe UI", 24), text_color="gray")
direcao_label.grid(row=0, column=3)

movimento_label = ctk.CTkLabel(app, textvariable=movimento_var, font=("Segoe UI", 18), text_color="gray")
movimento_label.pack(pady=5)

frame_botoes = ctk.CTkFrame(app, fg_color="#f5f5f5")
frame_botoes.pack(pady=10)

andares_layout = [
    ["6", "7", "8"],
    ["3", "4", "5"],
    ["T", "1", "2"]
]
braille_simples = {
    "T": "⠚", "1": "⠁", "2": "⠃", "3": "⠉",
    "4": "⠙", "5": "⠑", "6": "⠋", "7": "⠛", "8": "⠓"
}

def criar_botao_redondo(parent, andar):
    frame = ctk.CTkFrame(parent, width=72, height=72, corner_radius=36,
                         fg_color="#dddddd", border_color="#888", border_width=2)
    frame.grid_propagate(False)

    label_numero = ctk.CTkLabel(frame, text=andar, font=("Consolas", 18, "bold"), text_color="#222")
    label_numero.place(relx=0.5, rely=0.25, anchor="center")

    braille_label = ctk.CTkLabel(frame, text=braille_simples.get(andar, ""),
                                 font=("Segoe UI Symbol", 18), text_color="#111")
    braille_label.place(relx=0.5, rely=0.7, anchor="center")

    def clique(e): enviar_setpoint(andar)
    frame.bind("<Button-1>", clique)
    label_numero.bind("<Button-1>", clique)
    braille_label.bind("<Button-1>", clique)

    return frame


for r, linha in enumerate(andares_layout):
    for c, label in enumerate(linha):
        btn = criar_botao_redondo(frame_botoes, label)
        btn.grid(row=r, column=c, padx=6, pady=6)
        botoes[label] = btn

ctk.CTkLabel(app, text="📞 (35) 62133 – 6115", font=("Segoe UI", 12), text_color="#333").pack(pady=20)

app.mainloop()
