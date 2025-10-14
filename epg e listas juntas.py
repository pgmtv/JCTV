#!/usr/bin/env python3
"""
M3U & EPG Consolidator - Concatena múltiplos arquivos M3U e consolida seus EPGs
em um único arquivo XMLTV compactado (.xml.gz), com relatório de erros aprimorado.
Compatível com execução no GitHub Actions.
"""

import requests
import gzip
import lzma
import xml.etree.ElementTree as ET
import re
import sys
from urllib.parse import urlparse
from datetime import datetime
import os
from io import BytesIO
import tempfile
import shutil

class M3uEpgConsolidator:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.failed_urls = []
        self.successful_urls = []
        self.processed_channels = {}
        self.total_programmes = 0
        self.temp_xml_file = tempfile.mktemp(suffix=".xml")

    def extract_epg_urls_from_m3u_content(self, content):
        """Extrai URLs de EPG do conteúdo M3U completo."""
        epg_urls = set()
        print("🔍 Procurando URLs de EPG no conteúdo M3U consolidado...")

        pattern = r'#EXTM3U[^>]*?(?:url-tvg|x-tvg-url)="([^"]+)"'
        match = re.search(pattern, content, re.IGNORECASE)

        if match:
            urls_string = match.group(1)
            urls = [u.strip() for u in urls_string.split(',') if u.strip()]
            epg_urls.update(urls)
        
        valid_epg_urls = []
        for epg_url in epg_urls:
            cleaned_url = epg_url.strip().rstrip(',;"\'')
            parsed = urlparse(cleaned_url)
            
            if parsed.scheme and parsed.netloc and '.' in parsed.netloc:
                if not any(ext in cleaned_url.lower() for ext in ['.jpg', '.png', '.webp', '.jpeg']):
                    valid_epg_urls.append(cleaned_url)

        unique_urls = sorted(list(dict.fromkeys(valid_epg_urls)))
        print(f"  ✅ Encontradas {len(unique_urls)} URLs de EPG únicas e válidas.")
        return unique_urls

    def download_epg(self, url):
        print(f"\n📅 Baixando EPG: {url}")
        try:
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
            content = response.content
            if url.endswith('.gz'):
                content = gzip.decompress(content)
                print("  📜 Arquivo descomprimido (.gz)")
            elif url.endswith('.xz'):
                content = lzma.decompress(content)
                print("  📜 Arquivo descomprimido (.xz)")
            try:
                xml_content = content.decode('utf-8')
            except UnicodeDecodeError:
                xml_content = content.decode('latin-1', errors='ignore')
            if not xml_content.strip().startswith(('<', '<?xml')):
                raise Exception("Conteúdo não parece ser XML")
            self.successful_urls.append(url)
            print("  ✅ EPG baixado com sucesso")
            return xml_content
        except Exception as e:
            print(f"  ❌ Erro ao baixar EPG: {e}")
            self.failed_urls.append(url)
            return None

    def process_epg_incremental(self, xml_content, source_url):
        """Processa o conteúdo XML e associa erros à sua URL de origem."""
        try:
            root = ET.fromstring(xml_content)
            channels_count = 0
            programmes_count = 0

            if not os.path.exists(self.temp_xml_file):
                with open(self.temp_xml_file, 'w', encoding='utf-8') as f:
                    f.write('<?xml version="1.0" encoding="utf-8"?>\n<tv>\n')

            with open(self.temp_xml_file, 'a', encoding='utf-8') as f:
                for channel in root.findall('channel'):
                    channel_id = channel.get('id')
                    if channel_id and channel_id not in self.processed_channels:
                        self.processed_channels[channel_id] = True
                        channels_count += 1
                        f.write('\t' + ET.tostring(channel, encoding='unicode') + '\n')

                for programme in root.findall('programme'):
                    programmes_count += 1
                    self.total_programmes += 1
                    f.write('\t' + ET.tostring(programme, encoding='unicode') + '\n')
            
            print(f"  📊 Processado: {channels_count} canais novos, {programmes_count} programas")

        except ET.ParseError as e:
            print(f"  ❌ Erro de Análise XML (EPG Inválido) na fonte: {source_url}")
            print(f"     Detalhe do erro: {e}")
            if source_url not in self.failed_urls:
                self.failed_urls.append(source_url)
        except Exception as e:
            print(f"  ❌ Ocorreu um erro inesperado ao processar a fonte {source_url}: {e}")
            if source_url not in self.failed_urls:
                self.failed_urls.append(source_url)

    def finalize_xmltv_and_compress(self, final_output_gz):
        if not os.path.exists(self.temp_xml_file):
            print("\n⚠️ Nenhum dado de EPG foi processado. O arquivo final não foi gerado.")
            return
        with open(self.temp_xml_file, 'a', encoding='utf-8') as f:
            f.write('</tv>\n')
        print(f"\n📦 Comprimindo XML para {final_output_gz}...")
        with open(self.temp_xml_file, 'rb') as f_in, gzip.open(final_output_gz, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(self.temp_xml_file)
        print(f"✅ Arquivo EPG comprimido com sucesso!")

    def consolidate_epgs(self, epg_urls, final_output_gz):
        print(f"\n🔄 Iniciando consolidação de {len(epg_urls)} EPGs...")
        for i, url in enumerate(epg_urls, 1):
            print(f"\n[{i}/{len(epg_urls)}] Processando URL de EPG...")
            xml_content = self.download_epg(url)
            if xml_content:
                self.process_epg_incremental(xml_content, url)
                del xml_content
        self.finalize_xmltv_and_compress(final_output_gz)
        print(f"\n✅ Consolidação de EPG concluída!")
        print(f"📊 Total: {len(self.processed_channels)} canais únicos, {self.total_programmes} programas")

    def print_report(self):
        print("\n" + "="*80)
        print("📊 RELATÓRIO FINAL DE PROCESSAMENTO DE EPG")
        print("="*80)
        clean_successful = [url for url in self.successful_urls if url not in self.failed_urls]

        if clean_successful:
            print(f"\n✅ EPGs processados com sucesso ({len(clean_successful)}):")
            for url in clean_successful:
                print(f"  ✓ {url}")
        if self.failed_urls:
            print(f"\n❌ EPGs que falharam (download ou análise) ({len(self.failed_urls)}):")
            for url in self.failed_urls:
                print(f"  ✗ {url}")
        
        total = len(self.successful_urls)
        if total == 0:
            print("\n🤷 Nenhum EPG foi encontrado ou processado.")
        else:
            success_rate = len(clean_successful) / total * 100
            print(f"\n📈 Taxa de sucesso (processamento completo): {success_rate:.1f}%")
        print("="*80)

def main():
    consolidator = M3uEpgConsolidator()
    
    m3u_sources = [
        "https://github.com/LITUATUI/M3UPT/raw/refs/heads/main/M3U/M3UPT.m3u",
        "https://github.com/aseanic/aseanic.github.io/raw/31810aeb9cc29d671f58a554132e62f07f5a80e3/vod"
    ]
    
    # ✅ Compatível com GitHub Actions
    output_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(output_dir, exist_ok=True)

    playlist_output_file = os.path.join(output_dir, "PLAYLIST.m3u")
    epg_output_file = os.path.join(output_dir, "EPG.xml.gz")

    print("🚀 Iniciando Consolidador de M3U e EPG (v1.2 - GitHub Edition)")
    print(f"🗓️ Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    full_m3u_content = ""
    for i, m3u_url in enumerate(m3u_sources):
        print(f"\n--- Baixando Fonte M3U [{i+1}/{len(m3u_sources)}]: {m3u_url} ---")
        try:
            response = consolidator.session.get(m3u_url, timeout=60)
            response.raise_for_status()
            content = response.text
            if i > 0:
                content = re.sub(r'^#EXTM3U[^\n]*\n?', '', content, count=1)
            full_m3u_content += content + "\n"
            print("  ✅ Conteúdo baixado.")
        except requests.RequestException as e:
            print(f"  ❌ Erro ao baixar M3U: {e}")

    epg_urls = consolidator.extract_epg_urls_from_m3u_content(full_m3u_content)

    with open(playlist_output_file, 'w', encoding='utf-8') as f:
        f.write(full_m3u_content)
    print(f"\n📝 Arquivo de playlist consolidado salvo em: {playlist_output_file}")

    if not epg_urls:
        print("\n❌ Nenhuma URL de EPG válida foi encontrada.")
    else:
        consolidator.consolidate_epgs(epg_urls, epg_output_file)
    
    consolidator.print_report()

    if os.path.exists(playlist_output_file):
        print(f"\n📁 Arquivo de Playlist: {playlist_output_file} ({os.path.getsize(playlist_output_file) / (1024*1024):.2f} MB)")
    if os.path.exists(epg_output_file):
        print(f"📁 Arquivo de EPG: {epg_output_file} ({os.path.getsize(epg_output_file) / (1024*1024):.2f} MB)")

if __name__ == "__main__":
    main()
