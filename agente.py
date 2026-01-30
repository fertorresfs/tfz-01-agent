import os
import sys
import platform
import socket
import time
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from dotenv import load_dotenv

# --- 1. CARREGAMENTO ---
load_dotenv()

def get_env(var_name, default=None):
    val = os.getenv(var_name, default)
    return val if val else default

API_KEY = get_env("GOOGLE_API_KEY")
if not API_KEY:
    print("ERRO: API Key faltando.")
    sys.exit(1)

AGENT_NAME = get_env("AGENT_NAME", "Bot")
# Cria uma lista de modelos: [Principal, Reserva1, Reserva2...]
MAIN_MODEL = get_env("MODEL_ID", "gemini-2.0-flash-lite-001")
FALLBACKS = get_env("FALLBACK_MODELS", "gemini-1.5-flash").split(",")
MODEL_POOL = [MAIN_MODEL] + [m.strip() for m in FALLBACKS if m.strip()]

USER_NAME = get_env("USER_NAME", "Usuário")
RAW_PROMPT = get_env("SYSTEM_PROMPT_TEMPLATE", "Você é um assistente útil.")

# Monta o Prompt
SYSTEM_INSTRUCTION = RAW_PROMPT.replace(r'\n', '\n').format(
    agent_name=AGENT_NAME,
    user_name=USER_NAME,
    user_role=get_env("USER_ROLE", ""),
    user_details=get_env("USER_DETAILS", "")
)

client = genai.Client(api_key=API_KEY)

# --- 2. FERRAMENTAS ---
def obter_info_sistema() -> str:
    """Retorna IP, Hostname e OS."""
    try:
        hostname = socket.gethostname()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            s.connect(('10.254.254.254', 1))
            ip = s.getsockname()[0]
        except Exception: ip = '127.0.0.1'
        finally: s.close()
        return f"Host: {hostname} | IP: {ip} | OS: {platform.system()} {platform.release()}"
    except Exception as e: return str(e)

def listar_arquivos(caminho: str = ".") -> str:
    """Lista arquivos (max 20)."""
    try:
        if not os.path.exists(caminho): return "Caminho inválido."
        return "\n".join(os.listdir(caminho)[:20])
    except Exception as e: return str(e)

TOOLS = [obter_info_sistema, listar_arquivos]

# --- 3. CLASSE DE GERENCIAMENTO DE SESSÃO ---
class SessionManager:
    def __init__(self):
        self.current_model_index = 0
        self.chat = None
        self.history = [] # Mantém histórico para migrar entre modelos se necessário
        self.initialize_chat(MODEL_POOL[0])

    def initialize_chat(self, model_id, previous_history=None):
        """Inicia ou Reinicia o chat com um modelo específico."""
        try:
            # Se for recriação, tenta preservar histórico
            config_history = previous_history if previous_history else []
            
            self.chat = client.chats.create(
                model=model_id,
                history=config_history,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools=TOOLS,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False),
                    temperature=float(get_env("TEMPERATURE", "0.5")),
                )
            )
            return True
        except Exception as e:
            print(f"[ERRO DE INIT] Não foi possível iniciar {model_id}: {e}")
            return False

    def send_with_fallback(self, text_input):
        """
        Lógica 'Cascata': Tenta modelo 1 -> Erro 429 -> Tenta modelo 2 -> ...
        """
        # Sempre começa tentando pelo modelo atual (ou volta para o principal se quisermos resetar)
        # Aqui, vamos tentar o atual, e se falhar, avança na lista.
        
        attempts = 0
        max_attempts = len(MODEL_POOL)

        while attempts < max_attempts:
            current_model = MODEL_POOL[self.current_model_index]
            
            try:
                # Tenta enviar mensagem
                response = self.chat.send_message(text_input)
                
                # Se sucesso, atualiza histórico local (opcional, pois o objeto chat já guarda)
                # Retorna sucesso
                return response, current_model

            except ClientError as e:
                error_msg = str(e)
                # Verifica se é erro de Cota (429) ou Recurso Esgotado
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    print(f"\n[ALERTA] Cota cheia no modelo {current_model}...")
                    
                    # Avança para o próximo modelo
                    self.current_model_index = (self.current_model_index + 1) % len(MODEL_POOL)
                    next_model = MODEL_POOL[self.current_model_index]
                    
                    print(f"[SISTEMA] Migrando contexto para backup: {next_model} ⚡")
                    
                    # Tenta pegar o histórico antigo para não perder a conversa
                    old_history = self.chat._curated_history if hasattr(self.chat, '_curated_history') else []
                    
                    # Reinicia o chat com o novo modelo
                    if self.initialize_chat(next_model, previous_history=old_history):
                        attempts += 1
                        continue # Tenta enviar novamente no próximo loop
                    else:
                        break # Se não conseguiu nem iniciar o chat, erro grave.
                else:
                    # Se for outro erro (ex: erro de sintaxe), não adianta trocar modelo
                    raise e
        
        raise Exception("Todos os modelos de fallback estão esgotados ou com erro.")

# --- 4. MAIN ---
def main():
    session = SessionManager()

    print(f"╔════════════════════════════════════════════════════╗")
    print(f"║  {AGENT_NAME.upper()} - MODO MULTI-MODELO (DINÂMICO)     ║")
    print(f"║  Pool: {', '.join(MODEL_POOL)}")
    print(f"╚════════════════════════════════════════════════════╝")

    while True:
        try:
            prompt = input(f"\n[{USER_NAME}]: ").strip()
            if prompt.lower() in ['sair', 'exit']: break
            if not prompt: continue

            print("...", end="", flush=True)
            
            # Chama a função de cascata
            response, model_used = session.send_with_fallback(prompt)
            
            print("\r   \r", end="") # Limpa os pontinhos

            if response and response.text:
                # Mostra qual modelo respondeu se não for o principal (Debug visual)
                suffix = f" ({model_used})" if model_used != MODEL_POOL[0] else ""
                print(f"[{AGENT_NAME}{suffix}]: {response.text}")
            else:
                print(f"[{AGENT_NAME}]: (Ação executada)")

        except KeyboardInterrupt:
            print("\nEncerrando...")
            break
        except Exception as e:
            print(f"\n[ERRO FATAL]: {e}")
            print("Dica: Aguarde 1 minuto para resetar as cotas de todos os modelos.")

if __name__ == "__main__":
    main()