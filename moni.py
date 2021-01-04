from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By



# add user agent
opts = Options()
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4215.0 Safari/537.36 Edg/86.0.597.0")


# Chrome bootup
driver = webdriver.Chrome('../chromedriver', chrome_options=opts)


# open url
driver.get("http://testh5.alltobid.com/login?type=individual")

# click login confirm btn
driver.find_element_by_class_name("wdconfirmbtn").click()

# click agree confirm btn
driver.find_element_by_class_name("wdagreebtn").click()

# type bid account
driver.find_element_by_id("wtbusername").send_keys('12345678')

# type bid pwd
driver.find_element_by_id("wtbpassword").send_keys('1234')

# click start bid btn
driver.find_element_by_class_name("wsubmit").click()


# phase1


# type phase1 price
driver.find_element_by_class_name("whfinput01").clear()
driver.find_element_by_class_name("whfinput01").send_keys('100')

# type phase1 price confirm
driver.find_element_by_class_name("whfinput02").clear()
driver.find_element_by_class_name("whfinput02").send_keys('100')

# submit phase1 price 
driver.find_element_by_class_name("whfbtn").click()

# wait for CAPTCHA input



# submit
driver.find_element_by_class_name("whpdConfirm").click()

# check result and confirm

try:
    element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "walertcontent"))
    )
    text = element.find_element_by_tag_name('span')
    print(text.text)
    driver.find_element_by_class_name("walertagreebtn").click()
    
except Exception as e:
    print(e)



# phase2

# increase 700
driver.find_element_by_class_name("whcusraiseinput").clear()
driver.find_element_by_class_name("whcusraiseinput").send_keys('700')
driver.find_element_by_class_name("whcusraisebtn").click()
driver.find_element_by_class_name("whsetpricebtn").click()

# wait for CAPTCHA input

# submit
driver.find_element_by_class_name("whpdConfirm").click()

# check result and confirm
driver.find_element_by_class_name("walertagreebtn").click()

