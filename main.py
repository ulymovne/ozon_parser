from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
import time
import json
import random
import pandas as pd

URL_CATEGORY = "https://www.ozon.ru/category/smartfony-15502/?sorting=rating"
URL_PRODUCT = "https://www.ozon.ru/api/composer-api.bx/page/json/v2?url={}?layout_container=pdpPage2column&layout_page_index=2"
COUNT_PARSE_PRODUCT = 100


def init():
    """
    Инициализация вебдрайвера, возвращает подготовленный экземпляр Chrome.

    :return:
    """
    options = ChromeOptions()
    options.add_argument("start-maximized")
    # options.add_argument("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36")
    options.headless = True
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    browser = Chrome(executable_path='chromedriver', options=options)
    stealth(browser,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Linux",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )
    return browser


def parse_product_page(browser, url):
    """
    Парсинг json-страницы товара.
    На входе подготовленный экземпляр Chrome и адрес json страницы смартфона.
    На выходе версия OS у этого смартфона.

    :param browser:
    :param url:
    :return:
    """
    browser.get(url)
    browser.implicitly_wait(5)
    time.sleep(random.randint(4, 7))
    data_json = json.loads(browser.find_element(By.XPATH, '//pre').text)
    browser.implicitly_wait(3)
    os_characteristics = []
    for key, value in data_json['widgetStates'].items():
        if 'webCharacteristics' in key:
            product_char = json.loads(value)
            for characteristic in product_char['characteristics']:
                if 'title' in characteristic and characteristic['title'].lower() in ('общие', 'основные'):
                    os_characteristics.extend(characteristic['short'])
            break

    version_os = name_os = ''
    for oper_sys in os_characteristics:
        if 'версия' in oper_sys['name'].lower():
            version_os = oper_sys['values'][0]['text']
        elif 'операционная система' in oper_sys['name'].lower():
            name_os = oper_sys['values'][0]['text']
    if not version_os:
        version_os = name_os

    return version_os


def parse_catalog_page(browser, url, page):
    """
    Парсинг страницы каталога товаров, для получения адресов смартфонов.
    На входе подготовленный экземпляр Chrome, адрес каталога и номер страницы.
    На выходе список url смартфонов с этой страницы,
    в соответствии с порядком критерия поиска и без рекламных смарфтонов.

    :param browser:
    :param url:
    :param page:
    :return:
    """
    url_list = url.split('?')
    if len(url_list) == 1:
        url_full = url + f'?page={page}'
    else:
        url_full = f'?page={page}&'.join(url_list)

    browser.get(url_full)
    browser.implicitly_wait(5)
    time.sleep(random.randint(3, 8))
    datalayer = browser.execute_script("return window.__NUXT__")
    browser.implicitly_wait(2)
    part_layer = datalayer['state']['trackingPayloads']
    part_layer_dict = {}
    for key, value in part_layer.items():
        part_layer_dict[key] = json.loads(value)
    phone_link = []
    for key, product in part_layer_dict.items():
        # advId - признак рекламы
        if 'product_type' in product and 'advId' not in product:
            if product['product_type'] == 'product':
                phone_link.append(product['link'])

    phone_link = [*map(lambda x: x.split('?')[0], phone_link)]

    return phone_link

def parse_catalog(browser, length):
    """
    Общая функция парсинга страниц каталога.
    На подготовленный экземпляр Chrome и количество смартфонов необходимых для статитстики.
    На выходе список url смартфонов, в количестве не менее length.

    :param browser:
    :param length:
    :return:
    """
    products = []
    page = 1
    while len(products) < length:
        try:
            products.extend(parse_catalog_page(browser, url=URL_CATEGORY, page=page))
            print(f'Page {page} - ok, length products_list = {len(products)}')
            page += 1
        except Exception as e:
            print(f'Error download page - {page}')
            print(e)
            break
    return products

def parse_products(browser, products_list):
    """
    Общая функция парсинга страниц товаров.
    На подготовленный экземпляр Chrome и список url смартфонов.
    На выходе список типов операционной системы у этих смартфонов.

    :param browser:
    :param products_list:
    :return:
    """
    operation_systems = []
    for product in products_list:
        url = URL_PRODUCT.format(product)
        version_os = parse_product_page(browser, url)
        if not version_os:
            print('Version OS is not:')
            print(url)
        else:
            operation_systems.append(version_os)
    return operation_systems

def main():
    browser = init()
    try:
        # download url products
        products_list = parse_catalog(browser, COUNT_PARSE_PRODUCT)

        with open('products.json', 'w', encoding='utf-8') as file:
            json.dump(products_list, file, indent=4, ensure_ascii=False)
        print('Download products_list: OK')

        time.sleep(3)
        # parse OS from products_list
        operation_systems_list = parse_products(browser, products_list)

        with open('os.json', 'w', encoding='utf-8') as file:
            json.dump(operation_systems_list, file, indent=4, ensure_ascii=False)
        print('download os_phone data - ok')

        # get statistics
        df = pd.DataFrame(operation_systems_list[:COUNT_PARSE_PRODUCT], columns=['os_ver'])
        value_counts = df['os_ver'].value_counts()

        with open('os.txt', 'w', encoding='utf-8') as file:
            for i in value_counts.index:
                file.write('{:<15}-{:>4}\n'.format(i, value_counts[i]))
        print('Successful!')

    except Exception as e:
        print(e)
    finally:
        browser.close()
        browser.quit()

if __name__ == '__main__':
    main()
