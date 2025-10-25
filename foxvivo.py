from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import re

# ===========================
# CONFIGURAÇÕES DO CHROME
# ===========================
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-infobars")
options.add_argument("--disable-web-security")
options.add_argument("--window-size=1280,720")
options.add_argument("--remote-debugging-port=9222")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)


# ===========================
# FUNÇÕES AUXILIARES
# ===========================
def handle_cookie_consent(driver):
    """Tenta fechar popups ou aceitar cookies."""
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
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    driver.execute_script("arguments[0].click();", element)
                    print(f"Clicou no botão de cookies: {selector}")
                    time.sleep(1)
                    return True

        close_selectors = [
            "button[aria-label*=\'close\']",
            ".close", ".modal-close", "button.close",
            "[data-dismiss=\'modal\']", ".overlay-close", ".popup-close"
        ]

        for selector in close_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    driver.execute_script("arguments[0].click();", element)
                    print(f"Fechou modal/overlay: {selector}")
                    time.sleep(1)
                    return True
    except Exception as e:
        print(f"Erro ao tratar cookies/modals: {e}")

    return False


def wait_for_video_load(driver, timeout=30):
    """Aguarda até o vídeo carregar."""
    video_selectors = [
        "video", ".video-player", ".player-container",
        "[data-testid*=\'video\']", ".live-player",
        "iframe[src*=\'player\']", "iframe[src*=\'video\']"
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
    return False


def handle_iframes(driver):
    """Procura players dentro de iframes."""
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"Encontrados {len(iframes)} iframes")
        for i, iframe in enumerate(iframes):
            src = iframe.get_attribute("src") or ""
            if any(k in src.lower() for k in ["player", "video", "live", "stream"]):
                print(f"Iframe {i} parece conter vídeo: {src[:100]}...")
                driver.switch_to.frame(iframe)
                videos = driver.find_elements(By.TAG_NAME, "video")
                for v in videos:
                    try:
                        driver.execute_script("arguments[0].play();", v)
                    except Exception:
                        pass
                driver.switch_to.default_content()
    except Exception as e:
        print(f"Erro ao tratar iframes: {e}")


def try_play_video(driver):
    """Tenta dar play manual no vídeo."""
    try:
        time.sleep(3)
        play_selectors = [
            "button[aria-label*=\'play\']", "button[title*=\'play\']",
            "button.play-button", ".play-btn", ".video-play-button",
            ".player-play-button", "button.vjs-big-play-button",
            ".vjs-play-control", ".poster__play-wrapper",
            ".playkit-pre-playback-play-button", ".play-overlay"
        ]

        for selector in play_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                if el.is_displayed() and el.is_enabled():
                    driver.execute_script("arguments[0].scrollIntoView(true);", el)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", el)
                    print(f"Clicou no botão de play: {selector}")
                    time.sleep(3)
                    return True

        # Clicar diretamente no elemento <video>
        videos = driver.find_elements(By.TAG_NAME, "video")
        for v in videos:
            if v.is_displayed():
                driver.execute_script("arguments[0].click();", v)
                print("Clicou diretamente no elemento video")
                time.sleep(3)
                return True

        # Play via JavaScript
        driver.execute_script("""
            var videos = document.querySelectorAll(\'video\');
            for (var i = 0; i < videos.length; i++) {
                if (videos[i].paused) videos[i].play();
            }
        """)
        print("Tentou dar play via JavaScript")
        time.sleep(3)
        return True
    except Exception as e:
        print(f"Erro ao tentar dar play: {e}")
    return False


def extract_m3u8_from_network(driver):
    """Extrai URLs .m3u8 do log de rede."""
    try:
        logs = driver.execute_script("return window.performance.getEntriesByType(\'resource\');")
        urls = [l.get("name", "") for l in logs if ".m3u8" in l.get("name", "")]
        urls = list(set(urls))
        for u in urls:
            if any(x in u.lower() for x in ["master", "playlist", "index"]):
                return u
        if urls:
            return urls[0]
    except Exception as e:
        print(f"Erro ao extrair m3u8 dos logs: {e}")
    return None


def extract_m3u8_from_source(driver):
    """Extrai URLs .m3u8 do código-fonte."""
    try:
        html = driver.page_source
        m3u8_patterns = [
            r"https?://[^\s\"\'<>]+?\.m3u8[^\s\"\'<>]*",
            r"\"(https?://[^\"]+?\.m3u8[^\"]*)\"",
            r"\'(https?://[^\\]+?\.m3u8[^\\]*)\'",
            r"src=\"(https?://[^\"]+?\.m3u8[^\"]*)\"",
            r"src=\\'(https?://[^\\]+?\.m3u8[^\\]*)\\'",
            r"url:\s*['\"](https?://[^'\"]+?\.m3u8[^'\"]*)['\"]",
            r"source:\s*['\"](https?://[^'\"]+?\.m3u8[^'\"]*)['\"]",
            r"file:\s*['\"](https?://[^'\"]+?\.m3u8[^'\"]*)['\"]"
        ]

        for pattern in m3u8_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], tuple):
                    return matches[0][0] if matches[0][0] else matches[0]
                return matches[0]
    except Exception as e:
        print(f"Erro ao extrair m3u8 do HTML: {e}")
    return None


def get_foxnews_live_streams(driver):
    """Obtém URLs de streams ao vivo da Fox News."""
    live_urls = set()
    final_filtered_urls = set() # Inicializar aqui
    potential_live_pages = [
        "https://www.foxnews.com/live",
        "https://www.foxnews.com/shows/fox-news-live",
        "https://www.foxnews.com/go",
        "https://www.foxnews.com/video" # Incluir a página de vídeo geral para mais cobertura
    ]

    for url in potential_live_pages:
        try:
            print(f"Navegando para página potencial de live: {url}")
            driver.get(url)
            time.sleep(5)
            handle_cookie_consent(driver)

            # Tentar encontrar elementos que indiquem um stream ao vivo
            # Isso pode variar, então usaremos vários seletores
            live_selectors = [
                "a[href*=\"/live\"][href*=\".m3u8\"]",
                "a[href*=\"/live-stream\"]",
                "div[data-component-name=\"LivePlayer\"] a",
                "video[src*=\"live\"]",
                "iframe[src*=\"live\"]",
                "span.live-badge", # Exemplo de um badge \'Ao Vivo\'
                "div.on-air-now", # Exemplo de um contêiner \'No Ar Agora\'
                "div[data-qa-label=\"on-air-now\"]"
            ]

            for selector in live_selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    href = el.get_attribute("href") or el.get_attribute("src")
                    if href and (".m3u8" in href or "live" in href.lower()):
                        live_urls.add(href)
                        print(f"Encontrado potencial stream ao vivo: {href}")

            # Tentar extrair m3u8 diretamente da rede ou source nessas páginas
            m3u8_from_network = extract_m3u8_from_network(driver)
            if m3u8_from_network and "live" in m3u8_from_network.lower():
                live_urls.add(m3u8_from_network)
                print(f"M3U8 ao vivo encontrado via rede: {m3u8_from_network}")
            
            m3u8_from_source = extract_m3u8_from_source(driver)
            if m3u8_from_source and "live" in m3u8_from_source.lower():
                live_urls.add(m3u8_from_source)
                print(f"M3U8 ao vivo encontrado via source: {m3u8_from_source}")

            # Verificar se há indicadores visuais de "On Air Now" ou "Live" na página
            on_air_indicators = driver.find_elements(By.XPATH, "//*[contains(text(), \'On Air Now\') or contains(text(), \'LIVE\')] | //*[contains(@class, \'live-badge\') or contains(@class, \'on-air-now\')] | //*[contains(@class, \'live-tag\')] | //*[contains(@class, \'live-label\')]")
            
            # Se a página contém um indicador "On Air Now" ou "LIVE", consideramos os URLs encontrados nela
            if on_air_indicators:
                print(f"Indicador \'On Air Now\' ou \'LIVE\' encontrado na página {url}.")
                # Adicionar todos os URLs de stream encontrados para esta página ao conjunto final
                for u in live_urls:
                    # Refinar ainda mais: garantir que o URL em si contenha "live" ou seja um m3u8
                    if "live" in u.lower() or ".m3u8" in u.lower():
                        # Evitar URLs que parecem ser VODs, a menos que explicitamente marcados como live
                        if "/video/" in u.lower() and not ("live" in u.lower().split("/video/")[-1] or "live-stream" in u.lower()):
                            continue # Ignorar se for um vídeo gravado sem indicador claro de live
                        final_filtered_urls.add(u)
            else:
                print(f"Nenhum indicador \'On Air Now\' ou \'LIVE\' encontrado na página {url}. Ignorando URLs desta página.")

        except Exception as e:
            print(f"Erro ao processar URL de live {url}: {e}")

    return list(final_filtered_urls)


def extract_foxnews_data(url):
    """Extrai título, .m3u8 e thumbnail de um vídeo Fox News."""
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, \'webdriver\', {get: () => undefined})")

        print(f"Acessando: {url}")
        driver.get(url)
        time.sleep(5)
        handle_cookie_consent(driver)
        wait_for_video_load(driver)
        handle_iframes(driver)
        try_play_video(driver)
        time.sleep(15)

        m3u8 = extract_m3u8_from_network(driver) or extract_m3u8_from_source(driver)
        title = driver.title

        thumb = None
        logs = driver.execute_script("return window.performance.getEntriesByType(\'resource\');")
        for entry in logs:
            name = entry.get("name", "")
            if any(ext in name.lower() for ext in [".jpg", ".png", ".webp"]) and "thumb" in name.lower():
                thumb = name
                break

        return title, m3u8, thumb
    except Exception as e:
        print(f"Erro ao processar {url}: {e}")
        return None, None, None
    finally:
        if driver:
            driver.quit()


# ===========================
# FUNÇÃO PRINCIPAL
# ===========================
def main():
    print("Iniciando extração de streams ao vivo da Fox News...")

    driver_main = webdriver.Chrome(options=options)
    live_stream_urls = get_foxnews_live_streams(driver_main)
    driver_main.quit()

    print(f"Foram encontrados {len(live_stream_urls)} streams ao vivo.")

    with open("lista_foxnews.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for url in live_stream_urls:
            print("=" * 60)
            print(f"Processando: {url}")
            print("=" * 60)
            # Para streams ao vivo, o título pode ser genérico, e o m3u8_url já é o próprio url
            # Vamos tentar obter um título melhor se possível, mas o foco é o URL do stream
            title = f"Fox News Live Stream {live_stream_urls.index(url) + 1}"
            m3u8_url = url
            thumb = None # Pode ser difícil obter um thumbnail específico para streams ao vivo sem uma API

            if m3u8_url:
                thumb = thumb or ""
                f.write(f\'#EXTINF:-1 tvg-logo="{thumb}" group-title="FOX NEWS VIDEO", {title}\n\')
                f.write(f"{m3u8_url}\n")
                print(f"✅ Sucesso: {title}")
            else:
                print(f"❌ M3U8 não encontrado para {url}")

            time.sleep(5)

    print("\n" + "=" * 60)
    print("✅ Processamento concluído! Arquivo salvo como: lista_foxnews.m3u")
    print("=" * 60)


if __name__ == "__main__":
    main()
