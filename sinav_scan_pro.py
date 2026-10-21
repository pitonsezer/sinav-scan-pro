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
