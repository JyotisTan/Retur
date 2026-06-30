# ================= IMPORT =================
import ttkbootstrap as tk
from datetime import datetime, timedelta
from tkinter import messagebox
from ttkbootstrap.constants import *
from tkinter import ttk, filedialog
import pandas as pd
import threading, time, re, os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# ================= CONFIG =================
EMAIL_SENDER = "jyotisdwitanthioxak@gmail.com"
EMAIL_PASS = "jwordotihcueaskn"

data_cache = []
df = None
running = False
EMAIL_RECEIVER = ""
ATTACHMENT_FILES = []
sudah_kirim = set()
jadwal = {}  # 🔥 TAMBAH DI SINI

# ================= HELPER =================

def refresh_attachment():
    global attach_frame

    # bersihkan isi lama
    for widget in attach_frame.winfo_children():
        widget.destroy()

    tk.Label(
        attach_frame,
        text="📎 ATTACHMENT",
        font=("Segoe UI", 10, "bold"),
        foreground="#00ffff"
    ).pack(anchor="w")

    if not ATTACHMENT_FILES:
        tk.Label(
            attach_frame,
            text="No file",
            foreground="#888"
        ).pack(anchor="w")
        return

    for f in ATTACHMENT_FILES:
        row = tk.Frame(attach_frame)
        row.pack(fill="x", pady=1)

        tk.Label(
            row,
            text=f"• {os.path.basename(f)}",
            anchor="w"
        ).pack(side="left", fill="x", expand=True)

        # ❌ tombol hapus per file
        tk.Button(
            row,
            text="✖",
            width=2,
            command=lambda file=f: remove_attachment(file)
        ).pack(side="right")

    # 🧹 tombol clear all
    tk.Button(
        attach_frame,
        text="Clear All",
        command=clear_attachment
    ).pack(pady=5)
    
def remove_attachment(file):
    global ATTACHMENT_FILES
    if file in ATTACHMENT_FILES:
        ATTACHMENT_FILES.remove(file)
    refresh_attachment()
    
    
def mapping_jam(jam_str):
    try:
        t = datetime.strptime(jam_str, "%H:%M")

        # kalau ada menit → naik 1 jam
        if t.minute > 0:
            jam = t.hour + 1
        else:
            jam = t.hour

        # max mentok 23
        if jam >= 24:
            jam = 23

        return f"{jam:02d}:00"

    except:
        return jam_str

def get_hari_ini():
    hari_map = {
        "Monday": "SENIN",
        "Tuesday": "SELASA",
        "Wednesday": "RABU",
        "Thursday": "KAMIS",
        "Friday": "JUMAT",
        "Saturday": "SABTU",
        "Sunday": "MINGGU"
    }
    return hari_map[datetime.now().strftime("%A")]

def is_row_empty(row):
    return all(str(x).strip().lower() in ["", "nan"] for x in row)

def format_jam(j):
    for f in ("%H:%M:%S","%H:%M"):
        try:
            return datetime.strptime(str(j),f).strftime("%H:%M")
        except:
            pass
    return None

def cocok(jadwal, sekarang):
    try:
        t_jadwal = datetime.strptime(jadwal, "%H:%M")
        t_now = datetime.strptime(sekarang, "%H:%M")

        return t_now >= t_jadwal
    except:
        return False

def cek_tanggal_vs(text):
    try:
        dates = re.findall(r'\d{2}\.\d{2}\.\d{4}', text)
        if len(dates) >= 2:
            start = datetime.strptime(dates[0], "%d.%m.%Y")
            end = datetime.strptime(dates[1], "%d.%m.%Y")

            now = datetime.now()

            # 🔥 FIX: sampai akhir hari
            end = end.replace(hour=23, minute=59, second=59)

            return start <= now <= end
    except:
        pass
    return False

def short_text(text, max_len=80):
    return text if len(text)<=max_len else text[:max_len]+"..."

def get_status(jam, produk):
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{today}-{jam}-{produk}"

    now = datetime.now()

    try:
        jam_dt = datetime.strptime(jam, "%H:%M")
        jam_dt = jam_dt.replace(
            year=now.year,
            month=now.month,
            day=now.day
        )
    except:
        return "MENUNGGU"

    # ✅ sudah terkirim → HIJAU
    if key in sudah_kirim:
        return "TERKIRIM"

    # ⏳ belum waktunya
    if now < jam_dt:
        return "MENUNGGU"

    # ❌ lewat waktu
    return "EXPIRED"
# ================= LOG =================
def log(msg):
    log_box.insert("end", f"{datetime.now().strftime('%H:%M:%S')} | {msg}\n")
    log_box.see("end")

# ================= EMAIL =================
def kirim(produk_list, jam, kategori, info=""):

    try:
        rec = [e.strip() for e in EMAIL_RECEIVER.split(",") if e.strip()]
        if not rec:
            log("Email kosong")
            return False

        # ===== SUBJECT FIX DI SINI =====
        hari_ini = get_hari_ini()

        subject_map = {
            "HARI": hari_ini,
            "HARI INI": hari_ini,
            "VS": f"VS {info}" if info else "VS"
        }

        subject_kategori = subject_map.get(kategori.upper(), kategori)
        jam_fix = mapping_jam(jam)
        subject = f"REMINDER IKLAN ({jam_fix}) - {subject_kategori}"

        # ===== EMAIL =====
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = ", ".join(rec)

        body=f"Kategori: {kategori}\n\nProduk:\n"
        for p in produk_list:
            body+=f"- {p}\n"

        body+=f"\nJam: {jam}\n"
        if info:
            body+=f"Info: {info}\n"

        msg.attach(MIMEText(body,"plain"))

        for f in ATTACHMENT_FILES:
            if os.path.exists(f):
                part=MIMEBase("application","octet-stream")
                part.set_payload(open(f,"rb").read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition",
                    f'attachment; filename="{os.path.basename(f)}"')
                msg.attach(part)

        s=smtplib.SMTP_SSL("smtp.gmail.com",465)
        s.login(EMAIL_SENDER,EMAIL_PASS)
        s.sendmail(EMAIL_SENDER,rec,msg.as_string())
        s.quit()
        
        hari_ini = get_hari_ini()
        rec_list = [e.strip() for e in EMAIL_RECEIVER.split(",") if e.strip()]
        
        email_tujuan = ", ".join(rec_list)
        log_text = f"✔ {hari_ini} {jam} | {kategori} | TERKIRIM → {email_tujuan}\n"

        status_email_box.insert("end", log_text)
        status_email_box.see("end")
        
        return True
    
    except Exception as e:
        error_text = f"❌ {get_hari_ini()} {jam} | {kategori} | GAGAL\n"
        status_email_box.insert("end", error_text)
        status_email_box.see("end")

    log(f"ERROR: {e}")
    return False
    


# ================= DASHBOARD =================
def update_dashboard():
    tree.delete(*tree.get_children())
    if df is None:
        return

    now=datetime.now()
    hari_map={
        "Monday":"senin","Tuesday":"selasa","Wednesday":"rabu",
        "Thursday":"kamis","Friday":"jumat","Saturday":"sabtu","Sunday":"minggu"
    }
    hari_ini=hari_map[now.strftime("%A")]

    data_by_jam={}

    for _,row in df.iterrows():
        if is_row_empty(row):
            continue

        no=str(row[df.columns[0]]).strip().lower()
        produk=str(row[df.columns[1]]).strip()

        if not produk or produk.lower()=="nan":
            continue

        if no in ["1","01"]:
            tipe="HARIAN"
        elif hari_ini in no:
            tipe="HARI"
        elif "vs" in no:
            if cek_tanggal_vs(produk):
                tipe="VS"
            else:
                continue
        else:
            continue

        for col in df.columns[2:]:
            val=str(row[col]).strip()
            if val in ["","0","nan"]:
                continue

            jam=format_jam(col)
            if not jam:
                continue

            data_by_jam.setdefault(jam,{"HARIAN":[],"HARI":[],"VS":[]})
            data_by_jam[jam][tipe].append(produk)

    for jam in sorted(data_by_jam.keys()):
      
        
        now_str = datetime.now().strftime("%H:%M")

        tag_jam = ("jam",)
        if cocok(jam, now_str):
            tag_jam = ("jam", "active")

        tree.insert("", "end", values=(f"🕒 {jam}","","",""), tags=tag_jam)
        
        

        grup=data_by_jam[jam]

        def insert_section(title,data):
            if not data:
                return
            
            tag_hari = title.lower()
            tree.insert("",
             "end",
            values=(f"➤ {title}","","",""),
            tags=("section", tag_hari)
            )
       
            # tentukan kategori asli (sekali saja)
            if title == "HARIAN":
                kategori_asli = "HARIAN"
            elif title == "VS":
                 kategori_asli = "VS"
            else:
                kategori_asli = "HARI"

            # ambil status SEKALI per kategori
            status_kategori = get_status(jam, kategori_asli)

            for produk in data:
                if status_kategori == "TERKIRIM":
                    tag = "done"
                elif status_kategori == "EXPIRED":
                    tag = "expired"
                else:
                    tag = "pending"

                tree.insert(
                     "",
                    "end",
                    values=(title, jam, short_text(produk), status_kategori),
                    tags=(tag,)
                 )

        hari_ini_display = get_hari_ini()  # SENIN, SELASA, JUMAT, dll
        insert_section("HARIAN", grup["HARIAN"])
        insert_section(hari_ini_display, grup["HARI"])
        insert_section("VS", grup["VS"])
        
        

def auto_refresh():
    if df is not None:
        update_dashboard()
    app.after(5000, auto_refresh)  # refresh tiap 5 detik
def test_email():
    global EMAIL_RECEIVER

    # backup email lama
    backup = EMAIL_RECEIVER

    # pakai email test
    EMAIL_RECEIVER = "itsabarho3@gmail.com"

    sukses = kirim(
        ["TEST PRODUK - Email berhasil 🚀"],
        datetime.now().strftime("%H:%M"),
        "TEST"
    )

    if sukses:
        log("Test email terkirim")
    else:
        log("Test email gagal")

    # balikin email semula
    EMAIL_RECEIVER = backup


def loop():
    global sudah_kirim

    while running:
        now = datetime.now().strftime("%H:%M")
        today = datetime.now().strftime("%Y-%m-%d")

        batch = {}

        for row in data_cache:
            if is_row_empty(row):
                continue

            no = str(row[df.columns[0]]).strip().lower()
            produk = str(row[df.columns[1]]).strip()

            if not produk or produk.lower() == "nan":
                continue

            # ===== HARIAN =====
            if no in ["1", "01"]:
                kategori = "HARIAN"

            # ===== HARI =====
            elif any(h in no for h in ["senin","selasa","rabu","kamis","jumat","sabtu","minggu"]):

                hari_map = {
                    "monday": "senin",
                    "tuesday": "selasa",
                    "wednesday": "rabu",
                    "thursday": "kamis",
                    "friday": "jumat",
                    "saturday": "sabtu",
                    "sunday": "minggu"
                }

                hari_now = hari_map[datetime.now().strftime("%A").lower()]

                hari_list = re.split(r'[,&/]', no)
                hari_list = [h.strip() for h in hari_list]

                if hari_now in hari_list:
                    kategori = "HARI"
                else:
                    continue

            # ===== VS =====
            elif "vs" in no:
                if cek_tanggal_vs(produk):
                    kategori = "VS"
                else:
                    continue
            else:
                continue

            for col in df.columns[2:]:
                if str(row[col]) not in ["","0","nan"]:
                    jam = format_jam(col)

                    if jam and cocok(jam, now):

                        slot = mapping_jam(jam)
                        now_dt = datetime.strptime(now, "%H:%M")
                        slot_dt = datetime.strptime(slot, "%H:%M")

                    # ❌ kalau sudah lewat slot → jangan kirim
                        if now_dt >= slot_dt:
                            continue
                        batch.setdefault(jam, {})
                        batch[jam].setdefault(kategori, [])
                        batch[jam][kategori].append(produk)

        
        
        for jam, kategori_data in batch.items():
            for kategori, produk_list in kategori_data.items():

                key = f"{today}-{jam}-{kategori}"

                if key in sudah_kirim:
                    continue

                # 🔥 LOCK DULU SEBELUM KIRIM
                sudah_kirim.add(key)
                sukses = kirim(produk_list, jam, kategori)
                
                if sukses:
                     auto_refresh()  # tiap 5 detik
                     time.sleep(1)
        
        time.sleep(1)


def build_schedule():
    global jadwal
    jadwal = {}  # {"08:00": {"HARIAN":[...], "HARI":[...], "VS":[...]}, ...}

    hari_map = {
        "Monday":"senin","Tuesday":"selasa","Wednesday":"rabu",
        "Thursday":"kamis","Friday":"jumat","Saturday":"sabtu","Sunday":"minggu"
    }
    hari_ini = hari_map[datetime.now().strftime("%A")]

    for row in data_cache:
        if is_row_empty(row):
            continue

        no = str(row[df.columns[0]]).strip().lower()
        produk = str(row[df.columns[1]]).strip()
        if not produk or produk.lower() == "nan":
            continue

        # tentukan kategori
        if no in ["1","01"]:
            kategori = "HARIAN"
        elif any(h in no for h in ["senin","selasa","rabu","kamis","jumat","sabtu","minggu"]):
            hari_list = [h.strip() for h in re.split(r'[,&/]', no)]
            if hari_ini in hari_list:
                kategori = "HARI"
            else:
                continue
        elif "vs" in no:
            if cek_tanggal_vs(produk):
                kategori = "VS"
            else:
                continue
        else:
            continue

        # kumpulkan per jam
        for col in df.columns[2:]:
            val = str(row[col]).strip()
            if val in ["","0","nan"]:
                continue

            jam = format_jam(col)
            if not jam:
                continue

            jadwal.setdefault(jam, {"HARIAN":[], "HARI":[], "VS":[]})
            jadwal[jam][kategori].append(produk)


# ================= ACTION =================


def load():
    global df, data_cache

    file = filedialog.askopenfilename(filetypes=[("ODS","*.ods")])
    if file:
        df = pd.read_excel(file, engine="odf")

        # 🔥 simpan ke cache (biar loop ringan)
        data_cache = df.to_dict("records")

        log_box.delete("1.0", "end")
        log(f"📂 Load file: {os.path.basename(file)}")

        update_dashboard()

def start():
    global running, sudah_kirim

    if df is None:
        messagebox.showwarning(
            "Peringatan",
            "⚠️ Load file terlebih dahulu sebelum START!"
        )
        log("❌ Gagal start: file belum diload")
        return

    sudah_kirim.clear()
    running = True

    status_led.config(text="● RUNNING", foreground="#00ff00")

    threading.Thread(target=loop, daemon=True).start()
    log("STARTED")
    
def blink_led():
    if running:
        current = status_led.cget("foreground")
        status_led.config(foreground="#00ff00" if current == "#003300" else "#003300")
        app.after(500, blink_led)

# panggil di start()
blink_led()

def stop():
    global running
    running = False

    status_led.config(text="● STOP", foreground="red")

    log("STOPPED")
    
def set_email():
    global EMAIL_RECEIVER
    selected=[e for v,e in email_vars if v.get()]
    manual=entry_manual.get()
    if manual:
        selected+=manual.split(",")
    EMAIL_RECEIVER=",".join(selected)
    log("Email set")

def pilih_file():
    global ATTACHMENT_FILES

    files = filedialog.askopenfilenames()

    if files:
        for f in files:
            if f not in ATTACHMENT_FILES:   # biar tidak dobel
                ATTACHMENT_FILES.append(f)

    refresh_attachment()

def clear_attachment():
    global ATTACHMENT_FILES
    ATTACHMENT_FILES = []
    refresh_attachment()
    
def reset_log():
    # clear log aktivitas
    log_box.delete("1.0", "end")

    # clear log email terkirim
    status_email_box.delete("1.0", "end")

    # optional: kasih tulisan default lagi
    status_email_box.insert("end", "Belum ada pengiriman\n")

    log("Log di-reset")
   
    
# ================= GUI =================
app=tk.Window(themename="darkly")
app.title("Reminder PRO FINAL")
app.state("zoomed")  # auto fullscreen (Windows)

jam_label=tk.Label(app,font=("Segoe UI",11,"bold"))
jam_label.pack()

def update_jam():
    jam_label.config(text=datetime.now().strftime("%A, %d-%m-%Y | %H:%M:%S"))
    app.after(1000,update_jam)

update_jam()

tk.Label(app,text="REMINDER IKLAN SYSTEM",
         font=("Segoe UI",18,"bold")).pack(pady=10)

frame_top = tk.Frame(app)
frame_top.pack(fill="x", padx=10, pady=5)

email_frame = ttk.LabelFrame(frame_top, text="Email")
email_frame.pack(side="left", fill="both", expand=True, padx=5)

frame_btn = tk.Frame(frame_top)
frame_btn.pack(side="right", fill="y", padx=5)

tk.Button(frame_btn, text="Load File", width=15, command=load).pack(pady=3)
tk.Button(frame_btn, text="Attachment", width=15, command=pilih_file).pack(pady=3)
tk.Button(frame_btn, text="Start", width=15, command=start).pack(pady=3)
tk.Button(frame_btn, text="Stop", width=15, command=stop).pack(pady=3)
tk.Button(frame_btn, text="Test Email", width=15, command=test_email).pack(pady=3)

tk.Button(
    frame_btn,
    text="Reset Log",
    width=15,
    command=reset_log
).pack(pady=3)

status_led = tk.Label(
    frame_btn,
    text="● STOP",
    font=("Segoe UI", 10, "bold"),
    foreground="red"
)
status_led.pack(pady=10)
select_all_var = tk.BooleanVar()

def toggle_all_email():
    for v, _ in email_vars:
        v.set(select_all_var.get())

tk.Checkbutton(
    email_frame,
    text="✔ Pilih Semua",
    variable=select_all_var,
    command=toggle_all_email
).pack(anchor="w")

emails=["auditsabarho2@gmail.com",
    "andreydermawansm@gmail.com",
    "afifahckk@gmail.com",
    "onlinesabarmaju@gmail.com"]
email_vars=[]
for e in emails:
    v=tk.BooleanVar()
    tk.Checkbutton(email_frame,text=e,variable=v).pack(anchor="w")
    email_vars.append((v,e))

entry_manual=tk.Entry(email_frame)
entry_manual.pack(fill="x")

tk.Button(email_frame,text="Set Email",command=set_email).pack()

status_email_box = tk.Text(
    app,
    height=6,
    font=("Consolas", 10),
    bg="#1e1e1e",
    fg="#e6e6e6",
    insertbackground="white",
    spacing1=4,
    spacing2=2,
    spacing3=4
)

status_email_box.pack(fill="x", padx=10, pady=3)

status_email_box.tag_config("title", foreground="#00ffff", font=("Segoe UI", 10, "bold"))
status_email_box.tag_config("success", foreground="#00ff9c")
status_email_box.tag_config("error", foreground="#ff4d4d")

status_email_box.insert("end", "Belum ada pengiriman\n")
main_frame = tk.Frame(app)
main_frame.pack(fill="both", expand=True)

frame_dash = tk.Frame(main_frame)
frame_dash.pack(side="left", fill="both", expand=True)

frame_log = tk.Frame(main_frame)
frame_log.pack(side="right", fill="y")

# ================= ATTACHMENT =================
attach_frame = tk.Frame(frame_log)
attach_frame.pack(fill="x", padx=5, pady=5)

tk.Label(
    attach_frame,
    text="📎 ATTACHMENT",
    font=("Segoe UI", 10, "bold"),
    foreground="#00ffff"
).pack(anchor="w")

attach_label = tk.Label(
    attach_frame,
    text="No file",
    justify="left",
    anchor="nw",
    font=("Segoe UI", 9),
    foreground="#cccccc"
)
attach_label.pack(fill="x")

tree=ttk.Treeview(frame_dash,
    columns=("Kategori","Jam","Produk","Status"),
    show="headings")

tree.pack(side="left",fill="both",expand=True)

scroll=ttk.Scrollbar(frame_dash,command=tree.yview)
scroll.pack(side="right",fill="y")
tree.configure(yscrollcommand=scroll.set)

tree.heading("Kategori",text="Kategori")
tree.heading("Jam",text="Jam")
tree.heading("Produk",text="Produk")
tree.heading("Status",text="Status")

tree.column("Kategori",width=120)
tree.column("Jam",width=80)
tree.column("Produk",width=600)
tree.column("Status",width=120)

tree.tag_configure("jam",background="#003366",foreground="white")
tree.tag_configure("section",background="#222",foreground="#00ffff")
tree.tag_configure("done",background="#003300",foreground="#00ff9c")
tree.tag_configure("pending",background="#2b2b2b",foreground="#ccc")

tree.tag_configure("senin", background="#1f3b4d")
tree.tag_configure("selasa", background="#4d3b1f")
tree.tag_configure("rabu", background="#3b4d1f")
tree.tag_configure("kamis", background="#4d1f3b")
tree.tag_configure("jumat", background="#1f4d3b")
tree.tag_configure("sabtu", background="#4d4d1f")
tree.tag_configure("minggu", background="#3b1f4d")

tree.tag_configure("expired", background="#3a0000", foreground="#ff4d4d")

tree.tag_configure("active", background="#004d00", foreground="#00ff9c")


# ================= LOG =================


tk.Label(
    frame_log,
    text="LOG AKTIVITAS",
    font=("Segoe UI", 10, "bold")
).pack()

log_box = tk.Text(
    frame_log,
    width=35,
    font=("Consolas", 9)
)
log_box.pack(fill="both", expand=True, padx=5, pady=5)

tk.Label(
    frame_log,
    text="LOG AKTIVITAS",
    font=("Segoe UI", 10, "bold")
).pack()




auto_refresh()

app.mainloop()