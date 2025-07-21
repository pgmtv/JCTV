import requests
import gzip
import lzma # Importar lzma
import re
import os

def download_content(url):
    """Baixa o conteúdo de uma URL e retorna como string, descompactando se for gzip ou xz."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        if url.endswith(".gz"):
            return gzip.decompress(response.content).decode("utf-8")
        elif url.endswith(".xz"):
            return lzma.decompress(response.content).decode("utf-8") # Descompressão XZ
        else:
            return response.text
    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar {url}: {e}")
        return None
    except lzma.LZMAError as e:
        print(f"Erro ao descompactar XZ de {url}: {e}")
        return None

def extract_epg_from_m3u(m3u_content):
    """Extrai URLs de EPG de conteúdo M3U."""
    epg_urls = []
    # Procura por atributos tvg-url ou url-tvg que apontam para arquivos EPG
    matches = re.findall(r'url-tvg="(.*?)"|tvg-url="(.*?)"', m3u_content)
    for match in matches:
        for url_group in match:
            if url_group:
                # Divide a string por vírgulas para lidar com múltiplos URLs
                individual_urls = [u.strip() for u in url_group.split(',')] # Corrigido para splitar URLs separadas por vírgula
                for url in individual_urls:
                    if url and (url.endswith('.xml') or url.endswith('.xml.gz') or url.endswith('.xml.xz')):
                        epg_urls.append(url)
    return list(set(epg_urls)) # Retorna URLs únicas

def merge_epg_data(epg_data_list):
    """Mescla dados de EPG XML."""
    merged_xml = '<tv>\n'
    for epg_xml in epg_data_list:
        # Extrai tags <channel> e <programme>
        channels = re.findall(r'<channel.+?</channel>', epg_xml, re.DOTALL)
        programmes = re.findall(r'<programme.+?</programme>', epg_xml, re.DOTALL)

        for channel in channels:
            merged_xml += channel + '\n'
        for programme in programmes:
            merged_xml += programme + '\n'
    merged_xml += '</tv>'
    return merged_xml

def compress_epg(epg_xml):
    """Comprime dados de EPG XML para .xml.gz."""
    compressed_data = gzip.compress(epg_xml.encode('utf-8'))
    return compressed_data

def main():
    m3u_urls = [
        "https://drive.usercontent.google.com/u/0/uc",
        "https://github.com/aseanic/aseanic.github.io/raw/31810aeb9cc29d671f58a554132e62f07f5a80e3/vod",
    ]
    output_file = "/content/drive/MyDrive/EPG.xml.gz" # Caminho de saída corrigido para o diretório home
    epg_urls_to_process = []
    epg_data_list = []

    # Processar cada URL M3U
    for m3u_url in m3u_urls:
        print(f"Processando URL M3U: {m3u_url}")
        m3u_content = download_content(m3u_url)
        if m3u_content:
            extracted_epg_urls = extract_epg_from_m3u(m3u_content)
            epg_urls_to_process.extend(extracted_epg_urls)
        else:
            print(f"Não foi possível baixar o conteúdo M3U de {m3u_url}. Tentando usar como EPG diretamente.")
            # Se não for um M3U válido ou não puder ser baixado, tenta tratar como EPG XML diretamente
            epg_content = download_content(m3u_url)
            if epg_content:
                epg_data_list.append(epg_content)

    # Processar URLs de EPG extraídas ou fornecidas diretamente
    for epg_url in epg_urls_to_process:
        print(f"Baixando EPG de: {epg_url}")
        epg_content = download_content(epg_url)
        if epg_content:
            epg_data_list.append(epg_content)

    if not epg_data_list:
        print("Nenhum dado de EPG para mesclar.")
        return

    merged_epg_xml = merge_epg_data(epg_data_list)
    compressed_epg = compress_epg(merged_epg_xml)

    # Certificar-se de que o diretório de saída existe
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    with open(output_file, 'wb') as f:
        f.write(compressed_epg)
    print(f"EPG mesclado e salvo em: {output_file}")

if __name__ == '__main__':
    main()

