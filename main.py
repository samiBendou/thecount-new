import matplotlib

from app import App

if __name__ == "__main__":
    matplotlib.use('agg')
    app = App()
    app.window.root.mainloop()
