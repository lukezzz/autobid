import logging
import queue
import threading
import signal
import json
import time
from datetime import datetime, timedelta

import tkinter as tk
import tkinter.font as tkFont
from selenium.webdriver.common import action_chains
from tkinter.scrolledtext import ScrolledText
from tkinter import Tk, ttk, VERTICAL, HORIZONTAL, N, S, E, W

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.remote_connection import LOGGER as selenumLogger
from urllib3.connectionpool import log as urllibLogger
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger(__name__)
urllibLogger.setLevel(logging.WARNING)

STATE = {
    "login": "设置登陆信息",
    "init": "登陆成功",
    "p1": "出价第一阶段",
    "p2": "出价第二阶段",
}

cur_phrase = 'login'
lowest_price = 0
end_dt = ''

# UI setting
def center_window(win, w=None, h=None):
    # w = win.winfo_width()
    # h = win.winfo_height()
    ws = win.winfo_screenwidth()
    hs = win.winfo_screenheight()
    x = int((ws/2) - (w/2))
    y = int((hs/2) - (h/2)) - 30
    win.geometry("{}x{}+{}+{}".format(w,h,x,y))

# font setting
def _font(fname='微软雅黑', size=12, bold=tkFont.NORMAL):
    return tkFont.Font(family=fname, size=size, weight=bold)

# UI divider
def divider(parent, mode, border=2, bg='whitesmoke'):
    if mode == 'v':
        return tk.Frame(parent, width=border, bg=bg)
    else:
        return tk.Frame(parent, height=border, bg=bg)

# UI title label formater
def title_label(frame, text, size=14, bold=False):
    top_frame = tk.Frame(frame, bg='white')
    label = tk.Label(top_frame, text=text, bg='white', fg='gray48', height=2, font=_font(size=size, bold=tkFont.BOLD))
    label.pack(side=tk.LEFT, padx=5)
    top_frame.pack(fill=tk.X)
    return top_frame

def attach_to_session(executor_url, session_id):
    original_execute = WebDriver.execute
    def new_command_execute(self, command, params=None):
        if command == "newSession":
            # Mock the response
            return {'success': 0, 'value': None, 'sessionId': session_id}
        else:
            return original_execute(self, command, params)
    # Patch the function before creating the driver object
    WebDriver.execute = new_command_execute
    driver = webdriver.Remote(command_executor=executor_url, desired_capabilities={})
    driver.session_id = session_id
    # Replace the patched function with original function
    WebDriver.execute = original_execute
    return driver
    
def diff_timer(end, seconds, microseconds):
    end_dt = datetime.strptime(end, "%H:%M")
    seconds = 60 - seconds
    now = datetime.now() + timedelta(seconds=seconds, microseconds=microseconds)
    # print(now)
    # nowstr = now.strftime("%H:%M:%S.%f")
    # comp_dt = datetime.strptime(nowstr, "%H:%M:%S")
    return now.time() >= end_dt.time()

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
        selenumLogger.setLevel(logging.WARNING)
        global driver
        driver = webdriver.Chrome(options=opts, desired_capabilities=capabilities)
        driver.get("http://testh5.alltobid.com/login?type=individual")

        for entry in driver.get_log('browser'):
            logger.debug(entry)

        self.chrome2 = ChromeBackground()
        self.chrome2.start()

        

    def stop(self):
        self.chrome2.stop()
        driver.quit()
        self._stop_event.set()

class ChromeBackground(threading.Thread):
    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()

    def run(self):
        logger.debug('启动chrome2 后台监控')
        executor_url = driver.command_executor._url
        session_id = driver.session_id
        global driver2
        driver2 = attach_to_session(executor_url, session_id)
    

    def stop(self):
        driver2.quit()
        self._stop_event.set()

class ConsoleUi():
    """Poll messages from a logging queue and display them in a scrolled text widget"""

    def __init__(self, frame):
        self.frame = frame
        # Create a ScrolledText wdiget
        self.scrolled_text = ScrolledText(frame, state='disabled', height=14, width=54)
        self.scrolled_text.grid(row=0, column=0, sticky=(N, S, W))
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

class LoginUi:
    def __init__(self, frame):
        self.frame = frame

        title_label(self.frame, '设置登陆信息', 14, True).pack(side=tk.TOP, padx=10)
        divider(self.frame, 'h', border=1, bg='bisque3').pack(fill=tk.X)

        username_frame = tk.Frame(self.frame, bg='white')
        self.label(username_frame, text="用户名:").pack(side=tk.LEFT, pady=5)
        self.txt_username = tk.StringVar()
        self.txt_username.set('12345678')
        self.ent_username = tk.Entry(username_frame, textvariable=self.txt_username)
        self.ent_username.pack(side=tk.LEFT, pady=5)
        username_frame.pack(fill=tk.X)

        pwd_frame = tk.Frame(self.frame, bg='white')
        self.label(pwd_frame, text="   密码:").pack(side=tk.LEFT, pady=10)
        self.txt_password = tk.StringVar()
        self.txt_password.set('12345')
        self.ent_password = tk.Entry(pwd_frame, textvariable=self.txt_password)
        self.ent_password.pack(side=tk.LEFT, pady=5)
        self.btn_init_login = tk.Button(pwd_frame, text="开始模拟", command=self.init_login, state=tk.NORMAL)
        self.btn_init_login.pack(side=tk.LEFT, padx=10)
        pwd_frame.pack(fill=tk.X)



    def label(self, frame, text, size=10, fg='gray'):
        return tk.Label(frame, text=text, bg='white', font=_font(size))
    
    def init_login(self):
        global cur_phrase
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

            threading.Thread(target=self.wait_user_click_captcha).start()
            

        except Exception as e:
            logger.log(logging.ERROR, "登录错误")
       

    def wait_user_click_captcha(self):
        # check 3 'wicon-point'
        delay = 60
        global cur_phrase
        try:
            wicon_points = WebDriverWait(driver, delay).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'wicon-point')))
            
            logger.log(logging.INFO, "处理验证码中...")
            while(len(wicon_points) != 3):
                wicon_points = driver.find_elements(By.CLASS_NAME, 'wicon-point')
                time.sleep(1)

            try:
                driver.find_element(By.CLASS_NAME, 'walert').click()
                logger.log(logging.ERROR, "参加投标竞买失败")
                self.btn_init_login['state'] = tk.NORMAL
            except:
                driver.find_element(By.XPATH, '/html/body/div/div/div[1]/div/div[2]/div[2]/div[4]/span').click()
                logger.log(logging.INFO, "参加投标竞买成功")
                logger.log(logging.INFO, "等待开始...")
                cur_phrase = 'init'
                self.btn_init_login['state'] = tk.DISABLED
                # threading.Thread(target=self.get_bidinfo, daemon=True).start()
                # self.btn_sync_bid['state'] = tk.NORMAL

        except TimeoutException:
            logger.log(logging.ERROR, "验证码超时")
    
class StateUi:
    def __init__(self, frame):
        self.frame = frame

        # title_label(self.frame, '当前状态', 14, True).pack(side=tk.TOP, padx=10)
        global cur_phrase
        top_frame = tk.Frame(self.frame, bg='white')
        self.state_label = tk.Label(top_frame, text='当前状态: {}'.format(STATE[cur_phrase]), bg='white', fg='gray48', height=2, font=_font(size=14, bold=tkFont.BOLD))
        self.state_label.pack(side=tk.LEFT, padx=5)
        top_frame.pack(fill=tk.X)
        divider(self.frame, 'h', border=1, bg='bisque3').pack(fill=tk.X)

        # self.btn_sync_bid = tk.Button(self.frame, text="同步", command=lambda: threading.Thread(target=self.get_bidinfo, daemon=True).start())
        # self.btn_sync_bid = tk.Button(self.frame, text="同步", command=self.get_bidinfo)
        # self.btn_sync_bid.pack(fill=tk.X)
        time_frame1 = tk.Frame(self.frame, bg='white')
        self.label(time_frame1, text="首次出价时段结束时间:").pack(side=tk.LEFT, pady=5)
        self.lbl_p1_end_dt_content = tk.Label(
            time_frame1, 
            text='00:00',
            font=_font(size=16, bold=tkFont.BOLD)
            )
        self.lbl_p1_end_dt_content.pack(side=tk.LEFT, pady=5)
        time_frame1.pack(fill=tk.X)

        time_frame2 = tk.Frame(self.frame, bg='white')
        self.label(time_frame2, text="修改出价时段结束时间:").pack(side=tk.LEFT, pady=5)
        self.lbl_p2_end_dt_content = tk.Label(
            time_frame2, 
            text="00:00",
            font=_font(size=16, bold=tkFont.BOLD)
            )
        self.lbl_p2_end_dt_content.pack(side=tk.LEFT, pady=5)
        time_frame2.pack(fill=tk.X)

        cur_bider_frame = tk.Frame(self.frame, bg='white')
        self.label(cur_bider_frame, text="当前投标人数:").pack(side=tk.LEFT, pady=5)
        self.lbl_cur_bider_content = tk.Label(
            cur_bider_frame, 
            text="0",
            font=_font(size=16, bold=tkFont.BOLD)
            )
        self.lbl_cur_bider_content.pack(side=tk.LEFT, pady=5)
        cur_bider_frame.pack(fill=tk.X)

        cur_price_frame = tk.Frame(self.frame, bg='white')
        self.label(cur_price_frame, text="最低成交价格:").pack(side=tk.LEFT, pady=5)
        self.lbl_cur_price_content = tk.Label(
            cur_price_frame, 
            text="0", 
            font=_font(size=16, bold=tkFont.BOLD),
            fg='red')
        self.lbl_cur_price_content.pack(side=tk.LEFT, pady=5)
        cur_price_frame.pack(fill=tk.X)

        threading.Thread(target=self.get_bidinfo, daemon=True).start()


    def label(self, frame, text, size=12, fg='gray'):
        return tk.Label(frame, text=text, bg='white', fg=fg, font=_font(size=size))


    def get_bidinfo(self):
        global cur_phrase
        global lowest_price
        global end_dt
        while(True):
            self.state_label['text'] = "当前状态: {}".format(STATE[cur_phrase])
            if cur_phrase != 'login':
                try:
                    bid_info = driver2.find_element(By.CLASS_NAME, 'whpubinfo')
                except StaleElementReferenceException as e:
                    print(e)
                    time.sleep(2)
                    continue
                except Exception as e:
                    logger.log(logging.ERROR, "没有获取到拍牌信息或还未开始")
                    print(e)
                    time.sleep(5)
                    continue

                if bid_info:
                    try:
                        proinfo = bid_info.find_element(By.CLASS_NAME, 'proinfo')
                        detail_proinfo = bid_info.find_element(By.CLASS_NAME, 'detail-proinfo')

                        # check stage
                        cur_stage = detail_proinfo.find_elements(By.TAG_NAME, 'span')[1]

                        p1_end = proinfo.find_elements(By.TAG_NAME, 'span')[10]
                        self.lbl_p1_end_dt_content['text'] = p1_end.text

                        p2_end = proinfo.find_elements(By.TAG_NAME, 'span')[13]
                        self.lbl_p2_end_dt_content['text'] = p2_end.text
                        end_dt = p2_end.text

                        if cur_stage.text == '首次出价时段':
                            cur_phrase = 'p1'
                            cur_price = detail_proinfo.find_elements(By.TAG_NAME, 'span')[7]
                            self.lbl_cur_price_content['text'] = cur_price.text
                            lowest_price = cur_price.text

                            cur_bider = detail_proinfo.find_elements(By.TAG_NAME, 'span')[5]
                            self.lbl_cur_bider_content['text'] = cur_bider.text
                            
                            # self.start_price = detail_proinfo.find_elements(By.TAG_NAME, 'span')[7].text
                            # self.btn_p1_submit['state'] = tk.NORMAL
                            
                        else:
                            cur_phrase = 'p2'
                            cur_price = detail_proinfo.find_elements(By.TAG_NAME, 'span')[5]
                            self.lbl_cur_price_content['text'] = cur_price.text
                            lowest_price = cur_price.text

                            # self.btn_p1_submit['state'] = tk.DISABLED
                            # self.btn_p2_plus['state'] = tk.NORMAL
                            # self.btn_p2_policy1['state'] = tk.NORMAL
                            # self.btn_p2_policy2['state'] = tk.NORMAL

                        

                    except StaleElementReferenceException as e:
                        print(e)
                        time.sleep(2)
                        continue

                    except Exception as e:
                        print(e)
                        time.sleep(2)
                        continue

                time.sleep(0.3)
            else:
                time.sleep(3)

class PolicyUi:
    def __init__(self, frame):
        self.frame = frame

        self.policy_thread_status = False
        
        title_label(self.frame, '出价策略', 14, True).pack(side=tk.TOP, padx=10)
        p1_frame1 = tk.Frame(self.frame, bg='white')
        self.btn_p1_submit = tk.Button(p1_frame1, text="第一阶段出价", command=lambda: threading.Thread(target=self.p1_submit, daemon=True).start(), state=tk.NORMAL)
        self.btn_p1_submit.pack(side=tk.LEFT, padx=10, pady=5)
        p1_frame1.pack(fill=tk.X)

        p2_manul_policy_frame = tk.Frame(self.frame, bg='white')
        self.label(p2_manul_policy_frame, text="输入整数价格: +").pack(side=tk.LEFT, pady=5)
        self.add_price = tk.StringVar()
        self.add_price.set('500')
        self.ent_add_price = tk.Entry(p2_manul_policy_frame, textvariable=self.add_price, width=5)
        self.ent_add_price.pack(side=tk.LEFT)
        self.btn_p2_plus = tk.Button(p2_manul_policy_frame, text="手动提交", command=self.manual_plus, state=tk.NORMAL)
        self.btn_p2_plus.pack(side=tk.LEFT, padx=10)
        p2_manul_policy_frame.pack(fill=tk.X)

        p2_policy1_frame = tk.Frame(self.frame, bg='white')
        self.label(p2_policy1_frame, text="策略1: 52s + 400, 56.8s提交").pack(side=tk.LEFT, pady=5)
        self.btn_p2_policy1 = tk.Button(p2_policy1_frame, text="策略1", command=lambda: self.set_policy(52, 400, "56.8"), state=tk.NORMAL)
        self.btn_p2_policy1.pack(side=tk.LEFT, pady=5)
        p2_policy1_frame.pack(fill=tk.X)


        p2_policy2_frame = tk.Frame(self.frame, bg='white')
        self.label(p2_policy2_frame, text="策略2: 49s + 500, 57.3s提交").pack(side=tk.LEFT, pady=5)
        self.btn_p2_policy2 = tk.Button(p2_policy2_frame, text="策略2", command=lambda: self.set_policy(49, 500, "57.3"), state=tk.NORMAL)
        self.btn_p2_policy2.pack(side=tk.LEFT, pady=5)
        p2_policy2_frame.pack(fill=tk.X)


        p2_cancel_frame = tk.Frame(self.frame, bg='white')
        self.btn_cancel_policy = tk.Button(p2_cancel_frame, text="取消", command=lambda: self.cancecl_policy(), state=tk.NORMAL)
        self.btn_cancel_policy.pack(side=tk.LEFT, pady=5)
        p2_cancel_frame.pack(fill=tk.X)


    def label(self, frame, text, size=10, fg='gray'):
        return tk.Label(frame, text=text, bg='white', font=_font(size))

    def p1_submit(self):
        global lowest_price 
        logger.log(logging.INFO, "当前价格：{}".format(lowest_price))
        try:
            whfinput01 = driver.find_element(By.XPATH, '/html/body/div/div/div[2]/div/div[3]/div[2]/div[2]/div/div[1]/div[2]/div/input')
            # #root > div > div.whomemain > div > div.whbiddingcontent > div.whbiddingitem.whbiddingright > div.whbidcontent > div > div:nth-child(1) > div.whinputbox > div > input
            # /html/body/div/div/div[2]/div/div[3]/div[2]/div[2]/div/div[1]/div[2]/div/input
            whfinput02 = driver.find_element(By.XPATH, '/html/body/div/div/div[2]/div/div[3]/div[2]/div[2]/div/div[2]/div[2]/div[1]/input')
            # /html/body/div/div/div[2]/div/div[3]/div[2]/div[2]/div/div[2]/div[2]/div[1]/input
            whfbtn = driver.find_element(By.CLASS_NAME, 'whfbtn')
            actions = ActionChains(driver)
            actions.send_keys_to_element(whfinput01, Keys.COMMAND+"a")
            actions.send_keys_to_element(whfinput01, Keys.BACK_SPACE)
            actions.send_keys_to_element(whfinput01, lowest_price)
            actions.send_keys_to_element(whfinput02, Keys.COMMAND+"a")
            actions.send_keys_to_element(whfinput02, Keys.BACK_SPACE)
            actions.send_keys_to_element(whfinput02, lowest_price)
            actions.click(whfbtn)
            actions.perform()

            # #bidprice
            self.p1_alertbox()
            

        except NoSuchElementException as e:
            print(e)
            logger.log(logging.ERROR, "未获取到出价信息")


    def p1_alertbox(self):
        time.sleep(0.5)
        try:
            driver.find_element(By.CLASS_NAME, 'whSetPriceD')
            logger.log(logging.INFO, "等待验证码")
            threading.Thread(target=self.pricecaptcha).start()
            
        except NoSuchElementException as e:
            print(e)
            # logger.log(logging.ERROR, "w")
    
    def manual_plus(self):
        try:
            price = int(self.ent_add_price.get())
            if price % 100 != 0:
                logger.log(logging.ERROR, "输入价格错误，请重新输入")
                return
            
            threading.Thread(target=self.p2_plus, args=(price,), daemon=True).start()
        except Exception as e:
            logger.log(logging.ERROR, "输入价格错误，请重新输入")


    def p2_plus(self, price):
        logger.log(logging.INFO, "+ {}".format(price))
        global lowest_price
        logger.log(logging.INFO, "当前价格：{}".format(lowest_price))
        
        try:
            whsetpricetip = driver.find_element(By.XPATH, '/html/body/div/div/div[2]/div/div[3]/div[2]/div[2]/div/div[2]/div[3]/div[2]/div/input')
            whsetpricebtn = driver.find_element(By.CLASS_NAME, 'whsetpricebtn')
            submit_price = int(lowest_price) + int(price)
            actions = ActionChains(driver)
            actions.send_keys_to_element(whsetpricetip, Keys.COMMAND+"a")
            actions.send_keys_to_element(whsetpricetip, Keys.BACK_SPACE)
            actions.send_keys_to_element(whsetpricetip, submit_price)
            actions.click(whsetpricebtn)
            actions.perform()

            self.pricecaptcha()

        except Exception as e:
            print(e)

    def cancecl_policy(self):
        self.policy_thread_status = False

    def set_policy(self, inc_time, inc_price, advance_time):

        adv_t = datetime.strptime(advance_time, '%S.%f')

        delay_microsec = adv_t.microsecond / 1000

        if self.policy_thread_status == False:
            self.policy_thread_status = True
            logger.log(logging.WARN, "出价时间: {} 加价：{} 提交秒数：{} 延时：{}ms".format(inc_time, inc_price, adv_t.second, delay_microsec))
            threading.Thread(target=self.p2_autopolicy, args=(inc_time, inc_price, adv_t.second, delay_microsec,), daemon=True).start()
        else:
            logger.log(logging.ERROR, "正在执行策略，请先取消")


    def p2_autopolicy(self, inc_time, inc_price, advance_sec, delay_microsec):

        global lowest_price
        global end_dt
        # check dt
        # end_dt = self.state.lbl_p2_end_dt_content.cget("text")
        while(self.policy_thread_status):
            if diff_timer(end_dt, inc_time, 0):
                whsetpricetip = driver.find_element(By.XPATH, '/html/body/div/div/div[2]/div/div[3]/div[2]/div[2]/div/div[2]/div[3]/div[2]/div/input')
                whsetpricebtn = driver.find_element(By.CLASS_NAME, 'whsetpricebtn')
                submit_price = int(lowest_price) + inc_price
                actions = ActionChains(driver)
                actions.send_keys_to_element(whsetpricetip, Keys.COMMAND+"a")
                actions.send_keys_to_element(whsetpricetip, Keys.BACK_SPACE)
                actions.send_keys_to_element(whsetpricetip, submit_price)
                actions.click(whsetpricebtn)
                actions.perform()
                logger.log(logging.DEBUG, "出价时间: {}".format(datetime.now()))
                break

            time.sleep(0.2)

        while(self.policy_thread_status):
            if diff_timer(end_dt, advance_sec, delay_microsec):
                if self.pricecaptcha():
                    break
            time.sleep(0.2)    

    def p2_policy1(self):
        # simple capatcha: 49s + 700, submit at 56s
        logger.log(logging.INFO, "执行策略1: 52s + 400, 56.8s提交")
        global lowest_price
        global end_dt
        # check dt
        # end_dt = self.state.lbl_p2_end_dt_content.cget("text")
        while(True):
            if diff_timer(end_dt, 52, 0):
                whsetpricetip = driver.find_element(By.XPATH, '/html/body/div/div/div[2]/div/div[3]/div[2]/div[2]/div/div[2]/div[3]/div[2]/div/input')
                whsetpricebtn = driver.find_element(By.CLASS_NAME, 'whsetpricebtn')
                submit_price = int(lowest_price) + 400
                actions = ActionChains(driver)
                actions.send_keys_to_element(whsetpricetip, Keys.COMMAND+"a")
                actions.send_keys_to_element(whsetpricetip, Keys.BACK_SPACE)
                actions.send_keys_to_element(whsetpricetip, submit_price)
                actions.click(whsetpricebtn)
                actions.perform()
                logger.log(logging.DEBUG, "出价时间: {}".format(datetime.now()))
                break

            time.sleep(0.2)

        while(True):
            if diff_timer(end_dt, 56, 800):
                if self.pricecaptcha():
                    break
            time.sleep(0.2)    


    def p2_policy2(self):
        # difficute capatcha: 49s + 600, submit at 57s
        logger.log(logging.INFO, "执行策略2: 49s + 400, 57.3s提交")
        global lowest_price
        global end_dt
        # end_dt = self.state.lbl_p2_end_dt_content.cget("text")
        while(True):
            if diff_timer(end_dt, 49, 0):
                whsetpricetip = driver.find_element(By.XPATH, '/html/body/div/div/div[2]/div/div[3]/div[2]/div[2]/div/div[2]/div[3]/div[2]/div/input')
                whsetpricebtn = driver.find_element(By.CLASS_NAME, 'whsetpricebtn')
                submit_price = int(lowest_price) + 400
                actions = ActionChains(driver)
                actions.send_keys_to_element(whsetpricetip, Keys.COMMAND+"a")
                actions.send_keys_to_element(whsetpricetip, Keys.BACK_SPACE)
                actions.send_keys_to_element(whsetpricetip, submit_price)
                actions.click(whsetpricebtn)
                actions.perform()
                logger.log(logging.DEBUG, "出价时间: {}".format(datetime.now()))
                break
            time.sleep(0.2)

        while(True):
            if diff_timer(end_dt, 57, 300):
                if self.pricecaptcha():
                    break
            time.sleep(0.2)    

        
    def pricecaptcha(self):
        whSetPriceD = driver.find_element(By.CLASS_NAME, 'whSetPriceD')
        whpdTitleBox = whSetPriceD.find_element(By.CLASS_NAME, 'whpdTitleBox')
        submit_price = whpdTitleBox.find_elements(By.TAG_NAME, 'span')[0]
        logger.log(logging.ERROR, "{}".format(submit_price.text))
        logger.log(logging.INFO, "等待完成验证码...")
        try:
            pricecaptcha = whSetPriceD.find_element(By.CLASS_NAME, 'pricecaptcha')
            img = pricecaptcha.get_attribute('src')
            captcha_id = img.split('/')[4].split('.')[0]
            print(captcha_id)
            captcha_dict = {
                'demo001': "4227",
                'demo002': "0872",
                'demo003': "9538",
                'demo004': "8729",
                'demo005': "5765",
                'demo006': "2238",
                'demo007': "2176",
                'demo008': "6161",
                'demo009': "8255",
                'demo010': "2987",
            }
            captcha = captcha_dict[captcha_id]
            bidprice = whSetPriceD.find_element(By.ID, 'bidprice')
            whpdConfirm = whSetPriceD.find_element(By.CLASS_NAME, 'whpdConfirm')
            actions = ActionChains(driver)
            actions.send_keys_to_element(bidprice, captcha)
            actions.click(whpdConfirm)
            actions.perform()
            logger.log(logging.DEBUG, "验证码: {} 出价时间: {}".format(captcha, datetime.now()))

            # submit success
            try:
                walert = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'walert')))
                walertcontent = walert.find_element(By.CLASS_NAME, 'walertcontent')
                submit_result = walertcontent.find_elements(By.TAG_NAME, 'span')
                logger.log(logging.INFO, "{}".format(submit_result[0].text))
                # logger.log(logging.INFO, "{}".format(submit_result[1].text))
                # logger.log(logging.INFO, "{}".format(submit_result[2].text))
                walert.find_element(By.CLASS_NAME, 'walertagreebtn').click()
                

            except TimeoutException as e:
                print(e)

                # submit failed
                try:
                    wralert = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'wralert')))
                    wralertcontent = wralert.find_element(By.CLASS_NAME, 'wralertcontent')
                    submit_info = wralertcontent.find_elements(By.TAG_NAME, 'span')
                    logger.log(logging.INFO, "{}".format(submit_info[0].text))
                    logger.log(logging.INFO, "{}".format(submit_info[1].text))
                    logger.log(logging.INFO, "{}".format(submit_info[2].text))
                    wralert.find_element(By.CLASS_NAME, 'wralertagreebtn').click()

                except TimeoutException as e:
                    print(e)
                    pass
                

                
        except NoSuchElementException as e:
            print(e)
            logger.log(logging.ERROR, "出价失败")

        return True
            

       
class App:

    def __init__(self, root):
        self.root = root
        # self.root.geometry("{}x{}".format(300, 800))
        center_window(self.root, 400, 750)

        self.root.title('拍牌模拟')

        self.root.grab_set()

        self.body()

        self.login_ui
        self.console_ui
        self.state_ui
        self.policy_ui
       
        

        
        self.chrome = Chrome()
        self.chrome.start()
        
        
        self.root.protocol('WM_DELETE_WINDOW', self.quit)
        # self.root.bind('<Command-a>', self.testcommand)
        signal.signal(signal.SIGINT, self.quit)
        

    def quit(self, *args):
        driver.close()
        self.root.destroy()

    def body(self):
        self.title(self.root).pack(fill=tk.X)
        divider(self.root, 'h', border=3).pack(fill=tk.X)
        self.main(self.root).pack(expand=tk.YES, fill=tk.BOTH)
        divider(self.root, 'h', border=2, bg='bisque3').pack(fill=tk.X)
        self.bottom(self.root).pack(fill=tk.X)

    def title(self, parent):

        def label(frame, text, size, bold=False):
            return tk.Label(frame, text=text, bg='white', fg='black', height=2, font=_font(size=size, bold=tkFont.BOLD))

        frame = tk.Frame(parent, bg='white')
        label(frame, '拍牌模拟测试v0.1', 16, True).pack(side=tk.LEFT, padx=10)

        return frame

    def main(self, parent):
        frame = tk.Frame(parent, bg='white')
        self.main_login(frame).pack(fill=tk.X, padx=10, pady=2)
        self.main_bid_status(frame).pack(fill=tk.X, padx=10, pady=2)
        self.main_policy(frame).pack(fill=tk.X, padx=10, pady=2)
        return frame

    def bottom(self, parent):
        
        frame = tk.Frame(parent, height=10, width=20, bg='whitesmoke')
        self.console_ui = ConsoleUi(frame)

        return frame

    def main_login(self, parent):
        frame = tk.Frame(parent, height=5, bg='white')
        self.login_ui = LoginUi(frame)

        return frame

    
    def main_bid_status(self, parent):

        frame = tk.Frame(parent, bg='white', height=40)
        self.state_ui = StateUi(frame)
        return frame

    def main_policy(self, parent):

        frame = tk.Frame(parent, bg='white', height=30)
        self.policy_ui = PolicyUi(frame)
        return frame

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)
    
    

    root = tk.Tk()
    
    # root.columnconfigure(0, weight=1, minsize=10)
    # root.rowconfigure(0, weight=1, minsize=20)
    
    # get screen width and height
    app = App(root)
    
    
    root.call('wm', 'attributes', '.', '-topmost', '1')
    app.root.mainloop()