from selenium import webdriver

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import json
import pprint
import time


# add user agent
opts = Options()
opts.add_argument('ignore-certificate-errors')
# opts.add_argument('enable-devtools-experiments')
# opts.add_argument('force-devtools-available')
# opts.add_argument('debug-devtools')
# opts.add_argument('--headless')
# opts.add_argument("auto-open-devtools-for-tabs")
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4215.0 Safari/537.36 Edg/86.0.597.0")
capabilities = DesiredCapabilities.CHROME
capabilities["goog:loggingPrefs"] = {"performance": "ALL"}  # chromedriver 75+


# Chrome bootup
driver = webdriver.Chrome(chrome_options=opts, desired_capabilities=capabilities, service_log_path='./test.log')

# open url
logs = driver.get_log("performance")
# time.sleep(1)
# driver.get("https://repaimai2.alltobid.com/system-info")
driver.get("https://weibo.com/")



# time.sleep(3)

# driver.find_element_by_id("new_msg_data").clear()
# driver.find_element_by_id("new_msg_data").send_keys('123456')
# driver.find_element_by_id("new_msg_btn").click()

# driver.close()
# driver.quit()

def process_browser_logs_for_network_events(logs):
    for entry in logs:
        log = json.loads(entry["message"])["message"]
        print(log['method'])
        if (
            "Network.webSocketFrameSent" in log["method"]
            or "Network.webSocketFrameReceived" in log["method"]
            or "Network.webSocket" in log["method"]
        ):
            yield log
        # yield log

time.sleep(3)
while(True):
    events = process_browser_logs_for_network_events(logs)
    for event in events:
        print(event)
    time.sleep(2)

# with open("log_entries.txt", "wt") as out:
#     while(True):
#         events = process_browser_logs_for_network_events(logs)
#         for event in events:
#             pprint.pprint(event, stream=out)
#         time.sleep(1)