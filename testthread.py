import tkinter as tk
import time
from tkinter import Label, Button
from random import randint
import threading

root = tk.Tk()
root.title('test')
root.geometry("500x400")

def five_seconds():
    time.sleep(5)
    my_label.config(text='5 seconds is up')

def rando():
    random_label.config(text="random number: {}".format(randint(1, 100)))

my_label = Label(root, text="hello there")
my_label.pack(pady=20)

my_button1 = Button(root, text='5 seconds', command=threading.Thread(target=five_seconds).start())
my_button1.pack(pady=20)

my_button2 = Button(root, text='pick random', command=rando)
my_button2.pack(pady=20)

random_label = Label(root, text="")
random_label.pack(pady=20)

root.mainloop()