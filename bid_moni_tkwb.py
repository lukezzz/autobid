import logging
import queue
import threading
import signal

import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import ttk, VERTICAL, HORIZONTAL, N, S, E, W

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

logger = logging.getLogger(__name__)


class Chrome(threading.Thread):
    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()

    def run(self):
        logger.debug('Chrome started')
        # add user agent
        opts = Options()
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4215.0 Safari/537.36 Edg/86.0.597.0")
        opts.add_experimental_option("excludeSwitches", ['enable-automation'])
        global driver
        driver = webdriver.Chrome(options=opts)
        driver.get("http://testh5.alltobid.com/login?type=individual")
        for entry in driver.get_log('browser'):
            print(entry)

    def stop(self):
        driver.quit()
        self._stop_event.set()

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

class FormUi:
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

        self.btn_login = tk.Button(self.frame, text="登录", command=self.login)
        self.btn_login.grid(row=2, column=1)

    def login(self):
        # click login confirm btn
        try:
            driver.find_element(By.CLASS_NAME, "wdconfirmbtn").click()
            try:
                # click agree confirm btn
                driver.find_element(By.CLASS_NAME,"wdagreebtn").click()
            except NoSuchElementException:
                print("el not found")
        except NoSuchElementException:
            print("el not found")
            pass
        
        try:
            # type bid account
            wtbusername = driver.find_element(By.ID, "wtbusername")

            # type bid pwd
            wtbpassword = driver.find_element(By.ID, "wtbpassword")

            actions = ActionChains(driver)
            actions.send_keys_to_element(wtbusername, self.ent_username.get())
            actions.send_keys_to_element(wtbpassword, self.ent_password.get())
            actions.perform()
            logger.log(logging.INFO, "等待验证码")
        except Exception as e:
            logger.log(logging.ERROR, "登录错误")


class App:

    def __init__(self, root):
        self.root = root

        root.title('拍牌模拟')
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        # Create the panes and frames

        vertical_pane = ttk.PanedWindow(self.root, orient=VERTICAL)
        vertical_pane.grid(row=0, column=0, sticky="nsew")
        horizontal_pane = ttk.PanedWindow(vertical_pane, orient=HORIZONTAL)
        vertical_pane.add(horizontal_pane)
        form_frame = ttk.Labelframe(horizontal_pane, text="登录")
        form_frame.columnconfigure(1, weight=1)
        horizontal_pane.add(form_frame, weight=1)
        console_frame = ttk.Labelframe(horizontal_pane, text="Console")
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(0, weight=1)
        horizontal_pane.add(console_frame, weight=1)
        # third_frame = ttk.Labelframe(vertical_pane, text="Third Frame")
        # vertical_pane.add(third_frame, weight=1)

        # Initialize all frames
        self.form = FormUi(form_frame)
        

        self.chrome = Chrome()
        self.chrome.start()
        self.root.protocol('WM_DELETE_WINDOW', self.quit)
        self.root.bind('<Control-q>', self.quit)
        signal.signal(signal.SIGINT, self.quit)
        
        self.console = ConsoleUi(console_frame)

    def quit(self, *args):
        driver.quit()
        self.root.destroy()


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)
    

    root = tk.Tk()
    # root.columnconfigure(0, weight=1, minsize=10)
    # root.rowconfigure(0, weight=1, minsize=20)
    
    # get screen width and height
    app = App(root)
    w = root.winfo_width()
    h = root.winfo_height()
    ws = root.winfo_screenwidth()
    hs = root.winfo_screenheight()
    x = (ws/2) - (w/2)
    y = (hs/2) - (h/2)
    root.geometry("{}x{}+{}+{}".format(320,600, int(x), 100))
    app.root.mainloop()