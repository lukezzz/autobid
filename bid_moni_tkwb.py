import tkinter as tk
from tkinter.font import names
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains


# add user agent
opts = Options()
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4215.0 Safari/537.36 Edg/86.0.597.0")
opts.add_experimental_option("excludeSwitches", ['enable-automation'])
driver = webdriver.Chrome(options=opts)
driver.get("http://testh5.alltobid.com/login?type=individual")
for entry in driver.get_log('browser'):
    print(entry)

class App(tk.Frame):
    def __init__(self, master=None, **kw):
        
        tk.Frame.__init__(self, master=master, borderwidth=1, **kw)
        # self.columnconfigure(0, weight=0, minsize=10)
        # self.columnconfigure(1, weight=1, minsize=10)
        # self.rowconfigure([0, 1], weight=0, minsize=20)
        

        lbl_username = tk.Label(self, text="用户名:")
        lbl_username.grid(row=0, column=0, padx=10, pady=10)
        lbl_pwd = tk.Label(self, text="密码:")
        lbl_pwd.grid(row=1, column=0)


        self.txt_username = tk.StringVar()
        self.txt_username.set('12345678')
        self.ent_username = tk.Entry(self, textvariable=self.txt_username)
        self.ent_username.grid(row=0, column=1)

        self.txt_password = tk.StringVar()
        self.txt_password.set('12345')
        self.ent_password = tk.Entry(self, textvariable=self.txt_password)
        self.ent_password.grid(row=1, column=1)

        self.btn_login = tk.Button(self, text="login", command=self.login)
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
        
        # type bid account
        wtbusername = driver.find_element(By.ID, "wtbusername")

        # type bid pwd
        wtbpassword = driver.find_element(By.ID, "wtbpassword")

        actions = ActionChains(driver)
        actions.send_keys_to_element(wtbusername, self.ent_username.get())
        actions.send_keys_to_element(wtbpassword, self.ent_password.get())
        actions.perform()

if __name__ == '__main__':

    root = tk.Tk()
    # root.columnconfigure(0, weight=1, minsize=10)
    # root.rowconfigure(0, weight=1, minsize=20)
    root.title('拍牌模拟')
    # get screen width and height
    App(root).grid()
    w = root.winfo_width()
    h = root.winfo_height()
    ws = root.winfo_screenwidth()
    hs = root.winfo_screenheight()
    x = (ws/2) - (w/2)
    y = (hs/2) - (h/2)
    root.geometry("{}x{}+{}+{}".format(300,800, int(x), 100))
    root.mainloop()