import logging
import queue
import threading
import signal
import json
import time
from random import randint

import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import ttk, VERTICAL, HORIZONTAL, N, S, E, W

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

logger = logging.getLogger(__name__)



    

class QueueHandler(logging.Handler):
    """Class to send logging records to a queue
    It can be used from different threads
    The ConsoleUi class polls this queue to display records in a ScrolledText widget
    """
    # Example from Moshe Kaplan: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06
    # (https://stackoverflow.com/questions/13318742/python-logging-to-tkinter-text-widget) is not thread safe!
    # See https://stackoverflow.com/questions/43909849/tkinter-python-crashes-on-new-thread-trying-to-log-on-main-thread

    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)


class Chrome(threading.Thread):
    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()

    def run(self):
        logger.debug('启动浏览器')
        opts = Options()
        # add user agent
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4215.0 Safari/537.36 Edg/86.0.597.0")
        # remove automation popup
        opts.add_experimental_option("excludeSwitches", ['enable-automation'])
        # disable pwd mgmt
        opts.add_experimental_option(
            'prefs', 
            {
                'credentials_enable_service': False,
                'profile': {
                    'password_manager_enabled': False
                }
            })
        # set ws log
        capabilities = DesiredCapabilities.CHROME
        capabilities['goog:loggingPrefs'] = {"performance": "ALL"}
        global driver
        driver = webdriver.Chrome(options=opts, desired_capabilities=capabilities)
        driver.get("http://testh5.alltobid.com/login?type=individual")

        for entry in driver.get_log('browser'):
            logger.debug(entry)

    def stop(self):
        driver.quit()
        self._stop_event.set()


class ConsoleUi():
    """Poll messages from a logging queue and display them in a scrolled text widget"""

    def __init__(self, frame):
        self.frame = frame
        # Create a ScrolledText wdiget
        self.scrolled_text = ScrolledText(frame, state='disabled', height=12)
        self.scrolled_text.grid(row=0, column=0, sticky=(N, S, W, E))
        self.scrolled_text.configure(font='TkFixedFont')
        self.scrolled_text.tag_config('INFO', foreground='black')
        self.scrolled_text.tag_config('DEBUG', foreground='gray')
        self.scrolled_text.tag_config('WARNING', foreground='orange')
        self.scrolled_text.tag_config('ERROR', foreground='red')
        self.scrolled_text.tag_config('CRITICAL', foreground='red', underline=1)
        # Create a logging handler using a queue
        self.log_queue = queue.Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s: %(message)s')
        self.queue_handler.setFormatter(formatter)
        logger.addHandler(self.queue_handler)
        # Start polling messages from the queue
        self.frame.after(100, self.poll_log_queue)

    def display(self, record):
        msg = self.queue_handler.format(record)
        self.scrolled_text.configure(state='normal')
        self.scrolled_text.insert(tk.END, msg + '\n', record.levelname)
        self.scrolled_text.configure(state='disabled')
        # Autoscroll to the bottom
        self.scrolled_text.yview(tk.END)

    def poll_log_queue(self):
        # Check every 100ms if there is a new message in the queue to display
        while True:
            try:
                record = self.log_queue.get(block=False)
            except queue.Empty:
                break
            else:
                self.display(record)
        self.frame.after(100, self.poll_log_queue)



class LoginFormUI:
    def __init__(self, frame):
        self.frame = frame

        lbl_username = tk.Label(self.frame, text="用户名:")
        lbl_username.grid(row=0, column=0, padx=10, pady=10)
        lbl_pwd = tk.Label(self.frame, text="密码:")
        lbl_pwd.grid(row=1, column=0)

        self.txt_username = tk.StringVar()
        self.txt_username.set('12345678')
        self.ent_username = tk.Entry(self.frame, textvariable=self.txt_username)
        self.ent_username.grid(row=0, column=1)

        self.txt_password = tk.StringVar()
        self.txt_password.set('12345')
        self.ent_password = tk.Entry(self.frame, textvariable=self.txt_password)
        self.ent_password.grid(row=1, column=1)

        self.btn_init_login = tk.Button(self.frame, text="设置登录信息", command=self.init_login, state=tk.NORMAL)
        self.btn_init_login.grid(row=2, column=0, padx=10, pady=10)

        self.btn_start_bid = tk.Button(self.frame, text="开始竞标", command=lambda: threading.Thread(target=self.wait_user_click_captcha).start(), state=tk.NORMAL)
        self.btn_start_bid.grid(row=2, column=1, pady=10)
        
        self.btn_sync_bid = tk.Button(self.frame, text="同步", command=lambda: threading.Thread(target=self.get_bidinfo, daemon=True).start(), state=tk.DISABLED)
        self.btn_sync_bid.grid(row=2, column=2, pady=10)

        self.lbl_p1_end_dt = tk.Label(self.frame, text="首次出价时段结束时间:")
        self.lbl_p1_end_dt.grid(row=3, column=0, padx=10, pady=10)
        self.lbl_p1_end_dt_content = tk.Label(self.frame, text="00:00")
        self.lbl_p1_end_dt_content.grid(row=3, column=1, padx=10, pady=10)

        self.lbl_p2_end_dt = tk.Label(self.frame, text="修改出价时段结束时间:")
        self.lbl_p2_end_dt.grid(row=4, column=0, padx=10, pady=10)
        self.lbl_p2_end_dt_content = tk.Label(self.frame, text="00:00")
        self.lbl_p2_end_dt_content.grid(row=4, column=1, padx=10, pady=10)

        self.lbl_cur_price = tk.Label(self.frame, text="最低成交价格:")
        self.lbl_cur_price.grid(row=5, column=0, padx=10, pady=10)
        self.lbl_cur_price_conent = tk.Label(self.frame, text="0")
        self.lbl_cur_price_conent.grid(row=5, column=1, padx=10, pady=10)


    

    def init_login(self):
        # start init login stage

        # find the browser testing result
        try:
            
            wTestResult = driver.find_element(By.XPATH, '//*[@id="root"]/div[2]/div[2]/div/div/div[1]/span')
            if wTestResult.text == '浏览器测试通过':
                logger.log(logging.INFO, wTestResult.text)
                self.btn_init_login['state'] = tk.DISABLED
            else:
                logger.log(logging.ERROR, '浏览器测试未通过')
                return
        except NoSuchElementException:
                logger.log(logging.ERROR, "没有找到同意按钮")
                self.btn_init_login['state'] = tk.NORMAL

        # find and click confirm/agree button
        try:
            driver.find_element(By.CLASS_NAME, "wdconfirmbtn").click()
            logger.log(logging.INFO, "点击确认")
            try:
                # click agree confirm btn
                driver.find_element(By.CLASS_NAME,"wdagreebtn").click()
                logger.log(logging.INFO, "点击同意")
            except NoSuchElementException:
                logger.log(logging.ERROR, "没有找到同意按钮")
                self.btn_init_login['state'] = tk.NORMAL
        except NoSuchElementException:
            logger.log(logging.ERROR, "没有找到确认按钮")
            self.btn_init_login['state'] = tk.NORMAL
        
        try:
            # type bid account
            wtbusername = driver.find_element(By.ID, "wtbusername")

            # type bid pwd
            wtbpassword = driver.find_element(By.ID, "wtbpassword")

            actions = ActionChains(driver)
            actions.send_keys_to_element(wtbusername, self.ent_username.get())
            actions.send_keys_to_element(wtbpassword, self.ent_password.get())
            actions.perform()
            logger.log(logging.INFO, "账号录入完毕")
            logger.log(logging.INFO, "等待完成验证码操作...")

            # self.chrome.wait_user_click_captcha()

        except Exception as e:
            logger.log(logging.ERROR, "登录错误")
    
    # def five_seconds(self):
    #     self.lbl_test.config(text='start')
    #     logger.log(logging.WARN, "testing")
    #     time.sleep(5)
    #     self.lbl_test.config(text='5 seconds is up')
    #     logger.log(logging.WARN, "finish")
   
    def wait_user_click_captcha(self):
        # check 3 'wicon-point'
        delay = 10
        try:
            wicon_points = WebDriverWait(driver, delay).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'wicon-point')))
            
            logger.log(logging.INFO, "处理验证码中。。。")
            while(len(wicon_points) != 3):
                wicon_points = driver.find_elements(By.CLASS_NAME, 'wicon-point')
                time.sleep(1)

            try:
                driver.find_element(By.CLASS_NAME, 'walert').click()
                logger.log(logging.INFO, "参加投标竞买失败")
            except:
                driver.find_element(By.XPATH, '/html/body/div/div/div[1]/div/div[2]/div[2]/div[4]/span').click()
                logger.log(logging.INFO, "参加投标竞买成功")
                self.btn_start_bid['state'] = tk.DISABLED
                # threading.Thread(target=self.get_bidinfo, daemon=True).start()
                self.btn_sync_bid['state'] = tk.NORMAL

        except TimeoutException:
            logger.log(logging.ERROR, "验证码超时")
    
    def get_bidinfo(self):
        self.btn_sync_bid['state'] = tk.DISABLED
        while(True):
            try:
                bid_info = driver.find_element(By.CLASS_NAME, 'whpubinfo')
                
            except:
                logger.log(logging.ERROR, "没有获取到拍牌信息")


            if bid_info:
                proinfo = bid_info.find_element(By.CLASS_NAME, 'proinfo')
                detail_proinfo = bid_info.find_element(By.CLASS_NAME, 'detail-proinfo')

                # check stage
                cur_stage = detail_proinfo.find_elements(By.TAG_NAME, 'span')[1]
                print(cur_stage.text)

                p1_end = proinfo.find_elements(By.TAG_NAME, 'span')[10]
                self.lbl_p1_end_dt_content.config(text=p1_end.text)

                p2_end = proinfo.find_elements(By.TAG_NAME, 'span')[13]
                self.lbl_p2_end_dt_content.config(text=p2_end.text)

                

                if cur_stage.text == '首次出价时段':
                    cur_price = detail_proinfo.find_elements(By.TAG_NAME, 'span')[7]
                    self.lbl_cur_price_conent.config(text=cur_price.text)
                else:
                    cur_price = detail_proinfo.find_elements(By.TAG_NAME, 'span')[5]
                    self.lbl_cur_price_conent.config(text=cur_price.text)
                    pass
            time.sleep(0.5)
    
    
            
class App:

    def __init__(self, root):
        self.root = root
        root.lift()


        root.title('拍牌模拟')
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        # Create the panes and frames

        

        vertical_pane = ttk.PanedWindow(self.root, orient=VERTICAL)
        vertical_pane.grid(row=0, column=0, sticky="nsew")
        horizontal_pane = ttk.PanedWindow(vertical_pane, orient=HORIZONTAL)
        vertical_pane.add(horizontal_pane)

        login_form_frame = ttk.Labelframe(horizontal_pane, text="登陆设置")
        login_form_frame.columnconfigure(1, weight=1)
        horizontal_pane.add(login_form_frame, weight=1)

        console_frame = ttk.Labelframe(horizontal_pane, text="操作日志")
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(0, weight=1)
        horizontal_pane.add(console_frame, weight=1)
        # third_frame = ttk.Labelframe(vertical_pane, text="Third Frame")
        # vertical_pane.add(third_frame, weight=1)
        


        # Initialize all frames
        self.login_form = LoginFormUI(login_form_frame)
        self.console = ConsoleUi(console_frame)

        
        self.chrome = Chrome()
        self.chrome.start()
        
        self.root.protocol('WM_DELETE_WINDOW', self.quit)
        # self.root.bind('<Command-a>', self.testcommand)
        signal.signal(signal.SIGINT, self.quit)
        

    def quit(self, *args):
        driver.close()
        self.root.destroy()


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)
    

    root = tk.Tk()
    # root.columnconfigure(0, weight=1, minsize=10)
    # root.rowconfigure(0, weight=1, minsize=20)
    
    # get screen width and height
    app = App(root)
    # w = root.winfo_width()
    # h = root.winfo_height()
    # ws = root.winfo_screenwidth()
    # hs = root.winfo_screenheight()
    # x = (ws/2) - (w/2)
    # y = (hs/2) - (h/2)
    # root.geometry("{}x{}+{}+{}".format(320,600, int(x), 100))
    root.call('wm', 'attributes', '.', '-topmost', '1')
    app.root.mainloop()