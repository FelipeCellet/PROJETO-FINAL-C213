import numpy as np
import skfuzzy as fuzzy
import skfuzzy.control as ctrl
import paho.mqtt.client as mqtt
import time

emergencia_ativa = False
setpoint_backup = None


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
    client.subscribe("elevador/emergencia")
    client.subscribe("elevador/emergencia/reset")

def on_message(client, userdata, msg):
    global setpoint, estado, embalo_index, emergencia_ativa,setpoint_backup
    if msg.topic == "elevador/setpoint":
        try:
            novo_setpoint = float(msg.payload.decode())
            andar_atual = altura_para_andar_nome(posicaoAtual)

            # Verifica se o setpoint é o mesmo andar
            for nome, (altura_ref, _) in mapeamento_andares.items():
                if abs(novo_setpoint - altura_ref) < 1.0:  
                    if nome == andar_atual:
                        print(f"[MQTT] Setpoint recebido ({novo_setpoint}) é o mesmo andar atual ({nome}). Ignorando.")
                        return  

            
            setpoint = novo_setpoint
            setpoint_backup = setpoint 
            estado = "EMBALO"
            embalo_index = 0
            print(f"[MQTT] Novo setpoint: {setpoint}")

        except:
            print("[MQTT] Setpoint inválido recebido")

    elif msg.topic == "elevador/emergencia":
        print("[EMERGÊNCIA] Comando recebido. Interrompendo elevador...")
        emergencia_ativa = True

    elif msg.topic == "elevador/emergencia/reset":
        print("[EMERGÊNCIA] Reset recebido. Voltando ao normal.")
        emergencia_ativa = False
        if setpoint_backup is not None:
            setpoint = setpoint_backup
            estado = "EMBALO"
            embalo_index = 0



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

potenciaMotor = ctrl.Consequent(np.arange(0, 91, 1), 'potenciaMotor')
potenciaMotor['I'] = fuzzy.trimf(potenciaMotor.universe, [0, 15, 30])
potenciaMotor['B'] = fuzzy.trimf(potenciaMotor.universe, [15, 30, 55])
potenciaMotor['M'] = fuzzy.trimf(potenciaMotor.universe, [30, 55, 80])
potenciaMotor['A'] = fuzzy.trimf(potenciaMotor.universe, [55, 80, 90])


# === BASE DE REGRAS === #
rules = [
    ctrl.Rule(erro['MN'] & deltaErro['MN'], potenciaMotor['A']),
    ctrl.Rule(erro['MN'] & deltaErro['PN'], potenciaMotor['A']),
    ctrl.Rule(erro['MN'] & deltaErro['ZE'], potenciaMotor['A']),
    ctrl.Rule(erro['MN'] & deltaErro['PP'], potenciaMotor['M']),
    ctrl.Rule(erro['MN'] & deltaErro['MP'], potenciaMotor['B']),
    ctrl.Rule(erro['PN'] & deltaErro['MN'], potenciaMotor['A']),
    ctrl.Rule(erro['PN'] & deltaErro['PN'], potenciaMotor['A']),
    ctrl.Rule(erro['PN'] & deltaErro['ZE'], potenciaMotor['M']),
    ctrl.Rule(erro['PN'] & deltaErro['PP'], potenciaMotor['B']),
    ctrl.Rule(erro['PN'] & deltaErro['MP'], potenciaMotor['I']),
    ctrl.Rule(erro['ZE'] & deltaErro['MN'], potenciaMotor['M']),
    ctrl.Rule(erro['ZE'] & deltaErro['PN'], potenciaMotor['B']),
    ctrl.Rule(erro['ZE'] & deltaErro['ZE'], potenciaMotor['I']),
    ctrl.Rule(erro['ZE'] & deltaErro['PP'], potenciaMotor['B']),
    ctrl.Rule(erro['ZE'] & deltaErro['MP'], potenciaMotor['M']),
    ctrl.Rule(erro['PP'] & deltaErro['MN'], potenciaMotor['B']),
    ctrl.Rule(erro['PP'] & deltaErro['PN'], potenciaMotor['M']),
    ctrl.Rule(erro['PP'] & deltaErro['ZE'], potenciaMotor['M']),
    ctrl.Rule(erro['PP'] & deltaErro['PP'], potenciaMotor['A']),
    ctrl.Rule(erro['PP'] & deltaErro['MP'], potenciaMotor['A']),
    ctrl.Rule(erro['MP'] & deltaErro['MN'], potenciaMotor['M']),
    ctrl.Rule(erro['MP'] & deltaErro['PN'], potenciaMotor['M']),
    ctrl.Rule(erro['MP'] & deltaErro['ZE'], potenciaMotor['A']),
    ctrl.Rule(erro['MP'] & deltaErro['PP'], potenciaMotor['A']),
    ctrl.Rule(erro['MP'] & deltaErro['MP'], potenciaMotor['A']),
]

sistema_ctrl = ctrl.ControlSystem(rules)
simulador = ctrl.ControlSystemSimulation(sistema_ctrl)

# === LOOP PRINCIPAL COM EMBALO INICIAL E TS=200ms === #
try:
    embalo_index = 0
    print(f"[DEBUG] Estado: {estado} | Setpoint: {setpoint} | Posição: {posicaoAtual:.2f}")

    while True:
        if emergencia_ativa:
            print("[ELEVADOR] EMERGÊNCIA ATIVA. LOOP PARADO.")
            estado = "PARADO"
            setpoint = None
            client.publish("elevador/altura", f"{posicaoAtual:.2f}".encode())
            time.sleep(0.2)
            continue

        #  Nada acontece até que setpoint seja recebido
        if setpoint is None or estado == "PARADO":
            client.publish("elevador/altura", f"{posicaoAtual:.2f}".encode())
            time.sleep(0.2)
            continue

        #  EMBALO 2 segundos iniciais
        if estado == "EMBALO" and embalo_index < 10:
            tempo_s = (embalo_index + 1) * 0.2
            potencia = 0.315 * (tempo_s / 2)
            k1 = 1 if setpoint > posicaoAtual else -1
            posicaoAtual = abs(posicaoAtual * 0.999 + k1 * potencia * 0.251287)
            client.publish("elevador/altura", f"{posicaoAtual:.2f}".encode())
            embalo_index += 1
            time.sleep(0.2)
            if embalo_index == 10:
                estado = "MOVIMENTO"
                erro_anterior = setpoint - posicaoAtual
            continue

        #  FUZZY
        elif estado == "MOVIMENTO":
            erro_atual = setpoint - posicaoAtual
            deltaErro_atual = erro_atual - erro_anterior
            k1 = 1 if erro_atual > 0 else -1
            print(f"[DEBUG] erro={erro_atual:.2f} deltaErro={deltaErro_atual:.2f}")

            #  Validação
            if not (-25 <= erro_atual <= 25 and -2 <= deltaErro_atual <= 2):
                print("[FUZZY BLOQUEADO] Entradas fora do universo. Ignorando ciclo.")
                time.sleep(0.2)
                continue

            try:
                simulador.input['erro'] = erro_atual
                simulador.input['deltaErro'] = deltaErro_atual
                simulador.compute()
                potencia = simulador.output['potenciaMotor'] / 100
            except Exception as e:
                print(f"[ERRO FUZZY] Falha ao computar: {e}")
                time.sleep(0.2)
                continue

            posicaoAtual = abs(posicaoAtual * 0.9995 + k1 * potencia * 0.212312)
            erro_anterior = erro_atual

            #  Inicia frenagem
            if abs(erro_atual) < 0.02:
                print("[ELEVADOR] Iniciando frenagem...")
                for i in range(5):
                    t = (i + 1) * 0.2
                    erro_freio = setpoint - posicaoAtual
                    k1 = 1 if erro_freio > 0 else -1
                    potencia = (1 - t) * 0.315
                    nova_pos = posicaoAtual * 0.999 + k1 * potencia * 0.251287
                    posicaoAtual = abs(nova_pos)
                    client.publish("elevador/altura", f"{posicaoAtual:.2f}".encode())
                    time.sleep(0.2)

                estado = "PARADO"
                setpoint = None
                print("[ELEVADOR] Chegou ao destino e está parado.")
                continue

        #  posição atual
        client.publish("elevador/altura", f"{posicaoAtual:.2f}".encode())
        time.sleep(0.2)

except KeyboardInterrupt:
    print("\n[FINALIZADO PELO USUÁRIO]")
    client.loop_stop()
    client.disconnect()
