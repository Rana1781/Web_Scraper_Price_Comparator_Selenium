from selenium.common import exceptions
from msedge.selenium_tools import Edge, EdgeOptions
import pandas as pd
from fuzzywuzzy import fuzz

# driver setup
options = EdgeOptions()
options.use_chromium = True
options.headless = True
driver = Edge(options=options)

# Scraping Amazon Product Data

amazon_products = {}


def generate_url_amazon(search_term, page):
    base_template = 'https://www.amazon.com/s?k={}&ref=nb_sb_noss'
    search_term = search_term.replace(' ', '+')
    stem = base_template.format(search_term)
    url_template = stem + '&page={}'
    if page == 1:
        return stem
    else:
        return url_template.format(page)


def extract_card_data_amazon(card):
    try:
        description = card.find_element_by_xpath('.//h2/a').text.strip()
        price = card.find_element_by_xpath('.//span[@class="a-price-whole"]').text
        price = float(price)
        if description in amazon_products.keys() and price < amazon_products[description]:
            del amazon_products[description]
            amazon_products[description] = price
        else:
            amazon_products[description] = price

    except exceptions.NoSuchElementException:
        pass


def collect_product_cards_from_page_amazon(driver):
    cards = driver.find_elements_by_xpath('//div[@data-component-type="s-search-result"]')
    return cards


# scraping ebay product data

def generate_url_ebay(search_term, page):
    # 'https://www.ebay.com/sch/i.html?_from=R40&_trksid=m570.l1313&_nkw={}&_sacat=0'
    base_template = 'https://www.ebay.com/sch/i.html?_from=R40&_trksid=p2334524.m570.l1313&_nkw={}&_sacat=0&LH_TitleDesc=0&_osacat=0&_odkw={}'
    search_term = search_term.replace(' ', '+')
    stem = base_template.format(search_term, search_term)
    if page == 1:
        return stem
    else:
        next_page_template = 'https://www.ebay.com/sch/i.html?_from=R40&_nkw={}&_sacat=0&_pgn={}'
        next_page_url = next_page_template.format(search_term, page)
        return next_page_url


products_ebay = {}


def collect_product_cards_from_page_ebay(driver):
    cards = driver.find_elements_by_xpath('//li[@class="s-item    "]')
    cards2 = driver.find_elements_by_xpath('//li[@class="s-item    s-item--watch-at-corner"]')
    return cards + cards2


def extract_card_data_ebay(card):
    try:
        product_title = card.find_element_by_xpath('.//h3[@class="s-item__title s-item__title--has-tags"]').text
        price = card.find_element_by_xpath('.//span[@class="s-item__price"]').text
        temp_list = price.split(' ')
        price = float(temp_list[0][1:len(temp_list[0])])

        if product_title in products_ebay.keys() and price < products_ebay[product_title]:
            del products_ebay[product_title]
            products_ebay[product_title] = price
        else:
            products_ebay[product_title] = price

    except exceptions.NoSuchElementException:
        pass

    try:
        product_title2 = card.find_element_by_xpath(".//h3[@class='s-item__title']").text
        price2 = card.find_element_by_xpath('.//span[@class="s-item__price"]').text
        temp_list = price2.split(' ')
        price2 = float(temp_list[0][1:len(temp_list[0])])

        if product_title2 in products_ebay.keys() and price2 < products_ebay[product_title2]:
            del products_ebay[product_title2]
            products_ebay[product_title2] = price2
        else:
            products_ebay[product_title2] = price2

    except exceptions.NoSuchElementException:
        pass


# .......................Driver Code................................

def run(search_keyword):
    for page in range(1, 3):
        # scraping in ebay
        driver.get(generate_url_ebay(search_keyword.lower(), page))
        cards_ebay = collect_product_cards_from_page_ebay(driver)
        for card in cards_ebay:
            extract_card_data_ebay(card)

        # scraping in amazon
        driver.get(generate_url_amazon(search_keyword.lower(), page))
        cards_amazon = collect_product_cards_from_page_amazon(driver)
        for card in cards_amazon:
            extract_card_data_amazon(card)

    driver.quit()

    ebay_recommended_products = {}
    amazon_recommended_products = {}

    amazon_best_match_products = ''
    amazon_best_match_price = 0.0
    max_ratio_amazon = 0.0

    for k, v in amazon_products.items():
        ratio_current = fuzz.ratio(search_keyword, k)
        if ratio_current > max_ratio_amazon:
            max_ratio_amazon = ratio_current
            amazon_best_match_products = k
            amazon_best_match_price = v
        elif ratio_current == max_ratio_amazon and amazon_best_match_price > v:
            amazon_best_match_products = k
            amazon_best_match_price = v
        else:
            pass

        if ratio_current > 0.9:
            amazon_recommended_products[k] = v

    ebay_best_match_products = ''
    ebay_best_match_price = 0.0
    max_ratio_ebay = 0.0

    for k, v in products_ebay.items():
        ratio_current = fuzz.ratio(search_keyword, k)
        if ratio_current > max_ratio_ebay:
            max_ratio_ebay = ratio_current
            ebay_best_match_products = k
            ebay_best_match_price = v
        elif ratio_current == max_ratio_ebay and ebay_best_match_price > v:
            ebay_best_match_products = k
            ebay_best_match_price = v
        else:
            pass

        if ratio_current > 0.9:
            ebay_recommended_products[k] = v

    print("Total Unique Products Found in Amazon: ", len(amazon_products))
    print("Total Unique Products Found in eBay: ", len(products_ebay))

    # writing to a pandas dataframe in a sorted order (ascending)
    dataframe_ebay = pd.DataFrame(list(ebay_recommended_products.items()), columns=['Product Name', 'Price($)'])
    dataframe_amazon = pd.DataFrame(list(amazon_recommended_products.items()), columns=['Product Name', 'Price($)'])
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    # logical evaluations and user feedback
    if not len(amazon_products) == 0 and not len(products_ebay) == 0:
        print("\n\nAmazon Lowest Price Product Details: ", '\nProduct Name: ', amazon_best_match_products,
              "\nProduct Price: $", amazon_best_match_price, "\nHighest Matching Ratio: ",
              max_ratio_amazon)
        print("\n\neBay Lowest Price Product Details: ", '\nProduct Name: ', ebay_best_match_products,
              "\nProduct Price: $",
              ebay_best_match_price, "\nHighest Matching Ratio: ", max_ratio_ebay)
        print('\n\nFor better observation the recommended products are given below: ', '\n\neBay Products:\n',
              dataframe_ebay)
        print('\n\nAmazon Products:\n', dataframe_amazon)
        if amazon_best_match_price < ebay_best_match_price:
            print("\n\nLoading Recommendation... \n-> Hooray, You can buy from amazon with the lowest price $",
                  amazon_best_match_price)
        elif amazon_best_match_price > ebay_best_match_price:
            print("\n\nLoading Recommendation... \n-> Hooray, You can buy from ebay with the price $",
                  ebay_best_match_price)
        else:
            print("\n\nLoading Recommendation... \n-> No worries, You can buy from ebay or amazon with the price $",
                  ebay_best_match_price)

    elif not len(amazon_products) == 0:
        print("Amazon Lowest Price Product Details: ", '\nProduct Name: ', amazon_best_match_products,
              "\nProduct Price: ",
              amazon_best_match_price, "\nHighest Matching Ratio: ", max_ratio_amazon)
        print('\n\nAmazon Products:\n', dataframe_amazon)
    elif not len(products_ebay) == 0:
        print("eBay Lowest Price Product Details: ", '\nProduct Name: ', ebay_best_match_products, "\nProduct Price: ",
              ebay_best_match_price, "\nHighest Matching Ratio: ", max_ratio_ebay)
        print('\n\nAmazon Products:\n', dataframe_ebay)
    else:
        print("Oops! No related products are found in Amazon and eBay.")


if __name__ == '__main__':
    search_keyword = input("Please insert product name and model or search keywords: ")
    print('\n\nGenerating Report, please wait...\n\n')
    run(search_keyword)

# Wantdo Men's Mountain Waterproof Ski Jacket
# Nike Barcelona 2020-2021 Home Football Soccer T-Shirt Jersey
