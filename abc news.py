from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re

# Configurações do Chrome
options = Options()
options.add_argument("--headless")  # Executa sem interface gráfica
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-infobars")
options.add_argument("--disable-web-security")
options.add_argument("--disable-features=VizDisplayCompositor")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--remote-debugging-port=9222")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
)

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
        time.sleep(3)
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
            ".consent-accept",
            "#didomi-notice-agree-button",
            ".cmp-button_button--primary"
        ]

        for selector in cookie_selectors:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                driver.execute_script("arguments[0].click();", element)
                print(f"Clicou no botão de cookies: {selector}")
                time.sleep(2)
                return True
            except (TimeoutException, NoSuchElementException):
                continue

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
                element = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                driver.execute_script("arguments[0].click();", element)
                print(f"Fechou modal/overlay: {selector}")
                time.sleep(1)
                return True
            except (TimeoutException, NoSuchElementException):
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
            "[data-testid*='video']",
            ".live-player",
            "iframe[src*='player']",
            "iframe[src*='video']",
            ".jwplayer",
            ".vjs-tech"
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
    original_window = driver.current_window_handle
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"Encontrados {len(iframes)} iframes")

        for i, iframe in enumerate(iframes):
            try:
                src = iframe.get_attribute("src") or ""
                if any(k in src.lower() for k in ['player', 'video', 'live', 'stream', 'embed', 'youtube', 'vimeo']):
                    print(f"Iframe {i} parece conter vídeo: {src[:100]}...")
                    driver.switch_to.frame(iframe)
                    video_elements = driver.find_elements(By.TAG_NAME, "video")
                    if video_elements:
                        print(f"Encontrados {len(video_elements)} vídeos no iframe {i}")
                        for video in video_elements:
                            try:
                                driver.execute_script("arguments[0].play();", video)
                                print(f"Play no vídeo do iframe {i}")
                            except Exception:
                                pass
                    driver.switch_to.default_content()
            except Exception as e:
                print(f"Erro no iframe {i}: {e}")
                driver.switch_to.default_content()
    except Exception as e:
        print(f"Erro ao tratar iframes: {e}")
    finally:
        driver.switch_to.window(original_window)


def try_play_video(driver):
    """Tenta dar play no vídeo"""
    try:
        time.sleep(3)
        play_selectors = [
            "button[aria-label*='play']",
            "button[title*='play']",
            ".play-btn",
            ".video-play-button",
            ".player-play-button",
            "button.vjs-big-play-button",
            ".vjs-play-control",
            ".jw-icon-playback",
            ".fp-ui.fp-engine",
            ".bmpui-ui-overlay",
            ".shaka-play-button"
        ]
        for selector in play_selectors:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", element)
                print(f"Clicou no botão de play: {selector}")
                time.sleep(3)
                return True
            except (TimeoutException, NoSuchElementException):
                continue

        videos = driver.find_elements(By.TAG_NAME, "video")
        for video in videos:
            if video.is_displayed():
                driver.execute_script("arguments[0].click();", video)
                print("Clicou diretamente no vídeo")
                return True

        driver.execute_script("""
            var vids = document.querySelectorAll('video');
            for (var i=0;i<vids.length;i++){ if(vids[i].paused){vids[i].play();} }
        """)
        print("Play via JavaScript executado")
        return True
    except Exception as e:
        print(f"Erro ao tentar play: {e}")
    return False


def extract_m3u8_from_network(driver):
    """Extrai URLs .m3u8 dos logs de rede"""
    try:
        time.sleep(5)
        log_entries = driver.execute_script("return window.performance.getEntriesByType('resource');")
        m3u8_urls = []
        for entry in log_entries:
            url = entry.get('name', '')
            if '.m3u8' in url:
                m3u8_urls.append(url)
        m3u8_urls = list(set(m3u8_urls))
        for url in m3u8_urls:
            if any(k in url.lower() for k in ['master', 'playlist', 'index', 'chunklist']):
                return url
        if m3u8_urls:
            return m3u8_urls[0]
    except Exception as e:
        print(f"Erro ao extrair m3u8 dos logs: {e}")
    return None


def extract_m3u8_from_source(driver):
    """Extrai URLs .m3u8 do código-fonte"""
    try:
        src = driver.page_source
        m3u8_patterns = [
            r"(https?://[^\s\"'<>]+?\.m3u8[^\s\"'<>]*?)",  # corrigido
            r'"(https?://[^"]+?\.m3u8[^"]*)"',
            r"'(https?://[^']+?\.m3u8[^']*)'",
            r'src="([^"]+?\.m3u8[^"]*)"',
            r"src='([^']+?\.m3u8[^']*)'",
            r'url:\s*["\']([^"\']+?\.m3u8[^"\']*)["\']',
            r'source:\s*["\']([^"\']+?\.m3u8[^"\']*)["\']',
            r'file:\s*["\']([^"\']+?\.m3u8[^"\']*)["\']',
            r'"hls_url":"(.*?\.m3u8.*?)"',
            r'"src":"(.*?\.m3u8.*?)"'
        ]
        for pattern in m3u8_patterns:
            matches = re.findall(pattern, src, re.IGNORECASE)
            if matches:
                return matches[0]
    except Exception as e:
        print(f"Erro ao extrair m3u8 do código-fonte: {e}")
    return None


def extract_abcnews_data(url):
    """Processa uma URL e extrai título, m3u8 e thumbnail"""
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print(f"Acessando: {url}")
        driver.get(url)
        time.sleep(5)

        handle_cookie_consent(driver)
        wait_for_video_load(driver)
        handle_iframes(driver)
        try_play_video(driver)

        print("Aguardando stream carregar...")
        time.sleep(15)

        m3u8_url = extract_m3u8_from_network(driver)
        if not m3u8_url:
            m3u8_url = extract_m3u8_from_source(driver)

        title = driver.title
        thumbnail_url = None
        try:
            thumb = driver.find_element(By.CSS_SELECTOR, "meta[property='og:image']")
            thumbnail_url = thumb.get_attribute("content")
        except NoSuchElementException:
            pass

        return title, m3u8_url, thumbnail_url
    except Exception as e:
        print(f"Erro ao processar {url}: {e}")
        return None, None, None
    finally:
        if driver:
            driver.quit()


def main():
    print("Iniciando extração de streams da ABC News...")
    with open("lista_abcnews.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for url in abcnews_urls:
            print("=" * 60)
            print(f"Processando: {url}")
            title, m3u8_url, thumb = extract_abcnews_data(url)
            if m3u8_url:
                thumb = thumb or ""
                f.write(f'#EXTINF:-1 tvg-logo="{thumb}" group-title="ABC NEWS LIVE", {title}\n')
                f.write(f"{m3u8_url}\n")
                print(f"✅ Sucesso: {title}\n{m3u8_url}")
            else:
                print(f"❌ M3U8 não encontrado para {url}")
            time.sleep(5)
    print("✅ Arquivo 'lista_abcnews.m3u' gerado com sucesso!")


if __name__ == "__main__":
    main()
