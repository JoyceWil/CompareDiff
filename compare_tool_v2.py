import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk

# --- Sliding boundary overlay added on image ---
class ImageCompareTool:
    def __init__(self, master):
        self.master = master
        master.title("Image Compare Tool")

        self.canvas = tk.Canvas(master, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.img1 = None
        self.img2 = None
        self.tkimg1 = None
        self.tkimg2 = None

        self.split_pos = 300
        self.dragging = False

        master.bind("<Configure>", self.render)
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.do_drag)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drag)

        self.load_images()

    def load_images(self):
        path1 = filedialog.askopenfilename(title="选择第一张图片")
        path2 = filedialog.askopenfilename(title="选择第二张图片")
        if not path1 or not path2:
            return
        self.img1 = Image.open(path1)
        self.img2 = Image.open(path2)
        self.render()

    def render(self, event=None):
        if not self.img1 or not self.img2:
            return
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        img1_resized = self.img1.resize((w, h))
        img2_resized = self.img2.resize((w, h))

        self.tkimg1 = ImageTk.PhotoImage(img1_resized)
        self.tkimg2 = ImageTk.PhotoImage(img2_resized)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tkimg2)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tkimg1, clip=self.canvas.create_rectangle(0, 0, self.split_pos, h))

        self.canvas.create_line(self.split_pos, 0, self.split_pos, h, fill="red", width=3)

    def start_drag(self, event):
        if abs(event.x - self.split_pos) < 10:
            self.dragging = True

    def do_drag(self, event):
        if self.dragging:
            self.split_pos = max(0, min(event.x, self.canvas.winfo_width()))
            self.render()

    def stop_drag(self, event):
        self.dragging = False

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageCompareTool(root)
    root.mainloop()
