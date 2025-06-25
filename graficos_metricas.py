import numpy as np
import skfuzzy as fuzzy
import skfuzzy.control as ctrl
import matplotlib.pyplot as plt

# === VARIÁVEIS FUZZY (AJUSTADAS PARA O ELEVADOR) === #

erro = ctrl.Antecedent(np.arange(-25, 25.1, 0.1), 'erro')
erro.membershipA = 'i'
erro.unit = 'm'

erro['MN'] = fuzzy.trapmf(erro.universe, [-25, -25, -15, -7.5])
erro['PN'] = fuzzy.trimf(erro.universe, [-15, -7.5, 0])
erro['ZE'] = fuzzy.trimf(erro.universe, [-1.0, 0, 1.0])
erro['PP'] = fuzzy.trimf(erro.universe, [0, 7.5, 15])
erro['MP'] = fuzzy.trapmf(erro.universe, [7.5, 15, 25, 25])

# === PLOT === #
erro.view()
fig = plt.gcf()
axes = fig.gca()
fig.set_size_inches(7, 2.5)

axes.set_xlabel(f'Erro [{erro.unit}]')
axes.set_ylabel(f'Pertinência μ_{erro.membershipA}')
axes.grid(True)
plt.legend(loc='upper right')
plt.tight_layout()
plt.show()





deltaErro = ctrl.Antecedent(np.arange(-2, 2.01, 0.01), 'deltaErro')
deltaErro.membershipA = 'Δi'
deltaErro.unit = 'Δm'
deltaErro['MN'] = fuzzy.trapmf(deltaErro.universe, [-2, -2, -1.0, -0.5])
deltaErro['PN'] = fuzzy.trimf(deltaErro.universe, [-1.0, -0.5, 0])
deltaErro['ZE'] = fuzzy.trimf(deltaErro.universe, [-0.5, 0, 0.5])
deltaErro['PP'] = fuzzy.trimf(deltaErro.universe, [0, 0.5, 1.0])
deltaErro['MP'] = fuzzy.trapmf(deltaErro.universe, [0.5, 1.0, 2, 2])

# Plot
deltaErro.view()
fig = plt.gcf()
axes = fig.gca()
fig.set_size_inches(7, 2.5)

axes.set_xlabel(f'DeltaErro [{deltaErro.unit}]')
axes.set_ylabel(f'Pertinência μ_{deltaErro.membershipA}')
axes.grid(True)
plt.legend(loc='upper right')
plt.tight_layout()
plt.show()

potenciaMotor = ctrl.Consequent(np.arange(0, 91, 1), 'potenciaMotor')
potenciaMotor.membershipA = 'a'
potenciaMotor.unit = '%'
potenciaMotor['I'] = fuzzy.trimf(potenciaMotor.universe, [0, 15, 30])
potenciaMotor['B'] = fuzzy.trimf(potenciaMotor.universe, [15, 30, 55])
potenciaMotor['M'] = fuzzy.trimf(potenciaMotor.universe, [30, 55, 80])
potenciaMotor['A'] = fuzzy.trimf(potenciaMotor.universe, [55, 80, 90])

potenciaMotor.view()
fig = plt.gcf()
axes = fig.gca()
fig.set_size_inches(7, 2.5)
axes.set_xlabel(f'Potência do Motor [{potenciaMotor.unit}]')
axes.set_ylabel(f'Pertinência μ_{potenciaMotor.membershipA}')
axes.grid(True)
plt.legend(loc='upper right')
plt.tight_layout()
plt.show()





# === BASE DE REGRAS CONFORME A TABELA DEFINIDA ===




R1  = ctrl.Rule(erro['MN'] & deltaErro['MN'], potenciaMotor['A'])  # descendo rápido
R2  = ctrl.Rule(erro['MN'] & deltaErro['PN'], potenciaMotor['A'])  # descendo devagar
R3  = ctrl.Rule(erro['MN'] & deltaErro['ZE'], potenciaMotor['A'])  # parado (continua descendo com força)
R4  = ctrl.Rule(erro['MN'] & deltaErro['PP'], potenciaMotor['M'])  # já inverteu tendência
R5  = ctrl.Rule(erro['MN'] & deltaErro['MP'], potenciaMotor['B'])  # subindo rápido

R6  = ctrl.Rule(erro['PN'] & deltaErro['MN'], potenciaMotor['A'])
R7  = ctrl.Rule(erro['PN'] & deltaErro['PN'], potenciaMotor['A'])
R8  = ctrl.Rule(erro['PN'] & deltaErro['ZE'], potenciaMotor['M'])
R9  = ctrl.Rule(erro['PN'] & deltaErro['PP'], potenciaMotor['B'])
R10 = ctrl.Rule(erro['PN'] & deltaErro['MP'], potenciaMotor['I'])

R11 = ctrl.Rule(erro['ZE'] & deltaErro['MN'], potenciaMotor['M'])  # começou a frear
R12 = ctrl.Rule(erro['ZE'] & deltaErro['PN'], potenciaMotor['B'])  # desaceleração leve
R13 = ctrl.Rule(erro['ZE'] & deltaErro['ZE'], potenciaMotor['I'])  # parado mesmo
R14 = ctrl.Rule(erro['ZE'] & deltaErro['PP'], potenciaMotor['B'])  # tendência subindo
R15 = ctrl.Rule(erro['ZE'] & deltaErro['MP'], potenciaMotor['M'])  # subindo mais forte

R16 = ctrl.Rule(erro['PP'] & deltaErro['MN'], potenciaMotor['B'])
R17 = ctrl.Rule(erro['PP'] & deltaErro['PN'], potenciaMotor['M'])
R18 = ctrl.Rule(erro['PP'] & deltaErro['ZE'], potenciaMotor['M'])
R19 = ctrl.Rule(erro['PP'] & deltaErro['PP'], potenciaMotor['A'])
R20 = ctrl.Rule(erro['PP'] & deltaErro['MP'], potenciaMotor['A'])

R21 = ctrl.Rule(erro['MP'] & deltaErro['MN'], potenciaMotor['M'])
R22 = ctrl.Rule(erro['MP'] & deltaErro['PN'], potenciaMotor['M'])
R23 = ctrl.Rule(erro['MP'] & deltaErro['ZE'], potenciaMotor['A'])  # mesmo parado, força
R24 = ctrl.Rule(erro['MP'] & deltaErro['PP'], potenciaMotor['A'])
R25 = ctrl.Rule(erro['MP'] & deltaErro['MP'], potenciaMotor['A'])



# === SISTEMA DE CONTROLE === #
sistema_ctrl = ctrl.ControlSystem([
    R1, R2, R3, R4, R5, R6, R7, R8, R9, R10,
    R11, R12, R13, R14, R15, R16, R17, R18, R19, R20,
    R21, R22, R23, R24, R25
])
simulador = ctrl.ControlSystemSimulation(sistema_ctrl)


# Parâmetros da simulação
setpoint = 14  
posicaoAtual = 8 
posicoes = [posicaoAtual]
tempos = [0.0]
erro_anterior = setpoint - posicaoAtual




for t in np.arange(0.1, 1.1, 0.1): 
    potencia = t * 0.315 / 3  
    k1 = 1 if setpoint > posicaoAtual else -1
    posicaoAtual = abs(posicaoAtual * 0.999 + k1 * potencia * 0.251287)
    posicoes.append(posicaoAtual)
    tempos.append(tempos[-1] + 0.2)
    

# Loop da simulação
for i in range(1000):
    print(f"posicaoAtual: {posicaoAtual}")
    erro_atual = setpoint - posicaoAtual
    #print(f"Erro atual: {erro_atual}")
    deltaErro_atual = erro_atual - erro_anterior
    #print(f"Delta Erro atual: {deltaErro_atual}")


    # Define k1 conforme sentido de movimento
    k1 = 1 if setpoint > posicaoAtual else -1

    simulador.input['erro'] = erro_atual
    simulador.input['deltaErro'] = deltaErro_atual
    simulador.compute()

    print(f"Potência fuzzy aplicada: {simulador.output['potenciaMotor']:.2f}%")


    potencia = simulador.output['potenciaMotor'] / 100 

    
    posicaoAtual = abs(k1 * posicaoAtual * 0.9995 + potencia * 0.212312 )
    posicoes.append(posicaoAtual)
    tempos.append(tempos[-1] + 0.2)

    erro_anterior = erro_atual
    # Condição de parada
    if abs(erro_atual) < 0.02:
        print(f"entrou no if")
        erro_freio_anterior = setpoint - posicaoAtual

        for i in range(5):  
            t = (i + 1) * 0.2  # tempo  0.2, 0.4, 0.6, 0.8, 1.0

            erro_freio = setpoint - posicaoAtual
            k1 = 1 if erro_freio > 0 else -1

            potencia = (1 - t) * 0.315  

            nova_pos = posicaoAtual * 0.999 + k1 * potencia * 0.251287

            posicaoAtual = abs(nova_pos)
            posicoes.append(posicaoAtual)
            tempos.append(tempos[-1] + 0.2)
            erro_freio_anterior = erro_freio


        break

            

# === MAPEAMENTO DE ANDARES ===
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

# Filtra os andares realmente percorridos
min_altura = min(posicoes)
max_altura = max(posicoes)

alturas_ativas = []
labels_ativas = []
for nome, (altura, _) in mapeamento_andares.items():
    if min_altura - 1 <= altura <= max_altura + 1:
        alturas_ativas.append(altura)
        labels_ativas.append(nome)

# === GRÁFICO COM EIXO Y EM ANDARES E CORES ORIGINAIS ===
plt.plot(tempos, posicoes, label='Posição do Elevador (m)', color='tab:blue')
plt.axhline(y=setpoint, color='red', linestyle='--', label='Setpoint')

plt.yticks(alturas_ativas, labels_ativas)
plt.xlabel('Tempo (segundos)')
plt.ylabel('Andar')
plt.title('Simulação do Controle Fuzzy - Elevador')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()


# === CÁLCULO DAS MÉTRICAS ===

altura_inicial = posicoes[0]
altura_final = posicoes[-1]
erro_mm = (altura_final - setpoint) * 1000  # erro em milímetros
pico = max(posicoes) if setpoint > altura_inicial else min(posicoes)
percentual_pico = ((pico - setpoint) / setpoint) * 100
tempo_movimento = tempos[-1]
tipo_movimento = "Subida" if setpoint > altura_inicial else "Descida"

# Exibir resultados formatados
print("\n=== MÉTRICAS DA SIMULAÇÃO ===\n")
print(f"Tipo de Movimento: {tipo_movimento}")
print(f"Altura Final: {altura_final:.4f} m")
print(f"Erro: {erro_mm:.4f} mm")
print(f"Pico: {pico:.4f} m ({percentual_pico:+.4f}%)")
print(f"Tempo de Movimento: {tempo_movimento:.1f} s")




import pandas as pd
from tabulate import tabulate

# Termos possíveis
termos = ['MN', 'PN', 'ZE', 'PP', 'MP']

# Dicionário com as regras
regras_dict = {}

# Percorre as regras e extrai os rótulos dos termos por string parsing
for regra in sistema_ctrl.rules:
    antecedente_str = str(regra.antecedent)  # exemplo: "erro[MN] & deltaErro[PN]"
    consequente_str = str(regra.consequent)  # exemplo: "potenciaMotor[A]"

    # Extrai termos
    erro_label = antecedente_str.split("erro[")[1].split("]")[0]
    deltaErro_label = antecedente_str.split("deltaErro[")[1].split("]")[0]
    saida_label = consequente_str.split("potenciaMotor[")[1].split("]")[0]

    regras_dict[(deltaErro_label, erro_label)] = saida_label[0].upper()

# Monta a tabela
tabela = []
for delta in termos:
    linha = [delta]
    for erro in termos:
        saida = regras_dict.get((delta, erro), '-')
        linha.append(saida)
    tabela.append(linha)

# Cria DataFrame e imprime
colunas = ['dErro/erro'] + termos
df_regras = pd.DataFrame(tabela, columns=colunas)

print("\n==== TABELA DE REGRAS FUZZY ====\n")
print(tabulate(df_regras, headers='keys', tablefmt='fancy_grid'))
