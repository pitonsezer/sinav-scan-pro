# -*- coding: utf-8 -*-
"""SINAV SCAN PRO V2 – yerel Windows tarama ve sınav PDF ayırıcı."""
import os, sys, re, shutil, subprocess, threading, tempfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import fitz
from PIL import Image, ImageTk

APP = 'SINAV SCAN PRO V2'

def naps2_path():
    """Find the CLI, never silently substitute the GUI or an installer."""
    bases = [Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'NAPS2',
             Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'NAPS2',
             Path.home() / 'AppData' / 'Local' / 'Programs' / 'NAPS2']
    for base in bases:
        for name in ('NAPS2.Console.exe', 'naps2.console.exe'):
            candidate = base / name
            if candidate.is_file():
                return str(candidate)
    for name in ('NAPS2.Console.exe', 'naps2.console'):
        result = shutil.which(name)
        if result and Path(result).is_file():
            return result
    return None


def valid_console(path):
    return bool(path and Path(path).is_file() and Path(path).name.lower() == 'naps2.console.exe')


def missing_console_message():
    return ('NAPS2 komut satırı bileşeni (NAPS2.Console.exe) bulunamadı.\n\n'
            'NAPS2.exe normal arayüzdür; tarayıcı listesi komutlarını çalıştırmaz. '
            'Kurulum dosyasını da seçmeyin.\n\n'
            'NAPS2 kurulumunu onarın veya resmî NAPS2 paketinden Console bileşenini yükleyin. '
            'Ardından NAPS2 Konumu ile NAPS2.Console.exe dosyasını seçin.\n'
            'Tarayıcı bağlı değilken cihaz listesi boş olabilir.')

class App:
    def __init__(self, root):
        self.root=root; root.title(APP); root.geometry('1040x780'); root.minsize(860,650)
        self.source=tk.StringVar(); self.out=tk.StringVar(value=str(Path.home()/'Documents'/'Sinav_Scan_Pro'))
        self.device=tk.StringVar(); self.devices=[]; self.driver=tk.StringVar(value='twain'); self.dpi=tk.StringVar(value='300')
        self.mode=tk.StringVar(value='gray'); self.sides=tk.StringVar(value='duplex'); self.pages=tk.IntVar(value=2)
        self.hide=tk.BooleanVar(value=True); self.hide_pct=tk.DoubleVar(value=13)
        self.filename=tk.StringVar(value='Sinav'); self.naps=tk.StringVar(value=naps2_path() or '')
        self.status=tk.StringVar(value='Hazır. Önce örnek PDF açabilir veya tarayıcıdan tarayabilirsiniz.')
        self._img=None; self._doc=None; self._current=0
        self.build()
    def build(self):
        f=ttk.Frame(self.root, padding=14); f.pack(fill='both',expand=True)
        ttk.Label(f,text='SINAV SCAN PRO',font=('Segoe UI',20,'bold')).pack(anchor='w')
        ttk.Label(f,text='Çift taraflı ADF  •  İkişer sayfalık öğrenci PDF’leri  •  Öğrenci bilgilerini yerel ortamda gizleme').pack(anchor='w',pady=(0,12))
        top=ttk.LabelFrame(f,text='1  Kaynak: mevcut PDF veya tarayıcı',padding=10);top.pack(fill='x')
        row=ttk.Frame(top);row.pack(fill='x');ttk.Entry(row,textvariable=self.source).pack(side='left',fill='x',expand=True)
        ttk.Button(row,text='PDF Aç',command=self.choose).pack(side='left',padx=5)
        ttk.Button(row,text='NAPS2 Konumu',command=self.choose_naps).pack(side='left')
        dr=ttk.Frame(top);dr.pack(fill='x',pady=6)
        ttk.Label(dr,text='Sürücü').pack(side='left');ttk.Combobox(dr,textvariable=self.driver,values=['twain','wia','escl'],width=7,state='readonly').pack(side='left',padx=5)
        ttk.Label(dr,text='Cihaz adı').pack(side='left');self.device_combo=ttk.Combobox(dr,textvariable=self.device,width=29,values=[],state='normal');self.device_combo.pack(side='left',padx=5)
        ttk.Button(dr,text='Cihazları Bul',command=self.detect).pack(side='left',padx=5)
        ttk.Label(dr,text='ADF').pack(side='left',padx=(10,2));ttk.Combobox(dr,textvariable=self.sides,values=['duplex','feeder','glass'],width=8,state='readonly').pack(side='left')
        dr2=ttk.Frame(top);dr2.pack(fill='x')
        ttk.Label(dr2,text='Çözünürlük').pack(side='left');ttk.Combobox(dr2,textvariable=self.dpi,values=['150','200','300','600'],width=7,state='readonly').pack(side='left',padx=5)
        ttk.Label(dr2,text='Renk').pack(side='left');ttk.Combobox(dr2,textvariable=self.mode,values=['gray','color','bw'],width=9,state='readonly').pack(side='left',padx=5)
        self.scanbtn=ttk.Button(dr2,text='ADF’DEN TARA',command=self.scan);self.scanbtn.pack(side='right')
        mid=ttk.LabelFrame(f,text='2  PDF hazırlama seçenekleri',padding=10);mid.pack(fill='x',pady=10)
        m=ttk.Frame(mid);m.pack(fill='x')
        ttk.Label(m,text='Öğrenci başına sayfa').pack(side='left');ttk.Spinbox(m,from_=1,to=20,textvariable=self.pages,width=5).pack(side='left',padx=7)
        ttk.Label(m,text='Dosya öneki').pack(side='left');ttk.Entry(m,textvariable=self.filename,width=15).pack(side='left',padx=7)
        ttk.Checkbutton(m,text='1. sayfanın üstündeki kimlik alanını kalıcı kaldır',variable=self.hide).pack(side='left',padx=12)
        ttk.Label(m,text='Üstten %').pack(side='left');ttk.Spinbox(m,from_=2,to=35,increment=1,textvariable=self.hide_pct,width=5).pack(side='left',padx=5)
        m2=ttk.Frame(mid);m2.pack(fill='x',pady=(7,0));ttk.Entry(m2,textvariable=self.out).pack(side='left',fill='x',expand=True)
        ttk.Button(m2,text='Çıktı Klasörü',command=self.choose_out).pack(side='left',padx=5)
        ttk.Button(m2,text='İKİŞER SAYFA AYIR VE KAYDET',command=self.process).pack(side='left')
        prev=ttk.LabelFrame(f,text='3  Sayfa kontrolü (kimlik gizleme sınırını gözle inceleyin)',padding=8);prev.pack(fill='both',expand=True)
        bar=ttk.Frame(prev);bar.pack(fill='x')
        ttk.Button(bar,text='◀ Önceki',command=lambda:self.step(-1)).pack(side='left')
        ttk.Button(bar,text='Sonraki ▶',command=lambda:self.step(1)).pack(side='left',padx=5)
        self.pageno=ttk.Label(bar,text='PDF yüklenmedi');self.pageno.pack(side='left',padx=10)
        self.canvas=tk.Canvas(prev,bg='#edf1f5',highlightthickness=0);self.canvas.pack(fill='both',expand=True,pady=6)
        self.canvas.bind('<Configure>',lambda e:self.preview())
        ttk.Label(f,textvariable=self.status,foreground='#1b527e',wraplength=970).pack(anchor='w',pady=(5,0))
    def choose(self):
        p=filedialog.askopenfilename(filetypes=[('PDF dosyası','*.pdf')]);
        if p:self.load(p)
    def load(self,p):
        try:
            if self._doc:self._doc.close()
            self._doc=fitz.open(p);self.source.set(p);self._current=0;self.preview()
            self.status.set(f'PDF açıldı: {len(self._doc)} sayfa. Sayfa sıralamasını kontrol edin.')
        except Exception as e:messagebox.showerror('PDF açılamadı',str(e))
    def choose_naps(self):
        p=filedialog.askopenfilename(filetypes=[('NAPS2 Console','NAPS2.Console.exe')]);
        if p:
            if valid_console(p): self.naps.set(p)
            else: messagebox.showerror('Yanlış dosya',missing_console_message())
    def choose_out(self):
        p=filedialog.askdirectory();
        if p:self.out.set(p)
    def preview(self):
        if not self._doc:return
        try:
            page=self._doc[self._current]; cw=max(300,self.canvas.winfo_width()-20);ch=max(250,self.canvas.winfo_height()-20)
            scale=min(cw/page.rect.width,ch/page.rect.height,1.4)
            pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
            img=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
            self._img=ImageTk.PhotoImage(img)
            self.canvas.delete('all'); x=(self.canvas.winfo_width()-pix.width)//2;y=max(0,(self.canvas.winfo_height()-pix.height)//2)
            self.canvas.create_image(x,y,image=self._img,anchor='nw')
            n=max(1,int(self.pages.get())); is_front=(self._current%n==0)
            if self.hide.get() and is_front:
                h=int(pix.height*float(self.hide_pct.get())/100)
                self.canvas.create_rectangle(x,y,x+pix.width,y+h,fill='#ffc6c6',stipple='gray50',outline='red',width=2)
                self.canvas.create_text(x+10,y+min(20,h//2),anchor='w',text='GİZLENECEK KISIM',fill='black')
            self.pageno.config(text=f'Sayfa {self._current+1}/{len(self._doc)} | Öğrenci {(self._current//n)+1} | '+('Ön' if is_front else 'Devam'))
        except Exception:pass
    def step(self,k):
        if self._doc:self._current=max(0,min(len(self._doc)-1,self._current+k));self.preview()
    def detect(self):
        exe=self.naps.get() or naps2_path()
        if not valid_console(exe):
            messagebox.showwarning('NAPS2 Console eksik',missing_console_message());return
        self.naps.set(exe)
        self.status.set('Tarayıcılar aranıyor...')
        def work():
            try:
                p=subprocess.run([exe,'--listdevices','--driver',self.driver.get()],
                                 capture_output=True,text=True,timeout=45,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if p.returncode != 0:
                    raise RuntimeError((p.stderr or p.stdout or 'NAPS2 cihaz arama hatası').strip())
                devices=[line.strip() for line in p.stdout.splitlines() if line.strip()]
                def done():
                    self.devices=devices;self.device_combo.configure(values=devices)
                    if devices:
                        self.device.set(devices[0]);self.status.set(f'{len(devices)} tarayıcı bulundu.')
                        messagebox.showinfo('Tarayıcılar','Bulunan cihazlar:\n'+'\n'.join(devices))
                    else:
                        self.status.set('Bu sürücüyle tarayıcı bulunamadı. WIA/TWAIN seçimini değiştirip deneyin.')
                        messagebox.showinfo('Tarayıcılar','Cihaz bulunamadı. Tarayıcı bağlı değilse normaldir. WIA veya TWAIN deneyin.')
                self.root.after(0,done)
            except Exception as e:
                self.root.after(0,lambda err=str(e):messagebox.showerror('Tarayıcı aranamadı',err))
        threading.Thread(target=work,daemon=True).start()
    def scan(self):
        exe=self.naps.get()
        if not valid_console(exe):messagebox.showwarning('NAPS2 Console eksik',missing_console_message());return
        if not self.device.get().strip():messagebox.showwarning('Cihaz adı','Önce Cihazları Bul düğmesiyle tarayıcıyı seçin ve adını yazın.');return
        if not messagebox.askokcancel('ADF taraması','ADF’ye birkaç deneme yaprağı yerleştirdiniz mi?\nİlk denemede ön-arka sayfa sırasını kontrol edeceğiz.'):return
        self.scanbtn.config(state='disabled');self.status.set('Tarayıcıdan PDF alınıyor; işlem bitene kadar bekleyin...')
        def work():
            try:
                fd,tmp=tempfile.mkstemp(suffix='.pdf',prefix='sinav_scan_');os.close(fd);os.unlink(tmp)
                cmd=[exe,'-o',tmp,'--noprofile','--driver',self.driver.get(),'--device',self.device.get(), '--source',self.sides.get(),'--pagesize','a4','--dpi',self.dpi.get(),'--bitdepth',self.mode.get(),'--disableocr','--progress']
                p=subprocess.run(cmd,capture_output=True,text=True,timeout=1200)
                if p.returncode!=0 or not Path(tmp).is_file():raise RuntimeError((p.stderr or p.stdout or 'Tarama başarısız')[:1400])
                self.root.after(0,lambda:self.load(tmp))
            except Exception as e:self.root.after(0,lambda err=str(e):messagebox.showerror('Tarama hatası',err))
            finally:self.root.after(0,lambda:self.scanbtn.config(state='normal'))
        threading.Thread(target=work,daemon=True).start()
    def process(self):
        source=Path(self.source.get());
        if not source.is_file():messagebox.showwarning('PDF yok','Önce PDF açın veya tarama yapın.');return
        try:n=int(self.pages.get());assert 1<=n<=20
        except Exception:messagebox.showerror('Hata','Öğrenci başına sayfa 1–20 olmalı.');return
        doc=fitz.open(source)
        if len(doc)%n:
            doc.close();messagebox.showerror('Sayfa sayısı uyuşmuyor',f'Toplam sayfa sayısı öğrenci başına {n} sayfaya tam bölünmüyor.\nİşlem durduruldu: muhtemel eksik veya fazla sayfa!');return
        out=Path(self.out.get()); out.mkdir(parents=True,exist_ok=True)
        count=len(doc)//n;prefix=re.sub(r'[^A-Za-z0-9_-]','_',self.filename.get().strip()) or 'Sinav'
        dest=out/(prefix+'_ogrenciler')
        if dest.exists() and any(dest.iterdir()):
            doc.close();messagebox.showerror('Var olan dosyalar','Çıktı klasörü dolu. Mevcut öğrenci dosyalarını korumak için işlem iptal edildi. Farklı bir ad/klasör seçin.');return
        if self.hide.get():
            if not messagebox.askyesno('Kimlik alanı kontrolü',f'Her öğrencinin yalnızca ilk sayfasının ÜST %{self.hide_pct.get():g} bölümü KALICI OLARAK silinecek.\nÖnizlemedeki kırmızı alanın soruları kesmediğini kontrol ettiniz mi?'):doc.close();return
        dest.mkdir(exist_ok=True)
        try:
            for idx in range(count):
                target=fitz.open();target.insert_pdf(doc,from_page=idx*n,to_page=(idx+1)*n-1)
                if self.hide.get():
                    page=target[0];r=page.rect; area=fitz.Rect(r.x0,r.y0,r.x1,r.y0+r.height*float(self.hide_pct.get())/100)
                    page.add_redact_annot(area,fill=(1,1,1));page.apply_redactions(images=2,graphics=1,text=0)
                name=dest/f'{prefix}_{idx+1:03d}.pdf'
                target.save(name,garbage=4,deflate=True);target.close()
            doc.close();self.status.set(f'Tamamlandı: {count} dosya → {dest}')
            messagebox.showinfo('İşlem tamamlandı',f'{count} öğrenci PDF’si oluşturuldu.\n\n{dest}\n\nOrijinal PDF değiştirilmedi. Her dosyada {n} sayfa var.')
        except Exception as e:
            doc.close();messagebox.showerror('İşlem tamamlanamadı',f'{e}\nKısmi çıktı oluşmuş olabilir; klasörü kontrol edin.')

if __name__=='__main__':
    root=tk.Tk();s=ttk.Style(root)
    try:s.theme_use('clam')
    except Exception:pass
    App(root);root.mainloop()
