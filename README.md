# TFZ-01: Agente de IA Local (Gemini Powered)

Agente assistente pessoal desenvolvido em Python utilizando a nova SDK `google-genai` e suporte a Function Calling (Tools) para interagir com o sistema operacional.

## Funcionalidades
- **Multi-Modelo Dinâmico:** Sistema de "Cascata" que troca automaticamente de modelo (fallback) se a cota gratuita (Erro 429) estourar.
- **Function Calling:** Capacidade de ler IP, listar arquivos e executar diagnósticos de rede.
- **Personalidade Injetada:** Configurável via arquivo `.env`.

## Como Rodar

1. **Clone o repositório:**

```
bash
git clone [https://github.com/SEU-USUARIO/tfz-01-agent.git](https://github.com/SEU-USUARIO/tfz-01-agent.git)
cd tfz-01-agent
```

2. **Crie o ambiente virtual:**

```
bash
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate # Linux/Mac
```

3. **Instale as dependências:**

```
Bash
pip install -r requirements.txt
```

4. **Configure as Credenciais:**

***Renomeie o arquivo .env.example para .env.***

***Abra o .env e coloque sua GOOGLE_API_KEY real.***

***Ajuste seu USER_NAME e detalhes.***

5. **Execute:**

```
Bash
python agente.py
```