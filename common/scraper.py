import undetected_chromedriver as uc

def get_driver(headless=False):
    # Configure ChromeOptions
    uc_options = uc.ChromeOptions()

    if headless:
        uc_options.add_argument('--headless')


    '''using undetected_chromedriver set executable_path to chromedriver path'''
    print('Using undetected_chromedriver...')

    return uc.Chrome(use_subprocess=True)