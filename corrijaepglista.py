import logging
import re
import os
import requests
import gzip
import lzma
import xml.etree.ElementTree as ET
from tqdm import tqdm
from typing import List, Dict

# =========================================================
# CONFIGURAÇÃO DE LOGGING
# =========================================================
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


# =========================================================
# CLASSE M3UProcessor – carrega e extrai canais e URLs de EPG
# =========================================================
class M3UProcessor:
    def __init__(self, m3u_path: str):
        self.m3u_path = m3u_path
        self.epg_urls: set[str] = set()
        self.channels: List[Dict] = []

    def load_m3u(self) -> bool:
        try:
            with open(self.m3u_path, 'r', encoding='utf-8', errors='ignore') as f:
                m3u_content = f.read()
            logging.info(f"M3U carregado com sucesso de {self.m3u_path}")
            self._parse_m3u_content(m3u_content)
            return True
        except FileNotFoundError:
            logging.error(f"Erro: Arquivo M3U não encontrado em {self.m3u_path}")
            return False
        except Exception as e:
            logging.error(f"Erro ao carregar M3U de {self.m3u_path}: {e}")
            return False

    def _parse_m3u_content(self, m3u_content: str):
        lines = m3u_content.splitlines()
        for i, line in enumerate(lines):
            if line.startswith('#EXTM3U'):
                match_xtvg = re.search(r'x-tvg-url="([^"]+)"', line)
                match_urltvg = re.search(r'url-tvg="([^"]+)"', line)
                if match_xtvg:
                    self.epg_urls.update(match_xtvg.group(1).split(','))
                if match_urltvg:
                    self.epg_urls.update(match_urltvg.group(1).split(','))
            elif line.startswith('#EXTINF'):
                channel_info = {}
                channel_info['original_line'] = line

                match_tvg_id = re.search(r'tvg-id="([^"]*)"', line)
                channel_info['tvg-id'] = match_tvg_id.group(1) if match_tvg_id else ''

                match_tvg_name = re.search(r'tvg-name="([^"]*)"', line)
                channel_info['tvg-name'] = match_tvg_name.group(1) if match_tvg_name else ''

                match_name = re.search(r',([^,]+)$', line)
                channel_info['name'] = match_name.group(1).strip() if match_name else ''

                if i + 1 < len(lines):
                    channel_info['url'] = lines[i + 1].strip()
                else:
                    channel_info['url'] = ''
                self.channels.append(channel_info)


# =========================================================
# CLASSE M3UUpdater – atualiza o arquivo M3U ORIGINAL
# =========================================================
class M3UUpdater:
    def __init__(self, m3u_path: str, channels: List[Dict]):
        self.m3u_path = m3u_path
        self.channels = channels

    def update_m3u(self, original_m3u_content: str) -> bool:
        try:
            logging.info(f"Iniciando a atualização do arquivo M3U: {self.m3u_path}")

            updated_lines = []
            m3u_lines = original_m3u_content.splitlines()
            channel_index = 0
            vlc_opts_added = set()  # Para controlar se já adicionamos os #EXTVLCOPT

            # Log para verificar se o conteúdo foi carregado
            logging.debug(f"Conteúdo original do M3U carregado com {len(m3u_lines)} linhas.")

            for i, line in enumerate(m3u_lines):
                if line.startswith("#EXTINF"):
                    if channel_index < len(self.channels):
                        ch = self.channels[channel_index]

                        # Log para verificar se estamos atualizando o canal corretamente
                        logging.debug(f"Atualizando canal: {ch['name']} com URL: {ch['url']}")

                        updated_lines.append(ch["original_line"])  # Linha original
                        updated_lines.append(ch["url"])  # URL do canal
                        channel_index += 1

                        # Adiciona #EXTVLCOPT apenas uma vez
                        if ch["url"] not in vlc_opts_added:
                            updated_lines.append("#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36 CrKey/1.44.191160")
                            vlc_opts_added.add(ch["url"])

                else:
                    # Mantém cabeçalho e comentários
                    if not line.startswith("http"):
                        updated_lines.append(line)

            # Se não encontramos canais, log de erro
            if channel_index == 0:
                logging.error(f"Nenhum canal encontrado para atualizar no arquivo M3U!")

            # Sobrescreve o arquivo original apenas se houver atualizações
            if updated_lines:
                with open(self.m3u_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(updated_lines) + "\n")
                logging.info(f"✅ Arquivo M3U atualizado com sucesso: {self.m3u_path}")
                return True
            else:
                logging.warning(f"Nenhuma atualização foi feita no arquivo M3U.")
                return False

        except Exception as e:
            logging.error(f"Erro ao atualizar o arquivo M3U: {e}")
            return False


# =========================================================
# CLASSE EPGProcessor – baixa, descomprime e parseia EPGs XML
# =========================================================
class EPGProcessor:
    def __init__(self, temp_dir: str = '/tmp'):
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)

    def download_and_parse_epgs(self, epg_urls: set[str]) -> Dict[str, str]:
        all_epg_data = {}
        for url in epg_urls:
            filename = os.path.basename(url).split('?')[0]
            download_path = os.path.join(self.temp_dir, filename)
            decompressed_path = download_path

            if self._download_file(url, download_path):
                if filename.endswith('.gz'):
                    decompressed_path = os.path.join(self.temp_dir, filename.replace('.gz', ''))
                    if self._decompress_gz(download_path, decompressed_path):
                        all_epg_data.update(self._parse_epg_file(decompressed_path))
                elif filename.endswith('.xz'):
                    decompressed_path = os.path.join(self.temp_dir, filename.replace('.xz', ''))
                    if self._decompress_xz(download_path, decompressed_path):
                        all_epg_data.update(self._parse_epg_file(decompressed_path))
                else:
                    all_epg_data.update(self._parse_epg_file(download_path))

                # Limpa arquivos temporários
                if os.path.exists(download_path):
                    os.remove(download_path)
                if os.path.exists(decompressed_path) and decompressed_path != download_path:
                    os.remove(decompressed_path)
        return all_epg_data

    def _download_file(self, url: str, output_path: str) -> bool:
        try:
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            with open(output_path, 'wb') as f, tqdm(
                total=total_size, unit='B', unit_scale=True, desc=os.path.basename(output_path)
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
            logging.info(f"Arquivo baixado com sucesso: {output_path}")
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro ao baixar o arquivo {url}: {e}")
            return False

    def _decompress_gz(self, input_path: str, output_path: str) -> bool:
        try:
            with gzip.open(input_path, 'rb') as f_in, open(output_path, 'wb') as f_out:
                f_out.write(f_in.read())
            logging.info(f"Arquivo .gz descomprimido: {output_path}")
            return True
        except Exception as e:
            logging.error(f"Erro ao descomprimir .gz {input_path}: {e}")
            return False

    def _decompress_xz(self, input_path: str, output_path: str) -> bool:
        try:
            with lzma.open(input_path, 'rb') as f_in, open(output_path, 'wb') as f_out:
                f_out.write(f_in.read())
            logging.info(f"Arquivo .xz descomprimido: {output_path}")
            return True
        except Exception as e:
            logging.error(f"Erro ao descomprimir .xz {input_path}: {e}")
            return False

    def _parse_epg_file(self, epg_path: str) -> Dict[str, str]:
        epg_data = {}
        try:
            tree = ET.parse(epg_path)
            root = tree.getroot()

            for channel_elem in root.findall(".//channel"):
                tvg_id = channel_elem.get("id")
                if tvg_id:
                    epg_data[tvg_id] = channel_elem
            logging.info(f"EPG parseado com sucesso: {epg_path}")
        except Exception as e:
            logging.error(f"Erro ao parsear o EPG {epg_path}: {e}")
        return epg_data
