import gi
import subprocess
import psutil
from threading import Thread

gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, GLib, AyatanaAppIndicator3

class SparkMonitor:
    def __init__(self):
        self.indicator = AyatanaAppIndicator3.Indicator.new(
            "spark-monitor",
            "utilities-system-monitor",
            AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
        
        self.menu = Gtk.Menu()
        
        self.cpu_items = [Gtk.MenuItem(label="") for _ in range(5)]
        self.gpu_items = [Gtk.MenuItem(label="") for _ in range(5)]
        
        # CPU Section
        cpu_title = Gtk.MenuItem(label="=== Top 5 CPU Processes ===")
        cpu_title.set_sensitive(False)
        self.menu.append(cpu_title)
        for item in self.cpu_items: self.menu.append(item)
        
        self.menu.append(Gtk.SeparatorMenuItem())
        
        # GPU Section
        gpu_title = Gtk.MenuItem(label="=== Top 5 GPU Processes ===")
        gpu_title.set_sensitive(False)
        self.menu.append(gpu_title)
        for item in self.gpu_items: self.menu.append(item)
        
        self.menu.append(Gtk.SeparatorMenuItem())
        
        quit_item = Gtk.MenuItem(label="Quit Spark Monitor")
        quit_item.connect("activate", Gtk.main_quit)
        self.menu.append(quit_item)
        
        self.menu.show_all()
        self.indicator.set_menu(self.menu)

        # Exact character match for the guide to prevent any resizing
        self.guide = "🔴 CPU: 100% | 🔴 GPU: 100%"
        
        Thread(target=self.update_loop, daemon=True).start()

    def get_gpu_util(self):
        try:
            cmd = ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"]
            out = subprocess.check_output(cmd, encoding='utf-8')
            return int(out.strip().split('\n')[0])
        except Exception:
            return 0

    def get_top_cpu(self):
        try:
            out = subprocess.check_output(["ps", "-eo", "pcpu,comm", "--sort=-pcpu"], encoding="utf-8")
            lines = [line.strip() for line in out.strip().split('\n')[1:6]]
            return [f"{line.split()[0]}%  {line.split(maxsplit=1)[1]}" for line in lines]
        except Exception:
            return ["N/A"]

    def get_top_gpu(self):
        try:
            out = subprocess.check_output(["nvidia-smi"], encoding="utf-8")
            procs = []
            capture = False
            for line in out.split('\n'):
                if "Processes:" in line:
                    capture = True
                    continue
                if capture and "===" in line:
                    continue
                if capture and "MiB" in line:
                    parts = line.split()
                    mem, name = parts[-2], parts[-3].split('/')[-1]
                    procs.append(f"{mem}  {name}")
            return procs[:5] if procs else ["No GPU processes"]
        except Exception:
            return ["N/A"]

    def get_status_dot(self, value):
        if value > 80:
            return "🔴"
        elif value > 50:
            return "🟡"
        return "🟢"

    def update_menu_ui(self, top_cpu, top_gpu, label):
        self.indicator.set_label(label, self.guide)
        
        for i, item in enumerate(self.cpu_items):
            if i < len(top_cpu):
                item.set_label(top_cpu[i])
                item.show()
            else:
                item.hide()
                
        for i, item in enumerate(self.gpu_items):
            if i < len(top_gpu):
                item.set_label(top_gpu[i])
                item.show()
            else:
                item.hide()

    def update_loop(self):
        while True:
            cpu = psutil.cpu_percent(interval=1)
            gpu = self.get_gpu_util()
            
            top_cpu = self.get_top_cpu()
            top_gpu = self.get_top_gpu()
            
            cpu_dot = self.get_status_dot(cpu)
            gpu_dot = self.get_status_dot(gpu)
            
            # {:3d} strictly formats the number to be 3 characters wide (e.g. "  5", " 50", "100")
            label = f"{cpu_dot} CPU: {int(cpu):3d}% | {gpu_dot} GPU: {gpu:3d}%"
            
            GLib.idle_add(self.update_menu_ui, top_cpu, top_gpu, label)

if __name__ == "__main__":
    SparkMonitor()
    Gtk.main()