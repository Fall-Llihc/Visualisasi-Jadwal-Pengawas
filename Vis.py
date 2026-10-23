"""
Vis.py — NgawasChill Admin Console
Versi Streamlit ini hanya untuk admin: trigger sync, atur interval auto-refresh,
preview data, dan reset cache. Versi user (lookup NIM + agenda) ada di
GitHub Pages (folder docs/).
"""

import streamlit as st
import pandas as pd
import html as html_lib
import io
import requests
import time
from datetime import datetime, timezone, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NgawasChill Admin — Jadwal Pengawas Ujian FIF",
    page_icon="🛠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800&display=swap');

:root {
  --bg:#2C2C2C; --bg-sb:#242424; --bg-card:#353535; --bg-card-h:#3e3e3e;
  --bg-input:#333; --text:#E4E4E4; --text2:#aaa; --text3:#777;
  --cyan:#A8DADC; --pink:#FFC1CC; --lav:#B39CD0;
  --border:#444; --danger:#e06060; --success:#6BCB77;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] {
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
  background: var(--bg) !important; color: var(--text) !important;
}
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

[data-testid="stAppViewContainer"] { background: var(--bg) !important; }
[data-testid="stSidebar"] { background: var(--bg-sb) !important; border-right: 1px solid var(--border) !important; }
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }
[data-testid="stHeader"] { display: none !important; }
.stMainBlockContainer { padding: 36px 40px 60px !important; max-width: 100% !important; }
#MainMenu, footer, header { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
.stDeployButton { display: none !important; }

/* Sidebar brand */
.sb-brand { padding: 24px 20px 16px; border-bottom: 1px solid var(--border); }
.sb-logo { font-size: 22px; font-weight: 800; letter-spacing: -.5px; color: var(--lav); margin: 0; }
.sb-subtitle { font-size: 12px; color: var(--text2); margin-top: 3px; font-weight: 500; }

.sb-section { padding: 14px 20px; border-bottom: 1px solid rgba(68,68,68,.5); }
.sb-section-title {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .8px; color: var(--text3); margin-bottom: 10px;
}
.sb-hint { font-size: 11px; color: var(--text3); line-height: 1.45; margin-bottom: 10px; }

[data-testid="stSidebar"] .stTextInput > div > div > input,
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stNumberInput > div > div > input {
  background: var(--bg-input) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text) !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 13px !important;
}
[data-testid="stSidebar"] .stButton > button {
  width: 100%; border-radius: 8px !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 13px !important; font-weight: 600 !important;
  border: none !important; transition: filter .15s !important;
  padding: 10px 14px !important;
}

/* Sidebar footer */
.sb-footer {
  padding: 14px 20px; border-top: 1px solid var(--border);
  display: flex; gap: 10px; align-items: flex-start;
  background: rgba(179,156,208,.05);
}
.sb-update-dot {
  width: 8px; height: 8px; border-radius: 50%; background: var(--success);
  margin-top: 5px; flex-shrink: 0; box-shadow: 0 0 6px rgba(107,203,119,.4);
}
.sb-update-label { font-size: 10px; color: var(--text3); text-transform: uppercase; letter-spacing: .5px; font-weight: 600; }
.sb-update-time { font-size: 13px; color: var(--text); font-weight: 700; margin-top: 2px; }
.sb-update-rows { font-size: 10px; color: var(--text3); margin-top: 2px; }

/* Main view */
.mv-sup {
  font-size: 12px; color: var(--lav); font-weight: 600;
  text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px;
}
.mv-name { font-size: 30px; font-weight: 800; letter-spacing: -.5px; line-height: 1.2; margin-bottom: 10px; }
.mv-badges { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 28px; }
.mv-badge {
  background: rgba(179,156,208,.15); color: var(--lav);
  font-size: 13px; font-weight: 600; padding: 4px 12px; border-radius: 20px;
}
.mv-meta { font-size: 13px; color: var(--text2); }

.stats-row { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 24px; }
.stat-box { background: var(--bg-card); border-radius: 12px; padding: 18px 16px; text-align: center; }
.stat-value { font-size: 22px; font-weight: 800; line-height: 1.2; }
.stat-label { font-size: 11px; color: var(--text3); margin-top: 4px; text-transform: uppercase; letter-spacing: .4px; font-weight: 600; }

.section-h {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .8px; color: var(--lav);
  border-left: 3px solid var(--lav); padding-left: 10px;
  margin: 28px 0 14px;
}

.info-card {
  background: var(--bg-card); border-radius: 12px; padding: 18px 22px; margin-bottom: 14px;
}
.info-card h3 { font-size: 14px; font-weight: 700; margin-bottom: 10px; color: var(--text); }
.info-row { display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px; }
.info-row + .info-row { border-top: 1px solid rgba(68,68,68,.5); }
.info-key { color: var(--text3); }
.info-val { color: var(--text); font-weight: 600; }
.info-val--ok { color: var(--success); }
.info-val--err { color: var(--danger); }

.empty-state {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; min-height: 60vh; text-align: center; color: var(--text3);
}
.empty-state h2 { font-size: 22px; color: var(--text2); font-weight: 700; margin: 20px 0 8px; }
.empty-state p { font-size: 14px; max-width: 360px; line-height: 1.5; }

.sync-msg-ok { font-size: 11px; color: var(--success); margin-top: 8px; text-align: center; padding: 6px; background: rgba(107,203,119,.08); border-radius: 6px; }
.sync-msg-err { font-size: 11px; color: var(--danger); margin-top: 8px; text-align: center; padding: 6px; background: rgba(224,96,96,.08); border-radius: 6px; }

.sb-confirm { background: rgba(224,96,96,.08); border: 1px solid rgba(224,96,96,.2); border-radius: 8px; padding: 12px; margin-top: 8px; }
.sb-confirm p { font-size: 12px; color: var(--danger); margin-bottom: 8px; font-weight: 600; }

@media(max-width:860px) {
  .stMainBlockContainer { padding: 20px !important; }
  .stats-row { grid-template-columns: repeat(2,1fr) !important; }
  .mv-name { font-size: 22px !important; }
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
GITHUB_REPO         = "Fall-Llihc/Visualisasi-Jadwal-Pengawas"
RAW_DATA_URL        = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/data/jadwal.csv"
RAW_TS_URL          = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/data/last_updated.txt"
GITHUB_API_DISPATCH = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/sync_jadwal.yml/dispatches"
GITHUB_API_COMMITS  = f"https://api.github.com/repos/{GITHUB_REPO}/commits"

# Link SharePoint disimpan di Streamlit Secrets (SHAREPOINT_URL), sama seperti
# GitHub Secrets di workflow — file sumber berisi data pribadi pengawas, jadi
# link-nya tidak di-hardcode di repo publik.
def _get_sharepoint_url() -> str:
    try:
        url = str(st.secrets.get("SHAREPOINT_URL", "")).strip()
    except Exception:
        url = ""
    if url and "download=1" not in url:
        url += ("&" if "?" in url else "?") + "download=1"
    return url


SHAREPOINT_URL = _get_sharepoint_url()

DEFAULT_INTERVAL_MIN = 60

BULAN_ID = {
    1:'Januari', 2:'Februari', 3:'Maret', 4:'April', 5:'Mei', 6:'Juni',
    7:'Juli', 8:'Agustus', 9:'September', 10:'Oktober', 11:'November', 12:'Desember'
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def e(s):
    return html_lib.escape(str(s))


def normalize_nim(value) -> str:
    s = str(value).strip()
    if s.upper() in {"NAN", "NONE", ""}:
        return ""
    try:
        s = str(int(float(s)))
    except (ValueError, OverflowError):
        pass
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return s.upper()


def format_utc_to_wib(raw: str) -> str:
    """'2026-06-07 15:30:52 [UTC]' → '7 Juni 2026, 22:30 WIB'.

    Memakai naive datetime + timedelta(7h) — tidak ada efek timezone lokal
    server, jadi tampilan WIB selalu konsisten.
    """
    if not raw:
        return "—"
    try:
        s = str(raw).replace(" UTC", "").strip()
        # Dukung ISO 8601 dengan 'T' atau 'Z'
        s = s.replace("T", " ").replace("Z", "").strip()
        # Buang offset timezone kalau ada
        if "+" in s[10:] or "-" in s[10:]:
            for sep in ("+", "-"):
                idx = s.find(sep, 10)
                if idx > 0:
                    s = s[:idx]
                    break
        dt = datetime.strptime(s.strip(), "%Y-%m-%d %H:%M:%S")
        dt_wib = dt + timedelta(hours=7)
        return f"{dt_wib.day} {BULAN_ID[dt_wib.month]} {dt_wib.year}, {dt_wib.strftime('%H:%M')} WIB"
    except Exception:
        return str(raw)


@st.cache_data(ttl=120, show_spinner=False)
def fetch_data_commit_info(_dummy: int = 0):
    """Ambil commit terbaru pada folder /data via GitHub API.

    Return dict {sha, date_utc, message, author, html_url} atau None.
    """
    try:
        r = requests.get(
            GITHUB_API_COMMITS,
            params={"path": "data", "per_page": 1},
            timeout=15,
            headers={"Accept": "application/vnd.github+json"},
        )
        if r.status_code == 200:
            arr = r.json()
            if isinstance(arr, list) and arr:
                c = arr[0]
                committer = (c.get("commit") or {}).get("committer") or {}
                # ISO date → '2026-06-07 15:30:52'
                iso = committer.get("date", "")  # e.g. 2026-06-07T15:30:52Z
                date_str = iso.replace("T", " ").replace("Z", "") if iso else ""
                return {
                    "sha":       (c.get("sha") or "")[:7],
                    "date_utc":  date_str,
                    "message":   (c.get("commit") or {}).get("message", "")[:80],
                    "author":    committer.get("name", ""),
                    "html_url":  c.get("html_url", ""),
                }
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# DATA — download + parse (auto-detect header row → tahan perubahan layout)
# ─────────────────────────────────────────────────────────────────────────────
_HEADER_TOKENS = ("tanggal", "jam")
_MAX_HEADER_SCAN_ROWS = 50


def _row_is_header(row_values) -> bool:
    flat = " | ".join(str(v).strip().lower() for v in row_values if v is not None)
    return all(tok in flat for tok in _HEADER_TOKENS)


def _detect_header_row(df_no_header: pd.DataFrame):
    limit = min(len(df_no_header), _MAX_HEADER_SCAN_ROWS)
    for i in range(limit):
        if _row_is_header(df_no_header.iloc[i].tolist()):
            return i
    return None


def _robust_parse(content_bytes: bytes):
    """Auto-detect header row di XLSX/CSV — robust terhadap perubahan layout sumber."""
    # XLSX
    if content_bytes[:4] == b'PK\x03\x04':
        try:
            xl = pd.ExcelFile(io.BytesIO(content_bytes), engine="openpyxl")
            for sheet in xl.sheet_names:
                try:
                    raw = pd.read_excel(
                        io.BytesIO(content_bytes), sheet_name=sheet,
                        header=None, dtype=str, engine="openpyxl",
                    )
                except Exception:
                    continue
                hdr = _detect_header_row(raw)
                if hdr is None:
                    continue
                df = pd.read_excel(
                    io.BytesIO(content_bytes), sheet_name=sheet,
                    header=hdr, dtype=str, engine="openpyxl",
                )
                df.columns = [str(c).strip() for c in df.columns]
                df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
                df = df.loc[:, df.columns != ""]
                if "Tanggal" in df.columns and len(df) > 0:
                    return df, None
        except Exception as ex:
            return None, f"Gagal parse XLSX: {ex}"
        return None, "Header 'Tanggal'+'Jam' tidak ditemukan di XLSX."

    # CSV — coba beberapa encoding & separator
    last_err = "unknown"
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = content_bytes.decode(enc, errors="replace")
        except Exception as ex:
            last_err = str(ex)
            continue
        for sep in (";", ",", "\t"):
            try:
                raw = pd.read_csv(
                    io.StringIO(text), sep=sep, header=None, dtype=str,
                    engine="python", on_bad_lines="skip",
                )
            except Exception as ex:
                last_err = str(ex)
                continue
            if raw.empty or raw.shape[1] < 3:
                continue
            hdr = _detect_header_row(raw)
            if hdr is None:
                continue
            try:
                df = pd.read_csv(
                    io.StringIO(text), sep=sep, skiprows=hdr, dtype=str,
                    engine="python", on_bad_lines="skip",
                )
            except Exception as ex:
                last_err = str(ex)
                continue
            df.columns = [str(c).strip() for c in df.columns]
            df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
            df = df.loc[:, df.columns != ""]
            if "Tanggal" in df.columns and len(df) > 0:
                return df, None
    return None, f"Gagal parse file: {last_err}"


def _process_df(df: pd.DataFrame):
    df = df.copy()
    df.columns = df.columns.str.strip()
    df = df[df["Tanggal"].notna()].copy()
    df = df[df["Tanggal"].astype(str).str.strip() != ""].copy()
    df = df[~df["Tanggal"].astype(str).str.strip().str.startswith("#")].copy()
    df["Tanggal"] = df["Tanggal"].astype(str).str.strip()
    df["Jam"]     = df["Jam"].astype(str).str.strip()
    for i in ["1", "2", "3"]:
        col = f"NIM (Pengawas {i})"
        df[col] = df[col].apply(normalize_nim) if col in df.columns else ""
    for i in ["1", "2", "3"]:
        col = f"Nama Lengkap (Pengawas {i})"
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace({"nan": "", "None": "", "NaN": ""})
        else:
            df[col] = ""
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    return df, None


@st.cache_data(ttl=60, show_spinner=False)
def _load_from_github(_dummy: int = 0):
    try:
        r = requests.get(RAW_DATA_URL, timeout=15, headers={"Cache-Control": "no-cache"})
        if r.status_code == 404:
            return None, "File data/jadwal.csv belum ada di repo — jalankan GitHub Actions dulu."
        if r.status_code != 200:
            return None, f"GitHub: HTTP {r.status_code}"
        df = pd.read_csv(
            io.StringIO(r.content.decode("utf-8-sig", errors="replace")),
            dtype=str, engine="python", on_bad_lines="skip",
        )
        if "Tanggal" not in df.columns:
            return None, "Kolom Tanggal tidak ditemukan."
        return df, None
    except Exception as ex:
        return None, f"Gagal baca GitHub: {ex}"


@st.cache_data(ttl=60, show_spinner=False)
def _get_last_updated_txt(_dummy: int = 0) -> str:
    try:
        r = requests.get(RAW_TS_URL, timeout=10, headers={"Cache-Control": "no-cache"})
        if r.status_code == 200:
            return r.text.strip()
    except Exception:
        pass
    return ""


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_from_sharepoint(_dummy: int = 0):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/octet-stream,*/*;q=0.8",
        "Accept-Encoding": "identity",
    }
    if not SHAREPOINT_URL:
        return None, "SHAREPOINT_URL belum diset di Streamlit Secrets."
    try:
        resp = requests.get(SHAREPOINT_URL, headers=headers, timeout=30, allow_redirects=True)
    except Exception as ex:
        return None, f"Koneksi gagal: {ex}"
    ct = resp.headers.get("Content-Type", "")
    sz = len(resp.content)
    if resp.status_code == 403:
        body = resp.content.decode(errors="replace")
        if "allowlist" in body.lower():
            return None, "403 IP diblokir SharePoint tenant."
        return None, "403 Forbidden."
    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code}."
    if "html" in ct.lower():
        if "login.microsoftonline.com" in resp.url:
            return None, "SharePoint minta login — set link sharing ke 'Anyone'."
        return None, "SharePoint mengembalikan HTML."
    if sz < 500:
        return None, f"Response terlalu kecil ({sz} B)."
    df, err = _robust_parse(resp.content)
    if err:
        return None, err
    return _process_df(df)


def trigger_github_actions(gh_token: str):
    if not gh_token.strip():
        return False, "GitHub Token (GH_PAT) tidak diset di Secrets."
    try:
        r = requests.post(
            GITHUB_API_DISPATCH,
            headers={
                "Authorization": f"Bearer {gh_token.strip()}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={"ref": "main", "inputs": {"reason": "Manual trigger dari NgawasChill Admin"}},
            timeout=15,
        )
        if r.status_code == 204:
            return True, "GitHub Actions berhasil di-trigger! Tunggu ~30 detik lalu klik Pull Data."
        return False, f"GitHub API: HTTP {r.status_code} — {r.text[:150]}"
    except Exception as ex:
        return False, f"Gagal trigger: {ex}"


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULTS = {
    "df":              None,
    "data_error":      None,
    "fetch_count":     0,
    "admin_logged_in": False,
    "admin_msg":       "",
    "admin_msg_ok":    True,
    "interval_min":    DEFAULT_INTERVAL_MIN,
    "interval_input":  DEFAULT_INTERVAL_MIN,
    "last_auto_fetch": 0.0,
    "last_updated_str": "",
    "show_reset_confirm": False,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Safety net: pastikan key auto_update_enabled selalu ada — bila session state
# berasal dari deploy versi lama, init loop di atas mungkin tidak meng-cover
# key baru ini sehingga `st.session_state.auto_update_enabled` bisa AttributeError.
st.session_state.setdefault("auto_update_enabled", True)

# Auto-refresh check (non-blocking) — hanya jalan kalau toggle Auto-Update aktif
_now = time.time()
if (st.session_state.get("auto_update_enabled", True) and
    st.session_state.df is not None and
    (_now - st.session_state.last_auto_fetch) >= st.session_state.interval_min * 60):
    _load_from_github.clear()
    _get_last_updated_txt.clear()
    fetch_data_commit_info.clear()
    df_auto, err_auto = _load_from_github(st.session_state.fetch_count + 1)
    if not err_auto:
        df_auto, _ = _process_df(df_auto)
        st.session_state.df = df_auto
        st.session_state.fetch_count += 1
    st.session_state.last_auto_fetch = _now


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — admin login + controls
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    # Brand
    st.markdown(
        "<div class='sb-brand'>"
        "<h1 class='sb-logo'>NgawasChill</h1>"
        "<p class='sb-subtitle'>🛠 Admin Console</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    if not st.session_state.admin_logged_in:
        st.markdown("<div class='sb-section' style='padding-top:32px;text-align:center;'>", unsafe_allow_html=True)
        st.markdown("<p class='sb-section-title' style='text-align:center;'>🔐 Login Admin</p>", unsafe_allow_html=True)
        pwd = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
        if st.button("🔐 Login", use_container_width=True):
            try:
                correct = st.secrets.get("ADMIN_PASSWORD", "admin123")
            except Exception:
                correct = "admin123"
            if pwd == correct:
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("Password salah.")
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.markdown(
            "<div style='padding:10px 20px;font-size:11px;color:#6BCB77;'>✅ Login sebagai Admin</div>",
            unsafe_allow_html=True,
        )

        # ── Manual Sync ───────────────────────────────────────────────────
        st.markdown("<div class='sb-section'>", unsafe_allow_html=True)
        st.markdown("<p class='sb-section-title'>⚡ Manual Sync</p>", unsafe_allow_html=True)
        st.markdown("<p class='sb-hint'>Trigger GitHub Actions untuk ambil data terbaru dari SharePoint, lalu pull ke Streamlit.</p>", unsafe_allow_html=True)

        if st.button("🚀 Trigger GitHub Actions", use_container_width=True, type="primary"):
            try:
                gh_token = st.secrets.get("GH_PAT", "")
            except Exception:
                gh_token = ""
            ok, msg = trigger_github_actions(gh_token)
            st.session_state.admin_msg = msg
            st.session_state.admin_msg_ok = ok
            if ok:
                _load_from_github.clear()
                _get_last_updated_txt.clear()
                fetch_data_commit_info.clear()

        if st.button("🔄 Pull Data dari GitHub", use_container_width=True):
            _load_from_github.clear()
            _get_last_updated_txt.clear()
            fetch_data_commit_info.clear()
            st.session_state.df = None
            st.session_state.data_error = None
            st.session_state.fetch_count += 1
            st.session_state.last_auto_fetch = time.time()
            st.rerun()

        if st.button("🌐 Fetch dari SharePoint", use_container_width=True):
            _fetch_from_sharepoint.clear()
            with st.spinner("Mengambil dari SharePoint…"):
                df_sp, err_sp = _fetch_from_sharepoint(st.session_state.fetch_count + 1)
            if err_sp:
                st.session_state.admin_msg = err_sp
                st.session_state.admin_msg_ok = False
            else:
                st.session_state.df = df_sp
                st.session_state.data_error = None
                st.session_state.admin_msg = f"Berhasil ambil {len(df_sp)} baris dari SharePoint."
                st.session_state.admin_msg_ok = True
                st.session_state.fetch_count += 1
                st.session_state.last_auto_fetch = time.time()

        if st.session_state.admin_msg:
            cls = "sync-msg-ok" if st.session_state.admin_msg_ok else "sync-msg-err"
            icon = "✅" if st.session_state.admin_msg_ok else "❌"
            st.markdown(
                f"<div class='{cls}'>{icon} {e(st.session_state.admin_msg)}</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Auto-Update toggle ───────────────────────────────────────────
        st.markdown("<div class='sb-section'>", unsafe_allow_html=True)
        st.markdown("<p class='sb-section-title'>🔄 Auto-Update</p>", unsafe_allow_html=True)
        st.markdown(
            "<p class='sb-hint'>Aktifkan untuk otomatis pull data dari GitHub setiap "
            "<b>interval</b> di bawah. Matikan kalau tidak ingin selalu auto-pull "
            "(termasuk auto-trigger ke GitHub Actions tetap manual).</p>",
            unsafe_allow_html=True,
        )
        prev_auto = st.session_state.get("auto_update_enabled", True)
        st.session_state.auto_update_enabled = st.toggle(
            "Auto-update aktif",
            value=prev_auto,
            key="auto_update_toggle",
        )
        # Reset timer kalau baru saja diubah dari off → on agar tidak langsung fetch
        if (not prev_auto) and st.session_state.auto_update_enabled:
            st.session_state.last_auto_fetch = time.time()

        if st.session_state.get("auto_update_enabled", True):
            st.markdown(
                "<p style='font-size:11px;color:#6BCB77;text-align:center;margin-top:4px;'>"
                "🟢 Auto-pull aktif — refresh tiap "
                f"<b>{st.session_state.interval_min} mnt</b></p>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<p style='font-size:11px;color:#e06060;text-align:center;margin-top:4px;'>"
                "⚪ Auto-pull <b>nonaktif</b> — pull data hanya saat tombol di atas ditekan</p>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Interval ──────────────────────────────────────────────────────
        st.markdown("<div class='sb-section'>", unsafe_allow_html=True)
        st.markdown("<p class='sb-section-title'>⏱ Interval Auto-Refresh</p>", unsafe_allow_html=True)
        st.markdown(
            "<p class='sb-hint'>Atur seberapa sering Streamlit memperbarui data (minimum 5 menit).</p>",
            unsafe_allow_html=True,
        )

        c_minus, c_val, c_plus = st.columns([1, 2, 1])
        with c_minus:
            if st.button("−", use_container_width=True, key="int_minus"):
                st.session_state.interval_input = max(5, st.session_state.interval_input - 5)
        with c_val:
            st.markdown(
                f"<div style='text-align:center;font-size:18px;font-weight:700;color:#E4E4E4;padding:8px 0;'>"
                f"{st.session_state.interval_input} mnt</div>",
                unsafe_allow_html=True,
            )
        with c_plus:
            if st.button("+", use_container_width=True, key="int_plus"):
                st.session_state.interval_input += 5

        st.markdown(
            f"<p style='font-size:10px;color:#777;text-align:center;margin:4px 0;'>"
            f"Aktif: <b style='color:#A8DADC'>{st.session_state.interval_min} mnt</b></p>",
            unsafe_allow_html=True,
        )

        ca, cb = st.columns(2)
        with ca:
            if st.button("💾 Simpan", use_container_width=True):
                st.session_state.interval_min = st.session_state.interval_input
                st.success(f"✅ {st.session_state.interval_input} mnt")
        with cb:
            preset = st.selectbox(
                "Preset", ["15 mnt", "30 mnt", "1 jam", "2 jam", "6 jam"],
                label_visibility="collapsed",
            )
            if st.button("⚡ Pakai", use_container_width=True):
                pmap = {"15 mnt": 15, "30 mnt": 30, "1 jam": 60, "2 jam": 120, "6 jam": 360}
                st.session_state.interval_min   = pmap[preset]
                st.session_state.interval_input = pmap[preset]
                st.success(f"✅ {preset}")
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Reset ─────────────────────────────────────────────────────────
        st.markdown("<div class='sb-section'>", unsafe_allow_html=True)
        st.markdown("<p class='sb-section-title'>🗑 Reset Cache</p>", unsafe_allow_html=True)
        st.markdown("<p class='sb-hint'>Hapus seluruh cache Streamlit (akan re-fetch saat halaman dimuat ulang).</p>", unsafe_allow_html=True)
        if not st.session_state.show_reset_confirm:
            if st.button("🗑 Reset Cache", use_container_width=True):
                st.session_state.show_reset_confirm = True
                st.rerun()
        else:
            st.markdown(
                "<div class='sb-confirm'><p>Yakin ingin reset cache?</p></div>",
                unsafe_allow_html=True,
            )
            cr1, cr2 = st.columns(2)
            with cr1:
                if st.button("Ya, Reset", use_container_width=True):
                    for k in ["df", "data_error", "last_updated_str"]:
                        st.session_state[k] = _DEFAULTS.get(k)
                    _load_from_github.clear()
                    _fetch_from_sharepoint.clear()
                    _get_last_updated_txt.clear()
                    fetch_data_commit_info.clear()
                    st.session_state.show_reset_confirm = False
                    st.rerun()
            with cr2:
                if st.button("Batal", use_container_width=True):
                    st.session_state.show_reset_confirm = False
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Logout ────────────────────────────────────────────────────────
        st.markdown("<div style='padding:14px 20px;'>", unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.admin_logged_in = False
            st.session_state.admin_msg = ""
            st.session_state.show_reset_confirm = False
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Footer — last updated ─────────────────────────────────────────────
    commit_info = fetch_data_commit_info(st.session_state.fetch_count)
    if commit_info and commit_info.get("date_utc"):
        ts_display = format_utc_to_wib(commit_info["date_utc"])
    else:
        # Fallback: file last_updated.txt yang di-commit
        ts_raw = _get_last_updated_txt(st.session_state.fetch_count)
        ts_display = format_utc_to_wib(ts_raw) if ts_raw else "—"

    n_rows = len(st.session_state.df) if st.session_state.df is not None else 0
    st.markdown(
        f"<div class='sb-footer'>"
        f"<div class='sb-update-dot'></div>"
        f"<div>"
        f"<p class='sb-update-label'>Commit data terakhir</p>"
        f"<p class='sb-update-time'>{e(ts_display)}</p>"
        f"<p class='sb-update-rows'>{n_rows} baris data</p>"
        f"</div></div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.admin_logged_in:
    st.markdown(
        "<div class='empty-state'>"
        "<svg width='52' height='52' viewBox='0 0 24 24' fill='none' stroke='#444' stroke-width='1.4' stroke-linecap='round'>"
        "<rect x='3' y='11' width='18' height='11' rx='2'/><path d='M7 11V7a5 5 0 0110 0v4'/></svg>"
        "<h2>NgawasChill Admin Console</h2>"
        "<p>Login melalui sidebar untuk mengelola sinkronisasi data, interval auto-refresh, dan reset cache.</p>"
        "<p style='margin-top:12px;font-size:12px;color:#555;'>Versi user (lookup NIM &amp; agenda) tersedia di GitHub Pages.</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

# Auto-load data sekali saat login pertama kali
if st.session_state.df is None and st.session_state.data_error is None:
    with st.spinner("Mengambil data dari GitHub…"):
        df_r, err = _load_from_github(st.session_state.fetch_count)
        if err:
            df_r, err = _fetch_from_sharepoint(st.session_state.fetch_count)
        if not err:
            df_r, err = _process_df(df_r)
        if err:
            st.session_state.data_error = err
        else:
            st.session_state.df = df_r
        st.session_state.last_auto_fetch = time.time()
    st.rerun()

# Header
st.markdown(
    "<p class='mv-sup'>🛠 Dashboard Admin</p>"
    "<h1 class='mv-name'>Sinkronisasi Jadwal Ujian</h1>"
    "<div class='mv-badges'>"
    f"<span class='mv-badge'>{e(GITHUB_REPO)}</span>"
    "<span class='mv-meta'>Folder data dipantau: <code style='color:#A8DADC'>data/</code></span>"
    "</div>",
    unsafe_allow_html=True,
)

# Stats
df_now    = st.session_state.df
n_rows    = len(df_now) if df_now is not None else 0
n_dates   = df_now["Tanggal"].nunique() if df_now is not None else 0
n_slots   = df_now["Jam"].nunique() if df_now is not None else 0

# Hitung jumlah pengawas unik
n_pengawas = 0
if df_now is not None:
    nims = set()
    for col in ["NIM (Pengawas 1)", "NIM (Pengawas 2)", "NIM (Pengawas 3)"]:
        if col in df_now.columns:
            nims.update([x for x in df_now[col].astype(str) if x and x not in ("NAN", "NONE", "")])
    n_pengawas = len(nims)

elapsed = time.time() - st.session_state.last_auto_fetch
remain  = max(0, st.session_state.interval_min * 60 - elapsed)
rm, rs  = int(remain // 60), int(remain % 60)
_auto_on = st.session_state.get("auto_update_enabled", True)
auto_label = f"{rm}m {rs}s" if _auto_on else "Nonaktif"
auto_color = '#A8DADC' if _auto_on else '#e06060'

st.markdown(
    f"<div class='stats-row'>"
    f"<div class='stat-box'><p class='stat-value' style='color:#A8DADC'>{n_rows}</p><p class='stat-label'>Baris Data</p></div>"
    f"<div class='stat-box'><p class='stat-value' style='color:#FFC1CC'>{n_pengawas}</p><p class='stat-label'>Pengawas Unik</p></div>"
    f"<div class='stat-box'><p class='stat-value' style='color:#B39CD0'>{n_dates}</p><p class='stat-label'>Tanggal Ujian</p></div>"
    f"<div class='stat-box'><p class='stat-value' style='color:{auto_color}'>{auto_label}</p><p class='stat-label'>Auto-refresh</p></div>"
    f"</div>",
    unsafe_allow_html=True,
)

if st.session_state.data_error:
    st.error(f"❌ {st.session_state.data_error}")
    uploaded = st.file_uploader("Upload CSV/XLSX manual sebagai fallback",
                                type=["csv", "xlsx"], label_visibility="visible")
    if uploaded:
        raw = uploaded.read()
        df_up, err_up = _robust_parse(raw)
        if not err_up:
            df_up, err_up = _process_df(df_up)
        if err_up:
            st.error(f"Gagal: {err_up}")
        else:
            st.session_state.df         = df_up
            st.session_state.data_error = None
            st.rerun()

# ── Commit info ────────────────────────────────────────────────────────────
commit_info = fetch_data_commit_info(st.session_state.fetch_count)

st.markdown("<p class='section-h'>📡 Status Sinkronisasi</p>", unsafe_allow_html=True)

if commit_info:
    wib = format_utc_to_wib(commit_info["date_utc"])
    sha = commit_info["sha"]
    msg = commit_info["message"].split("\n")[0]
    auth = commit_info["author"]
    st.markdown(
        f"<div class='info-card'>"
        f"<h3>Commit Terakhir pada folder <code style='color:#A8DADC'>data/</code></h3>"
        f"<div class='info-row'><span class='info-key'>Waktu (WIB)</span><span class='info-val info-val--ok'>{e(wib)}</span></div>"
        f"<div class='info-row'><span class='info-key'>UTC mentah</span><span class='info-val'>{e(commit_info['date_utc'])}</span></div>"
        f"<div class='info-row'><span class='info-key'>SHA</span><span class='info-val'><code style='color:#B39CD0'>{e(sha)}</code></span></div>"
        f"<div class='info-row'><span class='info-key'>Author</span><span class='info-val'>{e(auth)}</span></div>"
        f"<div class='info-row'><span class='info-key'>Pesan</span><span class='info-val' style='max-width:60%;text-align:right;'>{e(msg)}</span></div>"
        f"</div>",
        unsafe_allow_html=True,
    )
else:
    ts_raw = _get_last_updated_txt(st.session_state.fetch_count)
    fallback = format_utc_to_wib(ts_raw) if ts_raw else "—"
    st.markdown(
        f"<div class='info-card'>"
        f"<h3>Commit Info</h3>"
        f"<div class='info-row'><span class='info-key'>Status</span><span class='info-val info-val--err'>GitHub API tidak merespon</span></div>"
        f"<div class='info-row'><span class='info-key'>Fallback (last_updated.txt)</span><span class='info-val'>{e(fallback)}</span></div>"
        f"</div>",
        unsafe_allow_html=True,
    )

# ── Data preview ──────────────────────────────────────────────────────────
if df_now is not None and not df_now.empty:
    st.markdown("<p class='section-h'>📊 Preview Data Mentah</p>", unsafe_allow_html=True)

    preview_cols = [c for c in [
        "Tanggal", "Jam", "Ruangan", "Nama MK", "Kelas", "Jenis Ujian",
        "NIM (Pengawas 1)", "Nama Lengkap (Pengawas 1)",
        "NIM (Pengawas 2)", "Nama Lengkap (Pengawas 2)",
    ] if c in df_now.columns]

    show_n = st.slider("Jumlah baris ditampilkan", 10, min(500, len(df_now)),
                       value=min(50, len(df_now)), step=10)
    st.dataframe(df_now[preview_cols].head(show_n), use_container_width=True, height=380)

    st.markdown("<p class='section-h'>🕒 Distribusi Slot Waktu</p>", unsafe_allow_html=True)
    slot_count = df_now["Jam"].value_counts().to_dict()
    rows_html = ""
    for slot, cnt in sorted(slot_count.items()):
        rows_html += (
            f"<div class='info-row'>"
            f"<span class='info-key'>{e(slot)}</span>"
            f"<span class='info-val'>{cnt} sesi</span>"
            f"</div>"
        )
    st.markdown(f"<div class='info-card'>{rows_html}</div>", unsafe_allow_html=True)
