# 🛗 Sistema de Elevador com Controle Fuzzy via MQTT

Este projeto simula o funcionamento completo de um elevador inteligente controlado por lógica fuzzy PD. Ele é dividido em duas partes integradas via protocolo MQTT:

1. **Sistema de Controle Fuzzy (backend)** — simula o movimento real do elevador com aceleração, frenagem e controle contínuo
2. **Interface Gráfica (frontend)** — permite controle visual dos andares, emergência, cronômetro e feedback do estado do elevador

---

## 🎯 Objetivos

- Simular um elevador com comportamento realista (aceleração, frenagem, lógica de fila)
- Comunicar ações e estados via MQTT
- Aplicar lógica fuzzy PD para controle de posição
- Fornecer interface intuitiva e acessível

---

## 🚀 Funcionalidades

### 🧠 Controle Fuzzy (backend)

- Simulação de movimento entre andares com:
  - Aceleração (embalo) suave
  - Controle fuzzy contínuo
  - Frenagem linear
- Reconhecimento de andares via altura
- Rejeição automática de setpoints repetidos
- Resposta a comandos de emergência e reset
- Publicação contínua da altura no tópico MQTT

### 🖥️ Interface Gráfica (frontend)

- Interface moderna com `customtkinter`
- Botões personalizados com aparência metálica e braille
- Fila de andares: aceita múltiplos toques em sequência
- Indicação visual do andar atual e da direção (⬆️⬇️⏹️)
- Cronômetro de viagem em tempo real
- Botão de emergência com animação de alerta
- Botão de reset para retomar operação

---

## 🧰 Tecnologias utilizadas

- `Python 3.10+`
- `scikit-fuzzy`
- `paho-mqtt`
- `customtkinter`
- Broker MQTT: `test.mosquitto.org` (público)

---

## 📡 Comunicação MQTT

| Tópico                      | Direção   | Descrição                                        |
|----------------------------|-----------|--------------------------------------------------|
| `elevador/setpoint`        | `publish` | Envia a altura desejada (em metros)              |
| `elevador/altura`          | `subscribe` | Recebe a altura atual do elevador (em tempo real) |
| `elevador/emergencia`      | `publish` | Interrompe o elevador imediatamente              |
| `elevador/emergencia/reset`| `publish` | Retoma o funcionamento após emergência           |

---

## 📈 Alturas por andar

| Andar | Altura (m) |
|-------|------------|
| T     | 4          |
| 1     | 8          |
| 2     | 11         |
| 3     | 14         |
| 4     | 17         |
| 5     | 20         |
| 6     | 23         |
| 7     | 26         |
| 8     | 29         |

---

## 🗂️ Estrutura do Projeto

```
elevador/
├── elevador_fuzzy.py          # Sistema de controle fuzzy (backend)
├── interface_elevador.py      # Interface gráfica customtkinter (frontend)
├── README.md
```

---

## ⚙️ Como executar

### Backend (controle fuzzy)

```bash
pip install numpy scikit-fuzzy paho-mqtt
python elevador_fuzzy.py
```

### Frontend (interface gráfica)

```bash
pip install customtkinter paho-mqtt
python interface_elevador.py
```

---
