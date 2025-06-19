import numpy as np
import skfuzzy as fuzzy
import skfuzzy.control as ctrl
import paho.mqtt.client as mqtt
import time

# === MAPEAMENTO ANDARES === #
mapeamento_andares = {
    'T': (4, 0),
    '1': (8, 1),
    '2': (11, 2),
    '3': (14, 3),
    '4': (17, 4),
    '5': (20, 5),
    '6': (23, 6),
    '7': (26, 7),
    '8': (29, 8)
}

def altura_para_andar_nome(altura, margem=1.0):
    for nome, (alt_ref, _) in mapeamento_andares.items():
        if abs(altura - alt_ref) <= margem:
            return nome
    return None

# === Estado Inicial === #
posicaoAtual = 4.0  # Começa no térreo
setpoint = None
estado = "PARADO"
erro_anterior = 0.0

# === MQTT === #
def on_connect(client, userdata, flags, rc):
    print("[MQTT] Conectado:", rc)
    client.subscribe("elevador/setpoint")

def on_message(client, userdata, msg):
    global setpoint, estado
    try:
        setpoint = float(msg.payload.decode())
        estado = "MOVIMENTO"
        print(f"[MQTT] Novo setpoint: {setpoint}")
    except:
        print("[MQTT] Setpoint inválido recebido")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("test.mosquitto.org", 1883, 60)
client.loop_start()

# === SISTEMA FUZZY === #
erro = ctrl.Antecedent(np.arange(-25, 25.1, 0.1), 'erro')
erro['MN'] = fuzzy.trapmf(erro.universe, [-25, -25, -15, -7.5])
erro['PN'] = fuzzy.trimf(erro.universe, [-15, -7.5, 0])
erro['ZE'] = fuzzy.trimf(erro.universe, [-0.5, 0, 0.5])
erro['PP'] = fuzzy.trimf(erro.universe, [0, 7.5, 15])
erro['MP'] = fuzzy.trapmf(erro.universe, [7.5, 15, 25, 25])

deltaErro = ctrl.Antecedent(np.arange(-2, 2.01, 0.01), 'deltaErro')
deltaErro['MN'] = fuzzy.trapmf(deltaErro.universe, [-2, -2, -1.0, -0.5])
deltaErro['PN'] = fuzzy.trimf(deltaErro.universe, [-1.0, -0.5, 0])
deltaErro['ZE'] = fuzzy.trimf(deltaErro.universe, [-0.5, 0, 0.5])
deltaErro['PP'] = fuzzy.trimf(deltaErro.universe, [0, 0.5, 1.0])
deltaErro['MP'] = fuzzy.trapmf(deltaErro.universe, [0.5, 1.0, 2, 2])

potenciaMotor = ctrl.Consequent(np.arange(0, 101, 1), 'potenciaMotor')
potenciaMotor['B'] = fuzzy.trimf(potenciaMotor.universe, [0, 31.5, 45])
potenciaMotor['M'] = fuzzy.trimf(potenciaMotor.universe, [31.5, 45, 90])
potenciaMotor['A'] = fuzzy.trimf(potenciaMotor.universe, [45, 90, 100])

rules = [
    ctrl.Rule(erro['MN'] & deltaErro['MN'], potenciaMotor['A']),
    ctrl.Rule(erro['MN'] & deltaErro['PN'], potenciaMotor['A']),
    ctrl.Rule(erro['MN'] & deltaErro['ZE'], potenciaMotor['A']),
    ctrl.Rule(erro['MN'] & deltaErro['PP'], potenciaMotor['M']),
    ctrl.Rule(erro['MN'] & deltaErro['MP'], potenciaMotor['M']),
    ctrl.Rule(erro['PN'] & deltaErro['MN'], potenciaMotor['A']),
    ctrl.Rule(erro['PN'] & deltaErro['PN'], potenciaMotor['M']),
    ctrl.Rule(erro['PN'] & deltaErro['ZE'], potenciaMotor['M']),
    ctrl.Rule(erro['PN'] & deltaErro['PP'], potenciaMotor['M']),
    ctrl.Rule(erro['PN'] & deltaErro['MP'], potenciaMotor['A']),
    ctrl.Rule(erro['ZE'] & deltaErro['MN'], potenciaMotor['M']),
    ctrl.Rule(erro['ZE'] & deltaErro['PN'], potenciaMotor['M']),
    ctrl.Rule(erro['ZE'] & deltaErro['ZE'], potenciaMotor['B']),
    ctrl.Rule(erro['ZE'] & deltaErro['PP'], potenciaMotor['M']),
    ctrl.Rule(erro['ZE'] & deltaErro['MP'], potenciaMotor['M']),
    ctrl.Rule(erro['PP'] & deltaErro['MN'], potenciaMotor['A']),
    ctrl.Rule(erro['PP'] & deltaErro['PN'], potenciaMotor['M']),
    ctrl.Rule(erro['PP'] & deltaErro['ZE'], potenciaMotor['M']),
    ctrl.Rule(erro['PP'] & deltaErro['PP'], potenciaMotor['M']),
    ctrl.Rule(erro['PP'] & deltaErro['MP'], potenciaMotor['A']),
    ctrl.Rule(erro['MP'] & deltaErro['MN'], potenciaMotor['M']),
    ctrl.Rule(erro['MP'] & deltaErro['PN'], potenciaMotor['M']),
    ctrl.Rule(erro['MP'] & deltaErro['ZE'], potenciaMotor['A']),
    ctrl.Rule(erro['MP'] & deltaErro['PP'], potenciaMotor['A']),
    ctrl.Rule(erro['MP'] & deltaErro['MP'], potenciaMotor['A']),
]

sistema_ctrl = ctrl.ControlSystem(rules)
simulador = ctrl.ControlSystemSimulation(sistema_ctrl)

# === LOOP PRINCIPAL === #
# === LOOP PRINCIPAL === #
try:
    while True:
        if estado == "MOVIMENTO" and setpoint is not None:
            erro_atual = setpoint - posicaoAtual
            deltaErro_atual = erro_atual - erro_anterior
            k1 = 1 if erro_atual > 0 else -1  # direção

            # Clamp de segurança para evitar valores fora do universo
            erro_atual = max(-25, min(25, erro_atual))
            deltaErro_atual = max(-2, min(2, deltaErro_atual))

            try:
                simulador.input['erro'] = erro_atual
                simulador.input['deltaErro'] = deltaErro_atual
                simulador.compute()
                potencia = simulador.output['potenciaMotor'] / 100
            except Exception as e:
                print(f"[ERRO FUZZY] Falha ao computar: {e}")
                print(f"  -> erro = {erro_atual:.2f}, deltaErro = {deltaErro_atual:.2f}")
                continue  # pula iteração

            posicaoAtual = abs(posicaoAtual * 0.9995 + k1 * potencia * 0.212312)
            erro_anterior = erro_atual

            # Se chegou no ponto de parada, iniciar frenagem
            if abs(erro_atual) < 0.02:
                print("[ELEVADOR] Iniciando frenagem...")
                erro_freio_anterior = erro_atual

                for t in np.arange(0.1, 1.1, 0.1):  # Frenagem por 1 segundo
                    erro_freio = setpoint - posicaoAtual
                    k1 = 1 if erro_freio > 0 else -1
                    potencia = (1 - t) * 0.315  # Desaceleração progressiva

                    nova_pos = posicaoAtual * 0.999 + k1 * potencia * 0.251287

                    if abs(erro_freio) > abs(erro_freio_anterior):
                        print(f"[ELEVADOR] Parou suavemente por afastamento em t+{t:.1f}s")
                        break

                    posicaoAtual = abs(nova_pos)
                    erro_freio_anterior = erro_freio
                    client.publish("elevador/altura", f"{posicaoAtual:.2f}".encode())
                    time.sleep(0.1)

                estado = "PARADO"
                setpoint = None
                print("[ELEVADOR] Chegou ao destino e está parado.")

        # Publica altura continuamente
        client.publish("elevador/altura", f"{posicaoAtual:.2f}".encode())
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n[FINALIZADO PELO USUÁRIO]")
    client.loop_stop()
    client.disconnect()
