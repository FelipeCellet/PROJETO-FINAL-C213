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

# === Cronômetro ===
cronometro_ativo = False
segundos_passados = 0

def atualizar_cronometro():
    global segundos_passados
    if cronometro_ativo:
        minutos = segundos_passados // 60
        segundos = segundos_passados % 60
        tempo_var.set(f"{minutos:02}:{segundos:02}")
        segundos_passados += 1
        app.after(1000, atualizar_cronometro)
    else:
        tempo_var.set("00:00")

# === Funções MQTT ===
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
            for nome, altura in mapeamento_andares.items():
                if altura == setpoint_atual:
                    botoes[nome].configure(border_color="#888", fg_color="#dddddd")
                    setpoint_atual = None
                    break

    except Exception as e:
        print("Erro:", e)

def enviar_setpoint(nome_andar):
    global setpoint_atual, cronometro_ativo, segundos_passados
    if nome_andar in mapeamento_andares:
        altura = mapeamento_andares[nome_andar]
        setpoint_atual = altura
        client.publish(TOPICO_ENVIAR, str(altura), retain=True)
        print(f"[ENVIADO] {nome_andar} → {altura}m")

        for nome in botoes:
            botoes[nome].configure(border_color="#888", fg_color="#dddddd")

        botoes[nome_andar].configure(border_color="red", fg_color="#ffe6e6")

        # Inicia cronômetro
        segundos_passados = 0
        cronometro_ativo = True
        atualizar_cronometro()

def acionar_emergencia():
    global setpoint_atual, cronometro_ativo
    setpoint_atual = None
    cronometro_ativo = False
    print("[INTERFACE] EMERGÊNCIA ACIONADA!")
    andar_var.set("—")
    movimento_var.set("🚨 EMERGÊNCIA")
    movimento_label.configure(text_color="red")
    direcao_label.configure(text="🚫")
    client.publish(TOPICO_EMERGENCIA, "true")

def resetar_emergencia():
    print("[INTERFACE] RESET enviado.")
    client.publish(TOPICO_RESET, "true")

# === MQTT ===
client = Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, 1883)
client.loop_start()

# === INTERFACE ===
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

# Relógio digital
ctk.CTkLabel(app, text="Tempo da viagem", font=("Segoe UI", 14), text_color="#444").pack(pady=(10, 0))
ctk.CTkLabel(app, textvariable=tempo_var, font=("Segoe UI Black", 24), text_color="#555").pack(pady=(0, 10))

# Ícones e botões
icones_frame = ctk.CTkFrame(app, fg_color="#f5f5f5")
icones_frame.pack(pady=10)

ctk.CTkLabel(icones_frame, text="⏪⏩", font=("Segoe UI", 20)).grid(row=0, column=0)

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

# Botões de andar
frame_botoes = ctk.CTkFrame(app, fg_color="#f5f5f5")
frame_botoes.pack(pady=10)

andares_layout = [
    ["6", "7", "8"],
    ["3", "4", "5"],
    ["T", "1", "2"]
]

braille_simples = {
    "T": "●", "1": "●", "2": "●●", "3": "●●",
    "4": "●●", "5": "●●", "6": "●●", "7": "●●", "8": "●●"
}

def criar_botao_redondo(parent, andar):
    frame = ctk.CTkFrame(parent, width=72, height=72, corner_radius=36,
                         fg_color="#dddddd", border_color="#888", border_width=2)
    frame.grid_propagate(False)

    label_numero = ctk.CTkLabel(frame, text=andar, font=("Consolas", 18, "bold"), text_color="#222")
    label_numero.place(relx=0.5, rely=0.25, anchor="center")

    canvas = tk.Canvas(frame, width=30, height=20, bg="#dddddd", highlightthickness=0)
    canvas.place(relx=0.5, rely=0.7, anchor="center")

    bolinhas = braille_simples.get(andar, "")
    if len(bolinhas) >= 1:
        canvas.create_oval(5, 5, 9, 9, fill="black", outline="")
    if len(bolinhas) >= 2:
        canvas.create_oval(15, 5, 19, 9, fill="black", outline="")

    def clique(e): enviar_setpoint(andar)
    frame.bind("<Button-1>", clique)
    label_numero.bind("<Button-1>", clique)
    canvas.bind("<Button-1>", clique)

    return frame

for r, linha in enumerate(andares_layout):
    for c, label in enumerate(linha):
        btn = criar_botao_redondo(frame_botoes, label)
        btn.grid(row=r, column=c, padx=6, pady=6)
        botoes[label] = btn

ctk.CTkLabel(app, text="📞 (35) 62133 – 6115", font=("Segoe UI", 12), text_color="#333").pack(pady=20)

app.mainloop()
