from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import concurrent.futures
import re

# Configurações do Chrome
options = Options()
options.add_argument("--headless")  # Executa sem interface gráfica
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1280,720")
options.add_argument("--disable-infobars")
options.add_argument("--disable-web-security")
options.add_argument("--disable-features=VizDisplayCompositor")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--remote-debugging-port=9222")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

# URLs dos vídeos ABC News
abcnews_urls = [
    "https://abcnews.go.com/live/video/special-live-01/",
    "https://abcnews.go.com/live/video/special-live-02/",
    "https://abcnews.go.com/live/video/special-live-03/",
    "https://abcnews.go.com/live/video/special-live-04/",
    "https://abcnews.go.com/live/video/special-live-05/",
    "https://abcnews.go.com/live/video/special-live-06/",
    "https://abcnews.go.com/live/video/special-live-07/",
    "https://abcnews.go.com/live/video/special-live-08/",
    "https://abcnews.go.com/live/video/special-live-09/",
    "https://abcnews.go.com/live/video/special-live-10/",
    "https://abcnews.go.com/live/video/special-live-11/"
]

def handle_cookie_consent(driver):
    """Trata mensagens de cookies e consentimento"""
    try:
        # Aguarda um pouco para elementos carregarem
        time.sleep(3)
        
        # Possíveis seletores para botões de aceitar cookies
        cookie_selectors = [
            "button[id*='accept']",
            "button[class*='accept']",
            "button[data-testid*='accept']",
            "button:contains('Accept')",
            "button:contains('I Accept')",
            "button:contains('Accept All')",
            "button:contains('Agree')",
            "button:contains('OK')",
            ".cookie-accept",
            ".accept-cookies",
            "#onetrust-accept-btn-handler",
            ".ot-sdk-show-settings",
            "button[aria-label*='Accept']",
            "button[title*='Accept']",
            "button[data-cy*='accept']",
            ".privacy-manager-accept-all",
            ".gdpr-accept",
            ".consent-accept"
        ]
        
        for selector in cookie_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        driver.execute_script("arguments[0].click();", element)
                        print(f"Clicou no botão de cookies: {selector}")
                        time.sleep(2)
                        return True
            except Exception:
                continue
                
        # Tenta fechar modais/overlays genéricos
        close_selectors = [
            "button[aria-label*='close']",
            "button[aria-label*='Close']",
            ".close",
            ".modal-close",
            "button.close",
            "[data-dismiss='modal']",
            ".overlay-close",
            ".popup-close"
        ]
        
        for selector in close_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        driver.execute_script("arguments[0].click();", element)
                        print(f"Fechou modal/overlay: {selector}")
                        time.sleep(1)
                        return True
            except Exception:
                continue
                
    except Exception as e:
        print(f"Erro ao tratar cookies/modals: {e}")
    
    return False

def wait_for_video_load(driver, timeout=30):
    """Aguarda o vídeo carregar completamente"""
    try:
        # Aguarda elementos de vídeo aparecerem
        video_selectors = [
            "video",
            ".video-player",
            ".player-container",
            "[data-testid*='video']",
            ".live-player",
            "iframe[src*='player']",
            "iframe[src*='video']"
        ]
        
        for selector in video_selectors:
            try:
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                print(f"Elemento de vídeo encontrado: {selector}")
                return True
            except TimeoutException:
                continue
                
    except Exception as e:
        print(f"Erro ao aguardar carregamento do vídeo: {e}")
    
    return False

def handle_iframes(driver):
    """Trata iframes que podem conter o player de vídeo"""
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"Encontrados {len(iframes)} iframes")
        
        for i, iframe in enumerate(iframes):
            try:
                # Verifica se o iframe pode conter vídeo
                src = iframe.get_attribute("src") or ""
                if any(keyword in src.lower() for keyword in ['player', 'video', 'live', 'stream']):
                    print(f"Iframe {i} parece conter vídeo: {src[:100]}...")
                    
                    # Muda para o iframe
                    driver.switch_to.frame(iframe)
                    
                    # Procura por elementos de vídeo dentro do iframe
                    video_elements = driver.find_elements(By.TAG_NAME, "video")
                    if video_elements:
                        print(f"Encontrados {len(video_elements)} elementos de vídeo no iframe {i}")
                        
                        # Tenta dar play
                        for video in video_elements:
                            try:
                                driver.execute_script("arguments[0].play();", video)
                                print(f"Play executado no vídeo do iframe {i}")
                            except Exception:
                                pass
                    
                    # Volta para o contexto principal
                    driver.switch_to.default_content()
                    
            except Exception as e:
                print(f"Erro ao processar iframe {i}: {e}")
                # Garante que volta para o contexto principal
                try:
                    driver.switch_to.default_content()
                except Exception:
                    pass
                    
    except Exception as e:
        print(f"Erro ao tratar iframes: {e}")

def try_play_video(driver):
    """Tenta dar play no vídeo usando vários métodos"""
    try:
        # Aguarda um pouco para elementos carregarem
        time.sleep(3)
        
        # Possíveis seletores para botões de play
        play_selectors = [
            "button[aria-label*='play']",
            "button[aria-label*='Play']",
            "button[title*='play']",
            "button[title*='Play']",
            "button.play-button",
            ".play-btn",
            ".video-play-button",
            "button[data-testid*='play']",
            ".player-play-button",
            "button.vjs-big-play-button",
            ".vjs-play-control",
            "button[class*='play']",
            "div[class*='play'][role='button']",
            ".poster__play-wrapper",
            "button[aria-label='Reproduzir vídeo']",
            ".playkit-pre-playback-play-button",
            "button.playkit-control-button",
            ".play-overlay",
            ".play-icon"
        ]
        
        for selector in play_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        # Scroll para o elemento se necessário
                        driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        time.sleep(1)
                        
                        # Tenta clicar usando JavaScript
                        driver.execute_script("arguments[0].click();", element)
                        print(f"Clicou no botão de play: {selector}")
                        time.sleep(3)
                        return True
            except Exception as e:
                continue
        
        # Se não encontrou botão, tenta clicar no vídeo diretamente
        try:
            video_elements = driver.find_elements(By.TAG_NAME, "video")
            for video in video_elements:
                if video.is_displayed():
                    driver.execute_script("arguments[0].click();", video)
                    print("Clicou diretamente no elemento video")
                    time.sleep(3)
                    return True
        except Exception as e:
            print(f"Erro ao clicar no vídeo: {e}")
            
        # Tenta usar JavaScript para dar play
        try:
            driver.execute_script("""
                var videos = document.querySelectorAll('video');
                for(var i = 0; i < videos.length; i++) {
                    if(videos[i].paused) {
                        videos[i].play();
                        console.log('Play via JavaScript no vídeo', i);
                    }
                }
            """)
            print("Tentou dar play via JavaScript")
            time.sleep(3)
            return True
        except Exception as e:
            print(f"Erro ao dar play via JavaScript: {e}")
            
    except Exception as e:
        print(f"Erro geral ao tentar dar play: {e}")
    
    return False

def extract_m3u8_from_network(driver):
    """Extrai URLs .m3u8 dos logs de rede"""
    try:
        # Obtém logs de performance/rede
        log_entries = driver.execute_script("return window.performance.getEntriesByType('resource');")
        
        m3u8_urls = []
        for entry in log_entries:
            url = entry.get('name', '')
            if '.m3u8' in url:
                m3u8_urls.append(url)
        
        # Remove duplicatas e retorna a melhor URL
        m3u8_urls = list(set(m3u8_urls))
        
        # Prioriza URLs que parecem ser de melhor qualidade
        for url in m3u8_urls:
            if any(quality in url.lower() for quality in ['master', 'playlist', 'index']):
                return url
                
        # Se não encontrou URL prioritária, retorna a primeira
        if m3u8_urls:
            return m3u8_urls[0]
            
    except Exception as e:
        print(f"Erro ao extrair m3u8 dos logs de rede: {e}")
    
    return None

def extract_m3u8_from_source(driver):
    """Extrai URLs .m3u8 do código fonte da página"""
    try:
        page_source = driver.page_source
        
        # Padrões regex para encontrar URLs .m3u8
        m3u8_patterns = [
            r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
            r'"(https?://[^"]+\.m3u8[^"]*)"',
            r"'(https?://[^']+\.m3u8[^']*)'",
            r'src="([^"]+\.m3u8[^"]*)"',
            r"src='([^']+\.m3u8[^']*)'",
            r'url:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']'
        ]
        
        for pattern in m3u8_patterns:
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            if matches:
                # Se o padrão captura grupos, pega o primeiro grupo
                if isinstance(matches[0], tuple):
                    return matches[0][0] if matches[0][0] else matches[0]
                else:
                    return matches[0]
                    
    except Exception as e:
        print(f"Erro ao extrair m3u8 do código fonte: {e}")
    
    return None

def extract_abcnews_data(url):
    """Função principal para extrair dados da ABC News"""
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        
        # Configura user agent para parecer mais com navegador real
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print(f"Acessando: {url}")
        driver.get(url)
        
        # Aguarda carregamento inicial
        time.sleep(5)
        
        # Trata mensagens de cookies/consentimento
        handle_cookie_consent(driver)
        time.sleep(2)
        
        # Aguarda vídeo carregar
        video_loaded = wait_for_video_load(driver)
        if not video_loaded:
            print(f"Vídeo não carregou para {url}")
        
        # Trata iframes que podem conter o player
        handle_iframes(driver)
        time.sleep(3)
        
        # Tenta dar play no vídeo
        play_success = try_play_video(driver)
        if play_success:
            print(f"Play executado com sucesso para {url}")
        else:
            print(f"Não conseguiu dar play para {url}")
        
        # Aguarda um tempo para o stream carregar
        print(f"Aguardando stream carregar para {url}...")
        time.sleep(20)
        
        # Tenta extrair .m3u8 dos logs de rede primeiro
        m3u8_url = extract_m3u8_from_network(driver)
        
        # Se não encontrou nos logs, tenta no código fonte
        if not m3u8_url:
            m3u8_url = extract_m3u8_from_source(driver)
        
        # Aguarda mais um pouco se ainda não encontrou
        if not m3u8_url:
            print(f"Aguardando mais tempo para {url}...")
            time.sleep(30)
            m3u8_url = extract_m3u8_from_network(driver)
            
        if not m3u8_url:
            m3u8_url = extract_m3u8_from_source(driver)
        
        # Coleta informações adicionais
        title = driver.title
        
        # Busca thumbnail
        thumbnail_url = None
        try:
            log_entries = driver.execute_script("return window.performance.getEntriesByType('resource');")
            for entry in log_entries:
                url_entry = entry.get('name', '')
                if any(ext in url_entry.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) and any(keyword in url_entry.lower() for keyword in ['thumb', 'preview', 'poster']):
                    thumbnail_url = url_entry
                    break
        except Exception:
            pass
        
        return title, m3u8_url, thumbnail_url
        
    except Exception as e:
        print(f"Erro ao processar {url}: {e}")
        return None, None, None
        
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

# Função para tentar clicar no botão de play (mantida para compatibilidade)
def try_click_play():
    # Esta função foi integrada na função try_play_video
    pass

# Implementação para tentar novamente até 4 vezes se aparecer erro (mantida para compatibilidade)
def retry_on_error(driver, url):
    retry_attempts = 0
    max_retries = 4
    
    while retry_attempts < max_retries:
        try:
            # Verifica se há mensagem de erro e botão "Tentar novamente"
            error_elements = [
                "a[href='javascript:void(0)'][class*='retry']",
                "a:contains('Tentar novamente')",
                ".error-message-container a",
                "a.retry-button",
                "button[class*='retry']",
                "button:contains('Try Again')",
                "button:contains('Retry')"
            ]
            
            retry_button = None
            for selector in error_elements:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if any(keyword in element.text.lower() for keyword in ["tentar novamente", "retry", "try again"]):
                            retry_button = element
                            break
                    if retry_button:
                        break
                except Exception:
                    continue
            
            # Se encontrou botão de retry, clica nele
            if retry_button:
                print(f"Tentativa {retry_attempts + 1}/{max_retries}: Clicando em 'Tentar novamente' para {url}")
                driver.execute_script("arguments[0].click();", retry_button)
                time.sleep(5)
                retry_attempts += 1
            else:
                break
                
        except Exception as e:
            print(f"Erro ao tentar novamente: {e}")
            retry_attempts += 1
            time.sleep(3)

def process_m3u_file(input_url, output_file):
    """Processa arquivo M3U (implementação básica)"""
    pass

def main():
    """Função principal"""
    print("Iniciando extração de streams da ABC News...")
    
    with open("lista_abcnews.m3u", "w", encoding='utf-8') as output_file:
        output_file.write("#EXTM3U\n")
        
        # Processa URLs sequencialmente para evitar sobrecarga
        for url in abcnews_urls:
            try:
                print(f"\n{'='*60}")
                print(f"Processando: {url}")
                print(f"{'='*60}")
                
                title, m3u8_url, thumbnail_url = extract_abcnews_data(url)
                
                if m3u8_url:
                    thumbnail_url = thumbnail_url if thumbnail_url else ""
                    output_file.write(f'#EXTINF:-1 tvg-logo="{thumbnail_url}" group-title="ABC NEWS LIVE", {title}\n')
                    output_file.write(f"{m3u8_url}\n")
                    print(f"✅ Sucesso: {url}")
                    print(f"   Título: {title}")
                    print(f"   M3U8: {m3u8_url}")
                else:
                    print(f"❌ M3U8 não encontrado para {url}")
                    
                # Pausa entre requisições
                time.sleep(5)
                
            except Exception as e:
                print(f"❌ Erro ao processar {url}: {e}")
    
    print(f"\n{'='*60}")
    print("Processamento concluído! Arquivo salvo como: lista_abcnews.m3u")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()

