import customtkinter as ctk
import tkinter as tk
from paho.mqtt.client import Client

# Configura tema visual
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# MQTT
BROKER = "test.mosquitto.org"
TOPICO_RECEBER = "elevador/altura"
TOPICO_ENVIAR = "elevador/setpoint"

mapeamento_andares = {
    'T': 4, '1': 8, '2': 11,
    '3': 14, '4': 17, '5': 20,
    '6': 23, '7': 26, '8': 29
}

ultima_altura = None
setpoint_atual = None
botoes = {}

def on_connect(client, userdata, flags, rc):
    client.subscribe(TOPICO_RECEBER)

def on_message(client, userdata, msg):
    global ultima_altura, setpoint_atual
    try:
        altura_atual = float(msg.payload.decode())
        ultima_altura = altura_atual

        andar_atual = "-"
        for nome, altura in mapeamento_andares.items():
            if abs(altura_atual - altura) <= 1.0:
                andar_atual = nome
                break

        andar_var.set(f"Andar: {andar_atual}")

        if setpoint_atual is None or abs(altura_atual - setpoint_atual) < 0.5:
            movimento = "parado"
            icone = "⏹️"
        elif altura_atual < setpoint_atual:
            movimento = "subindo"
            icone = "⬆️"
        else:
            movimento = "descendo"
            icone = "⬇️"

        movimento_var.set(f"{icone} {movimento.upper()}")

        # Apaga botão se chegou
        if setpoint_atual is not None and abs(altura_atual - setpoint_atual) < 0.5:
            for nome, altura in mapeamento_andares.items():
                if altura == setpoint_atual:
                    botoes[nome].configure(border_color="#d9d9d9")
                    setpoint_atual = None
                    break

    except Exception as e:
        print("Erro:", e)

def enviar_setpoint(nome_andar):
    global setpoint_atual
    if nome_andar in mapeamento_andares:
        altura = mapeamento_andares[nome_andar]
        setpoint_atual = altura
        client.publish(TOPICO_ENVIAR, str(altura), retain=True)
        print(f"[ENVIADO] {nome_andar} → {altura}m")
        botoes[nome_andar].configure(border_color="red")

# MQTT init
client = Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, 1883)
client.loop_start()

# Interface
app = ctk.CTk()
app.title("Painel Villarta Estilizado")
app.geometry("320x600")
app.configure(fg_color="#f5f5f5")

andar_var = tk.StringVar(value="Andar: -")
movimento_var = tk.StringVar(value="⏹️ PARADO")

ctk.CTkLabel(app, text="VILLARTA", font=("Segoe UI Black", 20)).pack(pady=(15, 0))
ctk.CTkLabel(app, text="elevadores", font=("Segoe UI", 14), text_color="#888").pack()
ctk.CTkLabel(app, text="CAPACIDADE 975kg\n13 PASSAGEIROS", font=("Segoe UI", 12)).pack(pady=10)
ctk.CTkLabel(app, textvariable=andar_var, font=("Segoe UI", 18)).pack()
ctk.CTkLabel(app, textvariable=movimento_var, font=("Segoe UI", 16), text_color="red").pack(pady=5)

frame_botoes = ctk.CTkFrame(app, fg_color="#f5f5f5")
frame_botoes.pack(pady=20)

layout = [
    ["6", "7", "8"],
    ["3", "4", "5"],
    ["T", "1", "2"]
]

for r, linha in enumerate(layout):
    for c, label in enumerate(linha):
        btn = ctk.CTkButton(
            frame_botoes, text=label,
            width=60, height=60, corner_radius=30,
            font=("Segoe UI", 16), fg_color="#e0e0e0",
            hover_color="#d6d6d6", border_color="#d9d9d9", border_width=2,
            command=lambda l=label: enviar_setpoint(l)
        )
        btn.grid(row=r, column=c, padx=8, pady=8)
        botoes[label] = btn

ctk.CTkLabel(app, text="☎ (35) 62133 – 6115", font=("Segoe UI", 12)).pack(pady=20)

app.mainloop()
