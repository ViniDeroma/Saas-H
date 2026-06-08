import os
import json
import time
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetForumTopicsRequest

CONFIG_FILE = "telegram_config.json"
SESSION_NAME = "erome_session"

class TelegramUploader:
    def __init__(self):
        self.config = self._load_or_create_config()
        self.client = TelegramClient(
            SESSION_NAME, 
            self.config['api_id'], 
            self.config['api_hash'],
            timeout=120,
            request_retries=15,
            connection_retries=15
        )
        self.selected_group = None
        self.topics = []
    
    def _load_or_create_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        print("\n" + "="*50)
        print("   CONFIGURAÇÃO INICIAL DO TELEGRAM (TELETHON)")
        print("="*50)
        print("Obtenha seu api_id e api_hash em: https://my.telegram.org/apps")
        print("Isso so sera necessario na primeira vez!\n")
        
        api_id = input("API ID (numero): ").strip()
        api_hash = input("API Hash (texto): ").strip()
        phone = input("Seu numero de telefone (ex: +5511999999999): ").strip()
        
        config = {
            'api_id': int(api_id) if api_id.isdigit() else api_id,
            'api_hash': api_hash,
            'phone': phone
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        return config

    def connect(self):
        """Conecta e realiza o login (se necessario)."""
        print("\n[Telegram] Conectando a sua conta...")
        self.client.start(phone=self.config['phone'])
        print("[Telegram] Conectado com sucesso!\n")

    def _get_groups(self):
        groups = []
        for dialog in self.client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                groups.append(dialog)
        return groups

    def _get_topics(self, group_entity):
        topics = []
        try:
            result = self.client(GetForumTopicsRequest(
                peer=group_entity,
                offset_date=0,
                offset_id=0,
                offset_topic=0,
                limit=100,
                q=""
            ))
            for topic in result.topics:
                topics.append(topic)
        except Exception as e:
            print(f"\n[AVISO] Nao foi possivel buscar os topicos do forum: {e}\n")
        return topics

    def setup_target_group(self):
        """Permite ao usuario escolher o grupo/forum alvo para os uploads."""
        print("Buscando seus grupos e canais...")
        groups = self._get_groups()
        
        # Mostrar os 30 mais recentes
        top_groups = groups[:30]
        print("\nSeus grupos/canais mais recentes:")
        for i, g in enumerate(top_groups, 1):
            print(f"[{i:02d}] {g.title}")
        
        print("\n[0] Cancelar integracao Telegram")
        choice = input("\nEscolha o numero do grupo (ou digite o nome para buscar): ").strip()
        
        if choice == '0':
            return False

        selected_dialog = None
        if choice.isdigit() and 1 <= int(choice) <= len(top_groups):
            selected_dialog = top_groups[int(choice)-1]
        else:
            # Busca por nome
            for g in groups:
                if choice.lower() in g.title.lower():
                    selected_dialog = g
                    break
        
        if not selected_dialog:
            print("Grupo nao encontrado. Integracao Telegram cancelada.")
            return False

        self.selected_group = selected_dialog.entity
        print(f"\n---> Grupo selecionado: {selected_dialog.title}")
        
        print("Buscando topicos do grupo...")
        self.topics = self._get_topics(self.selected_group)
        if self.topics:
            print(f"Encontrados {len(self.topics)} topicos ativos!")
        else:
            print("Nenhum topico encontrado. As mensagens serao enviadas no chat principal.")
            
        return True

    def ask_topic_for_album(self, album_title, current_idx, total_albums):
        """
        Pergunta interativamente em qual topico o usuario quer salvar este album.
        Retorna:
          - (topic_id, topico_nome) se escolheu um topico.
          - (None, "Chat Principal") se escolheu o chat principal.
          - ("skip", None) se escolheu pular o album inteiro (nao baixar).
          - ("local", None) se escolheu apenas baixar localmente, sem enviar pro Telegram.
        """
        print(f"\n" + "="*50)
        print(f"  ALBUM [{current_idx}/{total_albums}]: {album_title}")
        print("="*50)
        
        if self.topics:
            for i, t in enumerate(self.topics, 1):
                # t.title eh o nome do topico
                print(f"[{i:02d}] {getattr(t, 'title', f'Topico {t.id}')}")
        print("\nOpcoes Especiais:")
        print("[M] Enviar para o Chat Principal (sem topico)")
        print("[L] Baixar APENAS LOCAL (nao enviar pro Telegram)")
        print("[P] PULAR este album completamente")
        
        while True:
            choice = input("\nEscolha para onde enviar (numero ou letra): ").strip().upper()
            if choice == 'P':
                return "skip", None
            if choice == 'L':
                return "local", None
            if choice == 'M':
                return None, "Chat Principal"
            
            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(self.topics):
                    t = self.topics[idx-1]
                    return t.id, getattr(t, 'title', f'Topico {t.id}')
            
            print("Opcao invalida. Tente novamente.")

    def _upload_progress(self, current, total):
        if total > 0:
            percent = (current / total) * 100
            # reseta o print_last se for um novo arquivo (current caiu)
            if current < getattr(self, 'last_current_bytes', 0):
                self.last_upload_print = 0
            self.last_current_bytes = current
            
            last_print = getattr(self, 'last_upload_print', 0)
            if percent - last_print >= 25:
                print(f"      -> subindo arquivo atual: {percent:.0f}% ({current//(1024*1024)}MB / {total//(1024*1024)}MB)")
                self.last_upload_print = percent

    def upload_files(self, topic_id, file_paths, caption=""):
        """Faz o upload dos arquivos para o grupo/topico selecionado em blocos de 10."""
        if not self.selected_group or not file_paths:
            return False
            
        batch_size = 10
        total = len(file_paths)
        
        print(f"\n    [Telegram] Iniciando upload de {total} midias...")
        
        # Parametros extras para topicos
        kwargs = {}
        if topic_id:
            kwargs['reply_to'] = topic_id

        success_count = 0
        for i in range(0, total, batch_size):
            batch = file_paths[i:i+batch_size]
            print(f"    [Telegram] Enviando lote {i//batch_size + 1}/{(total+batch_size-1)//batch_size} ({len(batch)} arquivos)...")
            
            self.last_upload_print = 0
            self.last_current_bytes = 0
            
            try:
                # O primeiro lote vai com o titulo do album no caption
                self.client.send_file(
                    self.selected_group, 
                    batch, 
                    caption=caption if i == 0 else "", 
                    progress_callback=self._upload_progress,
                    **kwargs
                )
                success_count += len(batch)
            except Exception as e:
                print(f"    [ERRO Telegram] Falha no upload do lote: {e}")
                print(f"    Recriando a sessao do Telegram para forcar correcao...")
                try:
                    self.client.disconnect()
                except:
                    pass
                time.sleep(5)
                
                try:
                    # Recria o client do zero para limpar qualquer session ID corrompido
                    self.client = TelegramClient(
                        SESSION_NAME, 
                        self.config['api_id'], 
                        self.config['api_hash'],
                        timeout=120,
                        request_retries=15,
                        connection_retries=15
                    )
                    self.client.start(phone=self.config['phone'])
                    
                    self.client.send_file(
                        self.selected_group, 
                        batch, 
                        caption=caption if i == 0 else "", 
                        progress_callback=self._upload_progress,
                        **kwargs
                    )
                    success_count += len(batch)
                except Exception as e2:
                    print(f"    [ERRO Telegram] Falha CRITICA no lote apos reconectar: {e2}")
        
        print(f"    [Telegram] Upload concluido! ({success_count}/{total} arquivos)")
        return success_count > 0
