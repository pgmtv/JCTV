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
options.add_experimental_option("useAutomationExtension", False)

def handle_cookie_consent(driver):
    """Trata mensagens de cookies e consentimento"""
    try:
        time.sleep(3)
        cookie_selectors = [
            "button[id*=\'accept\']",
            "button[class*=\'accept\']",
            "button[data-testid*=\'accept\']",
            "button:contains(\'Accept\')",
            "button:contains(\'I Accept\')",
            "button:contains(\'Accept All\')",
            "button:contains(\'Agree\')",
            "button:contains(\'OK\')",
            ".cookie-accept",
            ".accept-cookies",
            "#onetrust-accept-btn-handler",
            ".ot-sdk-show-settings",
            "button[aria-label*=\'Accept\']",
            "button[title*=\'Accept\']",
            "button[data-cy*=\'accept\']",
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
                
        close_selectors = [
            "button[aria-label*=\'close\']",
            "button[aria-label*=\'Close\']",
            ".close",
            ".modal-close",
            "button.close",
            "[data-dismiss=\'modal\']",
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
        video_selectors = [
            "video",
            ".video-player",
            ".player-container",
            "[data-testid*=\'video\']",
            ".live-player",
            "iframe[src*=\'player\']",
            "iframe[src*=\'video\']"
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
                src = iframe.get_attribute("src") or ""
                if any(keyword in src.lower() for keyword in ["player", "video", "live", "stream"]):
                    print(f"Iframe {i} parece conter vídeo: {src[:100]}...")
                    driver.switch_to.frame(iframe)
                    video_elements = driver.find_elements(By.TAG_NAME, "video")
                    if video_elements:
                        print(f"Encontrados {len(video_elements)} elementos de vídeo no iframe {i}")
                        for video in video_elements:
                            try:
                                driver.execute_script("arguments[0].play();", video)
                                print(f"Play executado no vídeo do iframe {i}")
                            except Exception:
                                pass
                    driver.switch_to.default_content()
            except Exception as e:
                print(f"Erro ao processar iframe {i}: {e}")
                try:
                    driver.switch_to.default_content()
                except Exception:
                    pass
                    
    except Exception as e:
        print(f"Erro ao tratar iframes: {e}")

def try_play_video(driver):
    """Tenta dar play no vídeo usando vários métodos"""
    try:
        time.sleep(3)
        play_selectors = [
            "button[aria-label*=\'play\']",
            "button[aria-label*=\'Play\']",
            "button[title*=\'play\']",
            "button[title*=\'Play\']",
            "button.play-button",
            ".play-btn",
            ".video-play-button",
            "button[data-testid*=\'play\']",
            ".player-play-button",
            "button.vjs-big-play-button",
            ".vjs-play-control",
            "button[class*=\'play\']",
            "div[class*=\'play\'][role=\'button\']",
            ".poster__play-wrapper",
            "button[aria-label=\'Reproduzir vídeo\']",
            ".playkit-pre-playback-play-button",
            ".playkit-control-button",
            ".play-overlay",
            ".play-icon"
        ]
        
        for selector in play_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", element)
                        print(f"Clicou no botão de play: {selector}")
                        time.sleep(3)
                        return True
            except Exception as e:
                continue
        
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
            
        try:
            driver.execute_script(r"""
                var videos = document.querySelectorAll(\'video\');
                for(var i = 0; i < videos.length; i++) {
                    if(videos[i].paused) {
                        videos[i].play();
                        console.log(\'Play via JavaScript no vídeo\', i);
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
        log_entries = driver.execute_script(r"return window.performance.getEntriesByType(\'resource\');")
        
        m3u8_urls = []
        for entry in log_entries:
            url = entry.get("name", "")
            if ".m3u8" in url:
                m3u8_urls.append(url)
        
        m3u8_urls = list(set(m3u8_urls))
        
        for url in m3u8_urls:
            if any(quality in url.lower() for quality in ["master", "playlist", "index"]):
                return url
                
        if m3u8_urls:
            return m3u8_urls[0]
            
    except Exception as e:
        print(f"Erro ao extrair m3u8 dos logs de rede: {e}")
    
    return None

def extract_m3u8_from_source(driver):
    """Extrai URLs .m3u8 do código fonte da página"""
    try:
        page_source = driver.page_source
        
        m3u8_patterns = [
            r"https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]",
            r"\"(https?://[^"]+\.m3u8[^"]*)\"",
            r"\'(https?://[^\']+\.m3u8[^\']*)\'",
            r"src=\"(https?://[^"]+\.m3u8[^"]*)\"",
            r"src=\\\\'(https?://[^\\']+\.m3u8[^\\']*)\\\\'",
            r"url:\s*[\""](https?://[^\""]+\.m3u8[^\""]*)[""]",
            r"source:\s*[\""](https?://[^\""]+\.m3u8[^\""]*)[""]",
            r"file:\s*[\""](https?://[^\""]+\.m3u8[^\""]*)[""]"
        ]
        
        for pattern in m3u8_patterns:
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], tuple):
                    return matches[0][0] if matches[0][0] else matches[0]
                else:
                    return matches[0]
                    
    except Exception as e:
        print(f"Erro ao extrair m3u8 do código fonte: {e}")
    
    return None

def get_foxnews_video_links(driver, base_url):
    """Coleta links de vídeo da página principal da Fox News."""
    video_links = set()
    try:
        driver.get(base_url)
        time.sleep(5)
        handle_cookie_consent(driver)
        time.sleep(2)

        # Rolar para carregar mais vídeos (pode ser necessário ajustar o número de scrolls)
        for _ in range(5):  # Tenta rolar 5 vezes
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)

        # Encontrar todos os links de vídeo
        # Os links estão dentro de <article class="video-item"> com um <a> href dentro
        video_elements = driver.find_elements(By.CSS_SELECTOR, "article.video-item a")
        for element in video_elements:
            href = element.get_attribute("href")
            if href and "/video/" in href and "foxnews.com" in href:
                video_links.add(href)
        
    except Exception as e:
        print(f"Erro ao coletar links de vídeo da página principal: {e}")
    return list(video_links)

def extract_foxnews_data(url):
    """Função principal para extrair dados da Fox News"""
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.execute_script(r"Object.defineProperty(navigator, \'webdriver\', {get: () => undefined})")
        
        print(f"Acessando: {url}")
        driver.get(url)
        
        time.sleep(5)
        handle_cookie_consent(driver)
        time.sleep(2)
        
        video_loaded = wait_for_video_load(driver)
        if not video_loaded:
            print(f"Vídeo não carregou para {url}")
        
        handle_iframes(driver)
        time.sleep(3)
        
        play_success = try_play_video(driver)
        if play_success:
            print(f"Play executado com sucesso para {url}")
        else:
            print(f"Não conseguiu dar play para {url}")
        
        print(f"Aguardando stream carregar para {url}...")
        time.sleep(20)
        
        m3u8_url = extract_m3u8_from_network(driver)
        
        if not m3u8_url:
            m3u8_url = extract_m3u8_from_source(driver)
        
        if not m3u8_url:
            print(f"Aguardando mais tempo para {url}...")
            time.sleep(30)
            m3u8_url = extract_m3u8_from_network(driver)
            
        if not m3u8_url:
            m3u8_url = extract_m3u8_from_source(driver)
        
        title = driver.title
        
        thumbnail_url = None
        try:
            log_entries = driver.execute_script(r"return window.performance.getEntriesByType(\'resource\');")
            for entry in log_entries:
                url_entry = entry.get("name", "")
                if any(ext in url_entry.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]) and any(keyword in url_entry.lower() for keyword in ["thumb", "preview", "poster"]):
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

def main():
    """Função principal"""
    print("Iniciando extração de streams da Fox News...")
    
    foxnews_video_page = "https://www.foxnews.com/video"
    
    driver_main = None
    video_urls = []
    try:
        driver_main = webdriver.Chrome(options=options)
        video_urls = get_foxnews_video_links(driver_main, foxnews_video_page)
    finally:
        if driver_main:
            driver_main.quit()

    print(f"Encontrados {len(video_urls)} links de vídeo na página principal.")
    
    with open("lista_foxnews.m3u", "w", encoding="utf-8") as output_file:
        output_file.write("#EXTM3U\n")
        
        for url in video_urls:
            try:
                print(f"\n{\'=\'*60}")
                print(f"Processando: {url}")
                print(f"{\'=\'*60}")
                
                title, m3u8_url, thumbnail_url = extract_foxnews_data(url)
                
                if m3u8_url:
                    thumbnail_url = thumbnail_url if thumbnail_url else ""
                    output_file.write(f\'#EXTINF:-1 tvg-logo="{thumbnail_url}" group-title="FOX NEWS VIDEO", {title}\n\')
                    output_file.write(f\'{m3u8_url}\n\')
                    print(f"✅ Sucesso: {url}")
                    print(f"   Título: {title}")
                    print(f"   M3U8: {m3u8_url}")
                else:
                    print(f"❌ M3U8 não encontrado para {url}")
                    
                time.sleep(5)
                
            except Exception as e:
                print(f"❌ Erro ao processar {url}: {e}")
    
    print(f"\n{\'=\'*60}")
    print("Processamento concluído! Arquivo salvo como: lista_foxnews.m3u")
    print(f"{\'=\'*60}")

if __name__ == "__main__":
    main()

