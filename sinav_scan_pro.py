# -*- coding: utf-8 -*-
"""SINAV SCAN PRO V3 – yerel Windows tarama ve sınav PDF ayırıcı."""
import os, sys, re, shutil, subprocess, threading, tempfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import fitz
from PIL import Image, ImageTk

APP = 'SINAV SCAN PRO V3'

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
        self.hide=tk.BooleanVar(value=True)
        self.hide_pct=tk.DoubleVar(value=8); self.hide_back=tk.BooleanVar(value=False)
        self.back_pct=tk.DoubleVar(value=0)
        self.crop_margins=tk.BooleanVar(value=False)
        self.margins={'front':[0.0,0.0,0.0,0.0], 'back':[0.0,0.0,0.0,0.0]}
        self._drag=None; self._view=None
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
        ttk.Checkbutton(m,text='Ön sayfa kimlik alanını gizle',variable=self.hide,command=self.preview).pack(side='left',padx=12)
        ttk.Label(m,text='Ön üst %').pack(side='left');ttk.Spinbox(m,from_=0,to=50,increment=0.5,textvariable=self.hide_pct,width=5,command=self.preview).pack(side='left',padx=5)
        extra=ttk.Frame(mid);extra.pack(fill='x',pady=4)
        ttk.Checkbutton(extra,text='Arka sayfanın üstünü de gizle',variable=self.hide_back,command=self.preview).pack(side='left')
        ttk.Label(extra,text='Arka üst %').pack(side='left',padx=(8,0))
        ttk.Spinbox(extra,from_=0,to=50,increment=0.5,textvariable=self.back_pct,width=5,command=self.preview).pack(side='left',padx=5)
        ttk.Checkbutton(extra,text='Kenarları kırp (dört köşeden sürükle)',variable=self.crop_margins,command=self.preview).pack(side='left',padx=12)
        ttk.Button(extra,text='Kenarları sıfırla',command=self.reset_margins).pack(side='left')
        m2=ttk.Frame(mid);m2.pack(fill='x',pady=(7,0));ttk.Entry(m2,textvariable=self.out).pack(side='left',fill='x',expand=True)
        ttk.Button(m2,text='Çıktı Klasörü',command=self.choose_out).pack(side='left',padx=5)
        ttk.Button(m2,text='ORİJİNAL + KIRPILMIŞ KAYDET',command=self.process).pack(side='left')
        prev=ttk.LabelFrame(f,text='3  Sayfa kontrolü (kimlik gizleme sınırını gözle inceleyin)',padding=8);prev.pack(fill='both',expand=True)
        bar=ttk.Frame(prev);bar.pack(fill='x')
        ttk.Button(bar,text='◀ Önceki',command=lambda:self.step(-1)).pack(side='left')
        ttk.Button(bar,text='Sonraki ▶',command=lambda:self.step(1)).pack(side='left',padx=5)
        self.pageno=ttk.Label(bar,text='PDF yüklenmedi');self.pageno.pack(side='left',padx=10)
        self.canvas=tk.Canvas(prev,bg='#edf1f5',highlightthickness=0);self.canvas.pack(fill='both',expand=True,pady=6)
        self.canvas.bind('<Configure>',lambda e:self.preview())
        self.canvas.bind('<ButtonPress-1>',self.mouse_down)
        self.canvas.bind('<B1-Motion>',self.mouse_drag)
        self.canvas.bind('<ButtonRelease-1>',self.mouse_up)
        ttk.Label(prev,text='Kırmızı yatay çizgiyi sürükleyerek gizleme sınırını ayarlayın. Kenar kırpma açıksa mavi çerçeve köşelerini sürükleyin. Ayarlar ön/arka tüm öğrencilere uygulanır.').pack(anchor='w')
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
    def side(self):
        try: n=max(1,int(self.pages.get()))
        except Exception: n=2
        return 'front' if self._current % n == 0 else 'back'

    def reset_margins(self):
        self.margins[self.side()]=[0.0,0.0,0.0,0.0]
        self.preview()

    def preview(self):
        if not self._doc:return
        try:
            page=self._doc[self._current]
            cw=max(200,self.canvas.winfo_width()-20);ch=max(180,self.canvas.winfo_height()-20)
            scale=min(cw/page.rect.width,ch/page.rect.height,1.4)
            pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
            img=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
            self._img=ImageTk.PhotoImage(img)
            self.canvas.delete('all')
            x=(self.canvas.winfo_width()-pix.width)//2
            y=max(0,(self.canvas.winfo_height()-pix.height)//2)
            w,h=pix.width,pix.height
            self._view=(x,y,w,h)
            self.canvas.create_image(x,y,image=self._img,anchor='nw')
            side=self.side()
            active=self.hide.get() if side=='front' else self.hide_back.get()
            pct=float(self.hide_pct.get() if side=='front' else self.back_pct.get())
            if active:
                cut=y+h*max(0,min(50,pct))/100
                if cut>y:
                    self.canvas.create_rectangle(x,y,x+w,cut,fill='#ffb5b5',stipple='gray50',outline='')
                self.canvas.create_line(x,cut,x+w,cut,fill='#e12828',width=3)
                self.canvas.create_oval(x+w/2-6,cut-6,x+w/2+6,cut+6,fill='#e12828',outline='white')
                self.canvas.create_text(x+8,min(y+h-10,cut+12),anchor='w',text='KIRMIZI ÇİZGİ = KİMLİK GİZLEME SINIRI',fill='#9e1919',font=('Segoe UI',8,'bold'))
            if self.crop_margins.get():
                l,t,r,b=self.margins[side]
                x0=x+l*w; y0=y+t*h; x1=x+(1-r)*w; y1=y+(1-b)*h
                self.canvas.create_rectangle(x0,y0,x1,y1,outline='#1268c6',width=3,dash=(7,3))
                for hx,hy in ((x0,y0),(x1,y0),(x0,y1),(x1,y1)):
                    self.canvas.create_rectangle(hx-6,hy-6,hx+6,hy+6,fill='#1268c6',outline='white')
            n=max(1,int(self.pages.get()))
            self.pageno.config(text=f'Sayfa {self._current+1}/{len(self._doc)} | Öğrenci {self._current//n+1} | '+('Ön yüz' if side=='front' else 'Arka/devam'))
        except (ValueError,tk.TclError):pass

    def mouse_down(self,event):
        if not self._view:return
        x,y,w,h=self._view; side=self.side()
        if not (x-10<=event.x<=x+w+10 and y-10<=event.y<=y+h+10):return
        if self.crop_margins.get():
            l,t,r,b=self.margins[side]
            points={'tl':(x+l*w,y+t*h),'tr':(x+(1-r)*w,y+t*h),
                    'bl':(x+l*w,y+(1-b)*h),'br':(x+(1-r)*w,y+(1-b)*h)}
            nearest=min(points,key=lambda key:(event.x-points[key][0])**2+(event.y-points[key][1])**2)
            px,py=points[nearest]
            if abs(event.x-px)<18 and abs(event.y-py)<18:
                self._drag=('corner',nearest);return
        enabled=self.hide.get() if side=='front' else self.hide_back.get()
        if enabled:
            pct=float(self.hide_pct.get() if side=='front' else self.back_pct.get())
            if abs(event.y-(y+h*pct/100))<18:self._drag=('hide',None)

    def mouse_drag(self,event):
        if not self._drag or not self._view:return
        x,y,w,h=self._view; side=self.side();kind,handle=self._drag
        xp=min(1,max(0,(event.x-x)/w));yp=min(1,max(0,(event.y-y)/h))
        if kind=='hide':
            val=round(min(50,max(0,yp*100)),1)
            (self.hide_pct if side=='front' else self.back_pct).set(val)
        else:
            l,t,r,b=self.margins[side]
            if 'l' in handle:l=min(xp,1-r-0.10)
            if 'r' in handle:r=min(1-xp,1-l-0.10)
            if 't' in handle:t=min(yp,1-b-0.10)
            if 'b' in handle:b=min(1-yp,1-t-0.10)
            self.margins[side]=[max(0,l),max(0,t),max(0,r),max(0,b)]
        self.preview()

    def mouse_up(self,event):
        self._drag=None

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
        source=Path(self.source.get())
        if not source.is_file():
            messagebox.showwarning('PDF yok','Önce PDF açın veya tarama yapın.');return
        try:
            n=int(self.pages.get())
            if not 1<=n<=20:raise ValueError()
            f_pct=float(self.hide_pct.get());b_pct=float(self.back_pct.get())
            if not 0<=f_pct<=50 or not 0<=b_pct<=50:raise ValueError()
        except (ValueError,tk.TclError):
            messagebox.showerror('Hata','Sayfa sayısını ve gizleme oranlarını kontrol edin.');return
        doc=fitz.open(source)
        if len(doc)%n:
            total=len(doc);doc.close()
            messagebox.showerror('Sayfa sayısı uyuşmuyor',f'Toplam {total} sayfa, öğrenci başına {n} sayfaya tam bölünmüyor. İşlem iptal edildi.')
            return
        count=len(doc)//n
        prefix=re.sub(r'[^A-Za-z0-9_-]','_',self.filename.get().strip()) or 'Sinav'
        root=Path(self.out.get())/(prefix+'_ogrenciler')
        originals=root/'Orijinal';cropped=root/'Kırpılmış'
        planned=[(originals/f'{prefix}_{i:03d}.pdf',cropped/f'{prefix}_{i:03d}_K.pdf') for i in range(1,count+1)]
        clashes=[str(p) for pair in planned for p in pair if p.exists()]
        if clashes:
            doc.close();messagebox.showerror('Dosyalar zaten var','Mevcut dosyaların üzerine yazılmadı. Başka çıktı klasörü veya dosya öneki seçin.\n\n'+ '\n'.join(clashes[:4]));return
        if (self.hide.get() or self.hide_back.get()) and not messagebox.askyesno(
            'Gizleme sınırını onaylayın',
            f'Ön yüzde %{f_pct:g}, arka/devam yüzlerinde %{b_pct:g} üst alan gizlenebilir.\n'
            'KIRMIZI ÇİZGİNİN SORULARI KESMEDİĞİNİ kontrol ettiniz mi?\n\n'
            'Orijinal dosyalar ayrı klasörde eksiksiz korunacak.'):
            doc.close();return
        originals.mkdir(parents=True,exist_ok=True)
        cropped.mkdir(parents=True,exist_ok=True)
        written=[]
        try:
            for idx,(original_path,cropped_path) in enumerate(planned):
                original=fitz.open(); original.insert_pdf(doc,from_page=idx*n,to_page=(idx+1)*n-1)
                original.save(original_path,garbage=4,deflate=True)
                written.append(original_path)
                original.close()
                edited=fitz.open(original_path)
                for j,page in enumerate(edited):
                    side='front' if j==0 else 'back'
                    enabled=self.hide.get() if side=='front' else self.hide_back.get()
                    pct=f_pct if side=='front' else b_pct
                    if enabled and pct>0:
                        r=page.rect
                        area=fitz.Rect(r.x0,r.y0,r.x1,r.y0+r.height*pct/100)
                        page.add_redact_annot(area,fill=(1,1,1))
                        page.apply_redactions(images=2,graphics=1,text=0)
                    if self.crop_margins.get():
                        l,t,right,bottom=self.margins[side]
                        rect=page.rect
                        clip=fitz.Rect(rect.x0+l*rect.width,rect.y0+t*rect.height,
                                       rect.x1-right*rect.width,rect.y1-bottom*rect.height)
                        if clip.width<=1 or clip.height<=1:raise ValueError('Kırpma alanı geçersiz.')
                        page.set_cropbox(clip)
                edited.save(cropped_path,garbage=4,deflate=True)
                written.append(cropped_path)
                edited.close()
            self.status.set(f'{count} öğrenci: {originals} ve {cropped}')
            messagebox.showinfo('Tamamlandı',f'{count} orijinal + {count} kırpılmış PDF kaydedildi.\n\n{originals}\n{cropped}\n\nHer öğrenci dosyasında {n} sayfa var.')
        except Exception as exc:
            messagebox.showerror('Kayıt hatası',f'{exc}\nKısmi çıktılar mevcut olabilir; klasörü kontrol edin.')
        finally:doc.close()

if __name__=='__main__':
    root=tk.Tk();s=ttk.Style(root)
    try:s.theme_use('clam')
    except Exception:pass
    App(root);root.mainloop()
