"""
generate_data_js.py
Konversi data/jadwal.csv → docs/data.js + docs/data.json + docs/version.json
Dijalankan oleh GitHub Actions setelah fetch_jadwal.py selesai.

- data.js      : di-load saat halaman dibuka (render pertama tanpa fetch tambahan)
- version.json : kecil, di-poll frontend tiap beberapa menit
- data.json    : payload lengkap, hanya diambil frontend kalau versi berubah
"""

import os, sys, json, csv, re, subprocess, hashlib
from collections import Counter
from datetime import datetime, timezone, timedelta

CSV_PATH          = "data/jadwal.csv"
OUT_PATH          = "docs/data.js"
OUT_JSON_PATH     = "docs/data.json"
OUT_VERSION_PATH  = "docs/version.json"

# Nomor sesi resmi ditentukan oleh JAM MULAI. Jam selesai boleh berbeda antar
# periode (mis. 18.30-20.30 di UAS, 18.30-20.00 di UTS) — label & rentang
# diambil dari data aktual, jadi tidak perlu edit script tiap ganti periode.
CANONICAL_STARTS = {"08.00": 1, "10.45": 2, "14.00": 3, "16.00": 4, "18.30": 5}

SESSION_COLORS = {
    1: ("#A8DADC", "rgba(168,218,220,0.10)"),
    2: ("#FFC1CC", "rgba(255,193,204,0.10)"),
    3: ("#B39CD0", "rgba(179,156,208,0.10)"),
    4: ("#FFD580", "rgba(255,213,128,0.10)"),
    5: ("#e06060", "rgba(224,96,96,0.10)"),
}
# Warna untuk sesi tambahan (jam mulai di luar CANONICAL_STARTS) → sesi 6, 7, ...
EXTRA_COLORS = [
    ("#6BCB77", "rgba(107,203,119,0.10)"),
    ("#F4A261", "rgba(244,162,97,0.10)"),
    ("#7FB3FF", "rgba(127,179,255,0.10)"),
    ("#E9C46A", "rgba(233,196,106,0.10)"),
]

JAM_RE = re.compile(r"^(\d{2})\.(\d{2}) - (\d{2})\.(\d{2}) WIB$")

BULAN_STR_TO_NUM = {
    'januari':'01','februari':'02','maret':'03','april':'04','mei':'05','juni':'06',
    'juli':'07','agustus':'08','september':'09','oktober':'10','november':'11','desember':'12'
}


def is_international(kelas: str) -> bool:
    """True kalau ada token 'INT' di nama kelas (kelas internasional → honor 2×).

    Pakai split per separator agar 'INT' jadi token utuh. Cocok untuk bentuk
    'IF-49-INT', 'INT-48-01', 'CS_50_INT', dst — TIDAK match 'INTRO'/'INTERNAL'.
    """
    if not kelas:
        return False
    parts = re.split(r"[-_\s/]+", str(kelas).strip().upper())
    return "INT" in parts


def normalize_nim(v: str) -> str:
    s = str(v).strip()
    if s.upper() in {"NAN", "NONE", ""}:
        return ""
    try:
        s = str(int(float(s)))
    except (ValueError, OverflowError):
        pass
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return s.upper()


DATE_RANGE_RE = re.compile(r"^(\d{1,2})\s*[-–—]\s*\d{1,2}\s+([A-Za-z]+)\s+(\d{4})$")


def is_date_range(tanggal: str) -> bool:
    """True untuk rentang tanggal seperti '07 - 10 November 2026' (ujian online PJJ)."""
    return bool(DATE_RANGE_RE.match(str(tanggal).strip()))


def to_iso_date(tanggal: str) -> str:
    """Konversi berbagai format tanggal → ISO 'YYYY-MM-DD'.

    Mendukung:
      - '2026-06-22'
      - '2026-06-22 00:00:00'  (format dari Excel/SharePoint)
      - '22/06/2026' atau '22-06-2026'
      - 'Senin, 22 Juni 2026'
      - '07 - 10 November 2026'  (rentang → tanggal mulai)
    """
    s = str(tanggal).strip()
    if not s:
        return ""

    m = DATE_RANGE_RE.match(s)
    if m:
        mm = BULAN_STR_TO_NUM.get(m.group(2).lower(), '00')
        return f"{m.group(3)}-{mm}-{m.group(1).zfill(2)}"

    # 1) Sudah ISO (dengan / tanpa komponen waktu)
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # 2) Format DD/MM/YYYY atau DD-MM-YYYY
    m = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$", s)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"

    # 3) Format Indonesia: 'Senin, 22 Juni 2026' atau '22 Juni 2026'
    try:
        body = s.split(",", 1)[1].strip() if "," in s else s
        parts = body.split()
        d, mname, y = parts[0], parts[1], parts[2]
        mm = BULAN_STR_TO_NUM.get(mname.lower(), '00')
        return f"{y}-{mm}-{d.zfill(2)}"
    except Exception:
        return s


def normalize_jam(jam: str) -> str:
    """Normalisasi format jam: '08.00 – 10.15 WIB', '08:00-10:15', dll → '08.00 - 10.15 WIB'."""
    s = str(jam).strip()
    if not s:
        return ""
    # Ganti em-dash/en-dash dengan hyphen biasa
    s = s.replace("–", "-").replace("—", "-")
    # Ganti pemisah jam-menit ':' menjadi '.'
    s = re.sub(r"(\d{1,2}):(\d{2})", r"\1.\2", s)
    # Pad jam ke 2 digit
    s = re.sub(r"\b(\d)\.(\d{2})\b", r"0\1.\2", s)
    # Normalisasi spasi sekitar '-'
    s = re.sub(r"\s*-\s*", " - ", s)
    # Pastikan diakhiri 'WIB'
    if "WIB" not in s.upper():
        s = s + " WIB"
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"wib$", "WIB", s, flags=re.IGNORECASE)
    return s


def parse_jam(jam_norm: str):
    """'08.00 - 10.15 WIB' → ('08.00', '10.15'). None kalau format tidak dikenal."""
    m = JAM_RE.match(jam_norm)
    if not m:
        return None
    return f"{m.group(1)}.{m.group(2)}", f"{m.group(3)}.{m.group(4)}"


def jam_label(start: str, end: str) -> str:
    return f"{start} – {end} WIB"


def build_sessions(rows):
    """Bangun tabel sesi dari slot jam yang benar-benar ada di data.

    Return (start_to_session, sessions_js, session_time_ranges).
    """
    ends_by_start: dict = {}
    for row in rows:
        parsed = parse_jam(normalize_jam(row.get("Jam", "")))
        if parsed:
            ends_by_start.setdefault(parsed[0], Counter())[parsed[1]] += 1

    start_to_session = {s: n for s, n in CANONICAL_STARTS.items() if s in ends_by_start}
    extra_starts = sorted(s for s in ends_by_start if s not in CANONICAL_STARTS)
    for i, s in enumerate(extra_starts):
        start_to_session[s] = max(CANONICAL_STARTS.values()) + 1 + i

    sessions_js, ranges = {}, {}
    for start, num in sorted(start_to_session.items(), key=lambda kv: kv[1]):
        ends = ends_by_start[start]
        label_end = ends.most_common(1)[0][0]
        max_end = max(ends)  # rentang terlebar → deteksi konflik agenda konservatif
        color, bg = SESSION_COLORS.get(num) or EXTRA_COLORS[(num - 6) % len(EXTRA_COLORS)]
        sessions_js[num] = {
            "label": f"Sesi {num}", "time": jam_label(start, label_end),
            "color": color, "bg": bg,
            "start": start.replace(".", ":"), "end": max_end.replace(".", ":"),
        }
        ranges[num] = [start.replace(".", ":"), max_end.replace(".", ":")]
    return start_to_session, sessions_js, ranges


def clean_name(v: str) -> str:
    s = str(v).strip()
    return s if s and s.lower() not in ("nan", "none", "-", "") else ""


def get_data_commit_time() -> str:
    """Ambil waktu commit terakhir pada folder data/ via git log.

    Return format: 'YYYY-MM-DD HH:MM:SS' dalam UTC. Fallback ke now() bila git log gagal.
    """
    try:
        out = subprocess.check_output(
            ["git", "log", "-1", "--format=%cI", "--", "data/"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        if out:
            iso = out.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso)
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except Exception as ex:
        print(f"  WARN: git log gagal — {ex}")
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ── Read CSV ──────────────────────────────────────────────────────────────────
if not os.path.exists(CSV_PATH):
    print(f"ERROR: {CSV_PATH} tidak ditemukan. Jalankan fetch_jadwal.py dulu.")
    sys.exit(1)

rows = []
with open(CSV_PATH, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append({k.strip(): v for k, v in row.items()})

print(f"Read {len(rows)} rows from {CSV_PATH}")

START_TO_SESSION, SESSIONS_JS, SESSION_TIME_RANGES = build_sessions(rows)
for num, ses in SESSIONS_JS.items():
    print(f"  Sesi {num}: {ses['time']}")


def session_of(jam_norm: str) -> int:
    parsed = parse_jam(jam_norm)
    return START_TO_SESSION.get(parsed[0], 0) if parsed else 0


# ── Build PROCTOR_DB ─────────────────────────────────────────────────────────
proctors = {}   # nim → {name, nim, schedule:[]}
uid      = 1
skipped_slot = 0

# Pass 1: bangun lookup ruangan untuk mendeteksi kelas yang dipecah ke beberapa
# ruangan (split section). Key = (date_iso, jam, course, kelas).
split_lookup: dict = {}
for row in rows:
    tanggal_raw = str(row.get("Tanggal", "")).strip()
    jam_raw     = str(row.get("Jam", "")).strip()
    if not tanggal_raw or not jam_raw:
        continue
    jam_n = normalize_jam(jam_raw)
    if not session_of(jam_n):
        continue
    key = (
        to_iso_date(tanggal_raw),
        jam_n,
        str(row.get("Nama MK", "") or "").strip().upper(),
        str(row.get("Kelas",   "") or "").strip().upper(),
    )
    room = str(row.get("Ruangan", "") or "").strip()
    if not room:
        continue
    if key not in split_lookup:
        split_lookup[key] = []
    if room not in split_lookup[key]:
        split_lookup[key].append(room)

# Urutkan supaya nomor section konsisten di tiap reload
for k in split_lookup:
    split_lookup[k].sort()

split_kelas_count = sum(1 for v in split_lookup.values() if len(v) > 1)
print(f"Split-kelas terdeteksi: {split_kelas_count} kombinasi (date+jam+MK+kelas)")

# Pass 2: bangun PROCTOR_DB sambil isi info section bila kelasnya dipecah

for row in rows:
    tanggal_raw = str(row.get("Tanggal", "")).strip()
    jam_raw     = str(row.get("Jam", "")).strip()
    if not tanggal_raw or not jam_raw:
        continue

    jam = normalize_jam(jam_raw)
    session_num = session_of(jam)
    if session_num == 0:
        skipped_slot += 1
        if skipped_slot <= 5:
            print(f"  WARN: slot tidak dikenal '{jam_raw}' (norm: '{jam}') — dilewati")
        continue

    date_iso = to_iso_date(tanggal_raw)
    course   = str(row.get("Nama MK",    "") or "").strip()
    room     = str(row.get("Ruangan",    "") or "").strip()
    kelas    = str(row.get("Kelas",      "") or "").strip()
    jenis    = str(row.get("Jenis Ujian","") or "").strip()

    # Cek apakah kombinasi (date, jam, MK, kelas) ini dipecah ke beberapa ruangan.
    split_key   = (date_iso, jam, course.upper(), kelas.upper())
    split_rooms = split_lookup.get(split_key, [])
    section_info = None
    if len(split_rooms) > 1 and room in split_rooms:
        section_info = {
            "index": split_rooms.index(room) + 1,
            "total": len(split_rooms),
            "rooms": split_rooms,
        }

    for i in ["1", "2", "3"]:
        nim  = normalize_nim(str(row.get(f"NIM (Pengawas {i})", "") or ""))
        nama = clean_name(str(row.get(f"Nama Lengkap (Pengawas {i})", "") or ""))
        if not nim:
            continue
        if not nama:
            nama = nim

        if nim not in proctors:
            proctors[nim] = {"name": nama, "nim": nim, "schedule": []}
        elif proctors[nim]["name"] == nim and nama != nim:
            proctors[nim]["name"] = nama

        partner_labels = []
        for j in ["1", "2", "3"]:
            if j == i:
                continue
            p_nim  = normalize_nim(str(row.get(f"NIM (Pengawas {j})", "") or ""))
            p_nama = clean_name(str(row.get(f"Nama Lengkap (Pengawas {j})", "") or ""))
            if p_nim:
                partner_labels.append(p_nama if p_nama else p_nim)

        entry = {
            "id":      uid,
            "date":    date_iso,
            "session": session_num,
            "course":  course,
            "code":    room,
            "kelas":   kelas,
            "type":    jenis,
            "role":    f"P{i}",
        }
        if partner_labels:
            entry["partner"] = ", ".join(partner_labels)
        if section_info is not None:
            entry["section"] = section_info
        if is_international(kelas):
            entry["intl"] = True
        # Jam selesai berbeda dari label sesi (mis. sesi 5 berisi 20.00 & 20.30)
        entry_time = jam_label(*parse_jam(jam))
        if entry_time != SESSIONS_JS[session_num]["time"]:
            entry["time"] = entry_time
        if is_date_range(tanggal_raw):
            entry["dateRange"] = tanggal_raw

        proctors[nim]["schedule"].append(entry)
        uid += 1

total_entries = sum(len(p["schedule"]) for p in proctors.values())
print(f"Built PROCTOR_DB: {len(proctors)} pengawas, {total_entries} sesi total"
      + (f" ({skipped_slot} baris dilewati)" if skipped_slot else ""))

# ── Timestamp dari commit folder data/ ───────────────────────────────────────
ts_raw = get_data_commit_time()
print(f"Last data commit (UTC): {ts_raw}")

# ── Generate data.js ─────────────────────────────────────────────────────────
sessions_json    = json.dumps(SESSIONS_JS,        ensure_ascii=False, indent=2)
proctor_db_json  = json.dumps(proctors,           ensure_ascii=False, separators=(",", ":"))
session_ranges_json = json.dumps(SESSION_TIME_RANGES, ensure_ascii=False)

all_dates = sorted(
    e["date"] for p in proctors.values() for e in p["schedule"]
    if re.match(r"^\d{4}-\d{2}-\d{2}$", e["date"])
)
date_min = all_dates[0] if all_dates else ""
date_max = all_dates[-1] if all_dates else ""

# Versi = hash isi data (bukan timestamp) → frontend hanya re-fetch kalau data
# benar-benar berubah, dan file tidak berubah kalau tidak ada perubahan data.
data_version = hashlib.sha1(
    (sessions_json + session_ranges_json + proctor_db_json).encode("utf-8")
).hexdigest()[:12]

os.makedirs("docs", exist_ok=True)

# GitHub repo info untuk frontend bisa fetch commit time terbaru via API (fallback)
GITHUB_REPO = "Fall-Llihc/Visualisasi-Jadwal-Pengawas"

js_content = f"""// data.js — AUTO-GENERATED oleh GitHub Actions. JANGAN EDIT MANUAL.
// Generated: {ts_raw} UTC
(function () {{
  var HARI  = ['Minggu','Senin','Selasa','Rabu','Kamis','Jumat','Sabtu'];
  var BULAN = ['Januari','Februari','Maret','April','Mei','Juni','Juli',
               'Agustus','September','Oktober','November','Desember'];

  window.SESSIONS = {sessions_json};

  // Rentang waktu tiap sesi dalam format "HH:MM" (untuk deteksi konflik agenda)
  window.SESSION_TIME_RANGES = {session_ranges_json};

  // Helper: konversi "HH:MM" → menit total
  function toMinutes(t) {{
    var p = String(t).split(':');
    return parseInt(p[0], 10) * 60 + parseInt(p[1] || '0', 10);
  }}
  window.toMinutes = toMinutes;

  // Helper: cek overlap dua interval waktu (dalam string "HH:MM")
  window.timeOverlap = function (s1, e1, s2, e2) {{
    return toMinutes(s1) < toMinutes(e2) && toMinutes(s2) < toMinutes(e1);
  }};

  // Ambil hanya bagian "YYYY-MM-DD" agar kompatibel dengan beragam format input.
  function isoDateOnly(ds) {{
    if (!ds) return '';
    var m = String(ds).match(/^(\\d{{4}})-(\\d{{2}})-(\\d{{2}})/);
    return m ? (m[1] + '-' + m[2] + '-' + m[3]) : String(ds);
  }}
  window.isoDateOnly = isoDateOnly;

  window.formatDateIndo = function (ds) {{
    var iso = isoDateOnly(ds);
    if (!/^\\d{{4}}-\\d{{2}}-\\d{{2}}$/.test(iso)) return String(ds || '');
    var parts = iso.split('-');
    var y = parseInt(parts[0], 10);
    var mo = parseInt(parts[1], 10) - 1;
    var d = parseInt(parts[2], 10);
    // Pakai UTC agar tidak tergeser oleh timezone browser.
    var date = new Date(Date.UTC(y, mo, d));
    return HARI[date.getUTCDay()] + ', ' + d + ' ' + BULAN[mo] + ' ' + y;
  }};

  // Format "YYYY-MM-DD HH:MM:SS" (UTC) → "<tgl> <bulan> <tahun>, HH:MM WIB"
  // Memakai UTC + offset agar tidak double-shift ke timezone lokal browser.
  window.formatUpdateTime = function (raw) {{
    if (!raw) return '—';
    var s = String(raw).trim().replace(' UTC', '').replace(' ', 'T');
    if (!/Z|[+-]\\d{{2}}:?\\d{{2}}$/.test(s)) s += 'Z';
    var d = new Date(s);
    if (isNaN(d.getTime())) return String(raw);
    // Tambah offset WIB (UTC+7) lalu pakai getUTC* agar konsisten lintas timezone.
    var wib = new Date(d.getTime() + 7 * 3600000);
    var hh = String(wib.getUTCHours()).padStart(2, '0');
    var mm = String(wib.getUTCMinutes()).padStart(2, '0');
    return wib.getUTCDate() + ' ' + BULAN[wib.getUTCMonth()] + ' ' + wib.getUTCFullYear()
         + ', ' + hh + ':' + mm + ' WIB';
  }};

  window.HONOR_PER_SESSION = 30000;
  // Multiplier honor untuk kelas internasional (kelas dgn token 'INT', mis. IF-49-INT).
  window.HONOR_INT_MULTIPLIER = 2;
  window.honorOf = function (entry) {{
    return window.HONOR_PER_SESSION * (entry && entry.intl ? window.HONOR_INT_MULTIPLIER : 1);
  }};

  window.PROCTOR_DB = {proctor_db_json};

  // Hitung jumlah sesi konflik (multiple jadwal pada slot yg sama)
  window.countConflicts = function (schedule) {{
    var map = {{}}; var c = 0;
    schedule.forEach(function (s) {{
      var k = isoDateOnly(s.date) + '-' + s.session;
      if (!map[k]) map[k] = [];
      map[k].push(s);
    }});
    Object.values(map).forEach(function (v) {{ if (v.length > 1) c++; }});
    return c;
  }};

  window.isSessionConflict = function (schedule, date, session) {{
    var iso = isoDateOnly(date);
    return schedule.filter(function (s) {{
      return isoDateOnly(s.date) === iso && s.session === session;
    }}).length > 1;
  }};

  // Cek apakah agenda eksternal (date+start+end) bertabrakan dengan sesi pengawasan
  // pada hari yang sama. Mengembalikan array sesi-num yang konflik.
  window.findAgendaSessionConflicts = function (schedule, agenda) {{
    var iso = isoDateOnly(agenda.date);
    var conflicts = [];
    var seen = {{}};
    schedule.forEach(function (s) {{
      if (isoDateOnly(s.date) !== iso) return;
      var range = window.SESSION_TIME_RANGES[s.session];
      if (!range) return;
      if (window.timeOverlap(agenda.start, agenda.end, range[0], range[1])) {{
        if (!seen[s.session]) {{
          conflicts.push(s.session);
          seen[s.session] = 1;
        }}
      }}
    }});
    return conflicts;
  }};

  // Hitung breakdown honor dengan memperhitungkan konflik:
  //  - Internal conflict: 2+ jadwal di slot (date,session) yang sama → pengawas
  //    cuma bisa hadir 1, sisanya hangus (lost = N - 1). Bila honor entry
  //    berbeda (mis. ada kelas INT), pilih entry dgn honor TERTINGGI sebagai
  //    yang dihadiri (asumsi rasional → kelas yg lebih besar honornya).
  //  - Agenda eksternal yg overlap waktu dengan suatu slot → pengawas tidak bisa
  //    hadir di slot itu sama sekali, jadi semua N entry slot itu hangus.
  window.computeHonorBreakdown = function (schedule, agendas) {{
    var slots = {{}};
    schedule.forEach(function (s) {{
      var k = isoDateOnly(s.date) + '-' + s.session;
      if (!slots[k]) slots[k] = {{ date: isoDateOnly(s.date), session: s.session, entries: [] }};
      slots[k].entries.push(s);
    }});

    var attended      = 0;
    var lostInternal  = 0;
    var lostAgenda    = 0;
    var conflictSlots = 0;
    var honorGross    = 0;
    var honorNet      = 0;
    var honorLost     = 0;
    var intlAttended  = 0;
    var intlTotal     = 0;
    var agendaList = Array.isArray(agendas) ? agendas : [];

    schedule.forEach(function (s) {{
      honorGross += window.honorOf(s);
      if (s.intl) intlTotal += 1;
    }});

    Object.keys(slots).forEach(function (k) {{
      var slot = slots[k];
      var entries = slot.entries;
      var n = entries.length;

      var hasAgendaConflict = false;
      for (var i = 0; i < agendaList.length; i++) {{
        var ag = agendaList[i];
        if (isoDateOnly(ag.date) !== slot.date) continue;
        var range = window.SESSION_TIME_RANGES[slot.session];
        if (!range) continue;
        if (window.timeOverlap(ag.start, ag.end, range[0], range[1])) {{
          hasAgendaConflict = true;
          break;
        }}
      }}

      if (hasAgendaConflict) {{
        lostAgenda += n;
        entries.forEach(function (e) {{ honorLost += window.honorOf(e); }});
      }} else if (n > 1) {{
        // Pilih entry dgn honor tertinggi sebagai yang dihadiri (kelas INT > regular).
        var sorted = entries.slice().sort(function (a, b) {{
          return window.honorOf(b) - window.honorOf(a);
        }});
        attended      += 1;
        honorNet      += window.honorOf(sorted[0]);
        if (sorted[0].intl) intlAttended += 1;
        for (var j = 1; j < sorted.length; j++) {{
          honorLost += window.honorOf(sorted[j]);
        }}
        lostInternal  += n - 1;
        conflictSlots += 1;
      }} else {{
        attended += 1;
        honorNet += window.honorOf(entries[0]);
        if (entries[0].intl) intlAttended += 1;
      }}
    }});

    return {{
      total:           schedule.length,
      attended:        attended,
      lostInternal:    lostInternal,
      lostAgenda:      lostAgenda,
      lostTotal:       lostInternal + lostAgenda,
      conflictSlots:   conflictSlots,
      honorGross:      honorGross,
      honorNet:        honorNet,
      honorLost:       honorLost,
      intlAttended:    intlAttended,
      intlTotal:       intlTotal,
    }};
  }};

  window.LAST_UPDATE_RAW   = '{ts_raw}';
  window.GITHUB_REPO       = '{GITHUB_REPO}';
  window.DATA_ROWS         = {len(rows)};
  window.DATA_PROCTORS     = {len(proctors)};
  window.DATA_SESSIONS     = {total_entries};
  window.DATA_VERSION      = '{data_version}';
  window.DATA_DATE_MIN     = '{date_min}';
  window.DATA_DATE_MAX     = '{date_max}';

  // Live update: poll version.json (kecil); kalau versinya beda, ambil data.json
  // lalu timpa global. cb(payload) hanya dipanggil kalau data benar-benar berubah.
  window.fetchLatestData = function (cb) {{
    var bust = '?t=' + Date.now();
    fetch('version.json' + bust, {{ cache: 'no-store' }}).then(function (r) {{
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }}).then(function (v) {{
      if (!v || !v.version || v.version === window.DATA_VERSION) return null;
      return fetch('data.json' + bust, {{ cache: 'no-store' }}).then(function (r) {{
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      }});
    }}).then(function (d) {{
      if (!d || !d.proctors) return;
      window.SESSIONS            = d.sessions;
      window.SESSION_TIME_RANGES = d.sessionRanges;
      window.PROCTOR_DB          = d.proctors;
      window.LAST_UPDATE_RAW     = d.lastUpdate;
      window.DATA_ROWS           = d.rows;
      window.DATA_PROCTORS       = d.proctorCount;
      window.DATA_SESSIONS       = d.sessionCount;
      window.DATA_VERSION        = d.version;
      window.DATA_DATE_MIN       = d.dateMin;
      window.DATA_DATE_MAX       = d.dateMax;
      cb(d);
    }}).catch(function (err) {{
      console.warn('fetchLatestData gagal:', err);
    }});
  }};

  // Fetch waktu commit terakhir folder /data via GitHub API → akurat ke detik.
  // Fallback: pakai LAST_UPDATE_RAW kalau API gagal / offline.
  window.fetchLatestCommitTime = function (cb) {{
    try {{
      var url = 'https://api.github.com/repos/' + window.GITHUB_REPO + '/commits?path=data&per_page=1';
      fetch(url).then(function (r) {{
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      }}).then(function (arr) {{
        if (Array.isArray(arr) && arr.length && arr[0].commit && arr[0].commit.committer) {{
          var iso = arr[0].commit.committer.date; // sudah ISO UTC
          var d = new Date(iso);
          var pad = function (n) {{ return String(n).padStart(2, '0'); }};
          var raw = d.getUTCFullYear() + '-' + pad(d.getUTCMonth()+1) + '-' + pad(d.getUTCDate())
                  + ' ' + pad(d.getUTCHours()) + ':' + pad(d.getUTCMinutes()) + ':' + pad(d.getUTCSeconds());
          cb(raw);
        }}
      }}).catch(function (err) {{
        console.warn('fetchLatestCommitTime gagal:', err);
      }});
    }} catch (e) {{
      console.warn('fetchLatestCommitTime error:', e);
    }}
  }};
}})();
"""

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(js_content)

payload = {
    "version":       data_version,
    "lastUpdate":    ts_raw,
    "rows":          len(rows),
    "proctorCount":  len(proctors),
    "sessionCount":  total_entries,
    "dateMin":       date_min,
    "dateMax":       date_max,
    "sessions":      SESSIONS_JS,
    "sessionRanges": SESSION_TIME_RANGES,
    "proctors":      proctors,
}
with open(OUT_JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
with open(OUT_VERSION_PATH, "w", encoding="utf-8") as f:
    json.dump({"version": data_version, "lastUpdate": ts_raw}, f)

print(f"✓ Generated {OUT_PATH} ({len(js_content):,} bytes)")
print(f"  LAST_UPDATE_RAW = {ts_raw}")
print(f"  DATA_ROWS = {len(rows)}, PROCTORS = {len(proctors)}, SESSIONS = {total_entries}")
print(f"  DATA_VERSION = {data_version} → {OUT_JSON_PATH}, {OUT_VERSION_PATH}")
