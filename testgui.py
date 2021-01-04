import tkinter as tk
from tkinter.font import names
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


# add user agent
opts = Options()
opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4215.0 Safari/537.36 Edg/86.0.597.0")



class App(tk.Frame):
    def __init__(self, master=None, **kw):
        self.driver = webdriver.Chrome(options=opts)
        tk.Frame.__init__(self, master=master, **kw)
        self.txtUrl = tk.StringVar()
        self.entryUrl = tk.Entry(self, textvariable=self.txtUrl)
        self.entryUrl.grid(row=0, column=0)
        self.btnGet = tk.Button(self, text="test url", command=self.openWd)
        self.btnGet.grid(row=0, column=1)

        self.txtUsername = tk.StringVar()
        self.entryUsername = tk.Entry(self, textvariable=self.txtUsername)
        self.entryUsername.grid(row=1, column=0)

        self.txtPassword = tk.StringVar()
        self.entryPassword = tk.Entry(self, textvariable=self.txtPassword)
        self.entryPassword.grid(row=2, column=0)

        self.btnLogin = tk.Button(self, text="login", command=self.login)
        self.btnLogin.grid(row=3, column=0)

    def openWd(self):
        self.driver.get(self.txtUrl.get())

    def login(self):
        # click login confirm btn
        self.driver.find_element_by_class_name("wdconfirmbtn").click()

        # click agree confirm btn
        self.driver.find_element_by_class_name("wdagreebtn").click()

        # type bid account
        self.driver.find_element_by_id("wtbusername").send_keys('12345678')

        # type bid pwd
        self.driver.find_element_by_id("wtbpassword").send_keys('1234')

if __name__ == '__main__':

    root = tk.Tk()
    App(root).grid()
    root.mainloop()