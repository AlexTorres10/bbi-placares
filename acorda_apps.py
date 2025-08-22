from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

def bbi_placares(driver, url):
    print(f"Acessando primeiro app: {url}")
    driver.get(url)
    wait = WebDriverWait(driver, 10)

    # XPaths dos comboboxes
    xpaths = [
        '//*[@id="root"]/div[1]/div[1]/div/div[2]/div/section/div[1]/div/div[2]/div/div/div/div[1]',
        '//*[@id="root"]/div[1]/div[1]/div/div[2]/div/section/div[1]/div/div[3]/div/div/div/div[1]',
        '//*[@id="root"]/div[1]/div[1]/div/div[2]/div/section/div[1]/div/div[4]/div/div/div/div[1]'
    ]

    for xpath in xpaths:
        try:
            # Espera o combobox estar clicável e clica para abrir opções
            combobox = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            combobox.click()
            time.sleep(1)  # espera as opções aparecerem

            # As opções costumam estar em divs dentro de um menu aberto.
            # Vamos tentar pegar a primeira opção visível e clicar nela.
            # Ajuste a lógica se seu app usar outro padrão.

            options_xpath = '//div[@role="listbox"]//div[@role="option"]'
            options = wait.until(EC.presence_of_all_elements_located((By.XPATH, options_xpath)))

            if options:
                options[0].click()
                print(f"Selecionada primeira opção do combobox {xpath}")
            else:
                print(f"Nenhuma opção encontrada para combobox {xpath}")

            time.sleep(1)  # espera após seleção
        except Exception as e:
            print(f"Erro ao interagir com combobox {xpath}: {e}")

def acamp2025(driver, url):
    print(f"Acessando segundo app: {url}")
    driver.get(url)
    wait = WebDriverWait(driver, 10)

    try:
        input_nome = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="text_input_1"]')))
        input_nome.clear()
        input_nome.send_keys("Nome Exemplo")
        print("Escreveu no campo nome.")

        input_telefone = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="text_input_3"]')))
        input_telefone.clear()
        input_telefone.send_keys("11999999999")
        print("Escreveu no campo telefone.")
    except Exception as e:
        print(f"Erro ao interagir no segundo app: {e}")

def cotefacil(driver, url):
    print(f"Acessando terceiro app: {url}")
    driver.get(url)
    wait = WebDriverWait(driver, 10)

    try:
        input_login = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="text_input_1"]')))
        input_login.clear()
        input_login.send_keys("usuario_exemplo")
        print("Escreveu no campo login.")

        input_senha = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="text_input_2"]')))
        input_senha.clear()
        input_senha.send_keys("senha_exemplo")
        print("Escreveu no campo senha.")
    except Exception as e:
        print(f"Erro ao interagir no terceiro app: {e}")


# URLs dos seus apps Streamlit
app1_url = "https://bbi-placares.streamlit.app/"
app2_url = "https://cadastro-idpb-acamp-2025.streamlit.app/"
app3_url = "https://cotefacilsaude.streamlit.app/"

options = Options()
options.headless = True  # roda sem abrir janela
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

try:
    bbi_placares(driver, app1_url)
    time.sleep(3)
    acamp2025(driver, app2_url)
    time.sleep(3)
    cotefacil(driver, app3_url)
finally:
    driver.quit()
