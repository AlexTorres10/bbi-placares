from playwright.sync_api import sync_playwright
import time

def bbi_placares(page, url):
    print(f"Acessando primeiro app: {url}")
    page.goto(url)
    
    # XPaths dos comboboxes
    xpaths = [
        '//*[@id="root"]/div[1]/div[1]/div/div[2]/div/section/div[1]/div/div[2]/div/div/div/div[1]',
        '//*[@id="root"]/div[1]/div[1]/div/div[2]/div/section/div[1]/div/div[3]/div/div/div/div[1]',
        '//*[@id="root"]/div[1]/div[1]/div/div[2]/div/section/div[1]/div/div[4]/div/div/div/div[1]'
    ]

    for xpath in xpaths:
        try:
            # Espera o combobox estar visível e clica para abrir opções
            page.wait_for_selector(xpath, timeout=10000)
            page.click(xpath)
            time.sleep(1)  # espera as opções aparecerem

            # As opções costumam estar em divs dentro de um menu aberto.
            # Vamos tentar pegar a primeira opção visível e clicar nela.
            options_xpath = '//div[@role="listbox"]//div[@role="option"]'
            
            # Espera as opções aparecerem
            page.wait_for_selector(options_xpath, timeout=10000)
            options = page.locator(options_xpath)
            
            if options.count() > 0:
                options.first.click()
                print(f"Selecionada primeira opção do combobox {xpath}")
            else:
                print(f"Nenhuma opção encontrada para combobox {xpath}")

            time.sleep(1)  # espera após seleção
        except Exception as e:
            print(f"Erro ao interagir com combobox {xpath}: {e}")


def cotefacil(page, url):
    print(f"Acessando terceiro app: {url}")
    page.goto(url)
    
    try:
        # Espera e interage com o campo login
        page.wait_for_selector('//*[@id="text_input_1"]', timeout=10000)
        page.fill('//*[@id="text_input_1"]', "usuario_exemplo")
        print("Escreveu no campo login.")

        # Espera e interage com o campo senha
        page.wait_for_selector('//*[@id="text_input_2"]', timeout=10000)
        page.fill('//*[@id="text_input_2"]', "senha_exemplo")
        print("Escreveu no campo senha.")
    except Exception as e:
        print(f"Erro ao interagir no terceiro app: {e}")


# URLs dos seus apps Streamlit
app1_url = "https://bbi-placares.streamlit.app/"
app2_url = "https://cadastro-idpb-acamp-2025.streamlit.app/"
app3_url = "https://cotefacilsaude.streamlit.app/"

# Executa o Playwright
with sync_playwright() as p:
    # Configurações do browser (equivalente às opções do Chrome)
    browser = p.chromium.launch(
        headless=True,  # roda sem abrir janela
        args=[
            '--no-sandbox',
            '--disable-dev-shm-usage'
        ]
    )
    
    # Cria um novo contexto do browser
    context = browser.new_context()
    page = context.new_page()
    
    try:
        bbi_placares(page, app1_url)
        time.sleep(3)
        cotefacil(page, app3_url)
    finally:
        browser.close()