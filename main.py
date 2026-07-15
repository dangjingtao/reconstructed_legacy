# -*- coding: utf-8 -*-
"""DWG/DXF JZD extraction tool rebuilt from the recovered Python bytecode.

Target runtime: CPython 3.8 on Windows 7 SP1 or newer.
"""

from __future__ import print_function

import ctypes
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading


TEMP_ODA_DIR = None
ODA_EXE = None


def get_windows_version():
    class OSVERSIONINFO(ctypes.Structure):
        _fields_ = [
            ("dwOSVersionInfoSize", ctypes.c_uint32),
            ("dwMajorVersion", ctypes.c_uint32),
            ("dwMinorVersion", ctypes.c_uint32),
            ("dwBuildNumber", ctypes.c_uint32),
            ("dwPlatformId", ctypes.c_uint32),
            ("szCSDVersion", ctypes.c_wchar * 128),
        ]

    try:
        osvi = OSVERSIONINFO()
        osvi.dwOSVersionInfoSize = ctypes.sizeof(OSVERSIONINFO)
        ctypes.windll.kernel32.GetVersionExW(ctypes.byref(osvi))
        return osvi.dwMajorVersion, osvi.dwMinorVersion, osvi.dwBuildNumber
    except Exception:
        return 10, 0, 0


def is_win7():
    major, minor, _ = get_windows_version()
    return major == 6 and minor == 1


def _resource_root():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def setup_portable_oda():
    global TEMP_ODA_DIR, ODA_EXE

    if TEMP_ODA_DIR and os.path.exists(TEMP_ODA_DIR):
        return True

    bundled_oda = os.path.join(_resource_root(), "oda")
    if os.path.isdir(bundled_oda):
        try:
            temp_dir = tempfile.mkdtemp(prefix="oda_")
            for item in os.listdir(bundled_oda):
                src = os.path.join(bundled_oda, item)
                dst = os.path.join(temp_dir, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            candidate = os.path.join(temp_dir, "ODAFileConverter.exe")
            if os.path.exists(candidate):
                TEMP_ODA_DIR = temp_dir
                ODA_EXE = candidate
                return True
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as exc:
            print("释放便携版ODA失败: {0}".format(exc))

    candidates = [
        r"C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe",
        r"C:\Program Files\ODA\ODAFileConverter 21.5.0\ODAFileConverter.exe",
        r"C:\Program Files (x86)\ODA\ODAFileConverter 21.5.0\ODAFileConverter.exe",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            ODA_EXE = candidate
            return True
    return False


def cleanup_oda():
    global TEMP_ODA_DIR
    if TEMP_ODA_DIR and os.path.exists(TEMP_ODA_DIR):
        try:
            shutil.rmtree(TEMP_ODA_DIR, ignore_errors=True)
        except Exception:
            pass
        TEMP_ODA_DIR = None


class OPENFILENAME(ctypes.Structure):
    _fields_ = [
        ("lStructSize", ctypes.c_uint32),
        ("hwndOwner", ctypes.c_void_p),
        ("hInstance", ctypes.c_void_p),
        ("lpstrFilter", ctypes.c_wchar_p),
        ("lpstrCustomFilter", ctypes.c_wchar_p),
        ("nMaxCustFilter", ctypes.c_uint32),
        ("nFilterIndex", ctypes.c_uint32),
        ("lpstrFile", ctypes.c_wchar_p),
        ("nMaxFile", ctypes.c_uint32),
        ("lpstrFileTitle", ctypes.c_wchar_p),
        ("nMaxFileTitle", ctypes.c_uint32),
        ("lpstrInitialDir", ctypes.c_wchar_p),
        ("lpstrTitle", ctypes.c_wchar_p),
        ("Flags", ctypes.c_uint32),
        ("nFileOffset", ctypes.c_uint16),
        ("nFileExtension", ctypes.c_uint16),
        ("lpstrDefExt", ctypes.c_wchar_p),
        ("lCustData", ctypes.c_ssize_t),
        ("lpfnHook", ctypes.c_void_p),
        ("lpTemplateName", ctypes.c_wchar_p),
        ("pvReserved", ctypes.c_void_p),
        ("dwReserved", ctypes.c_uint32),
        ("FlagsEx", ctypes.c_uint32),
    ]


OFN_FILEMUSTEXIST = 0x1000
OFN_PATHMUSTEXIST = 0x0800
OFN_HIDEREADONLY = 0x0004
OFN_EXPLORER = 0x80000
MB_OK = 0
MB_OKCANCEL = 1
MB_ICONINFORMATION = 64
MB_ICONERROR = 16
MB_ICONWARNING = 48
MB_TOPMOST = 0x40000
IDOK = 1


def show_file_dialog(file_type="all"):
    filters = {
        "dwg": ("DWG文件 (*.dwg)\0*.dwg\0所有文件 (*.*)\0*.*\0\0", "选择DWG文件"),
        "dxf": ("DXF文件 (*.dxf)\0*.dxf\0所有文件 (*.*)\0*.*\0\0", "选择DXF文件"),
        "all": (
            "CAD文件 (*.dwg;*.dxf)\0*.dwg;*.dxf\0DWG文件 (*.dwg)\0*.dwg\0"
            "DXF文件 (*.dxf)\0*.dxf\0所有文件 (*.*)\0*.*\0\0",
            "选择DWG或DXF文件",
        ),
    }
    filter_text, title = filters.get(file_type, filters["all"])
    buffer = ctypes.create_unicode_buffer(32768)
    ofn = OPENFILENAME()
    ofn.lStructSize = ctypes.sizeof(OPENFILENAME)
    ofn.lpstrFilter = filter_text
    ofn.lpstrFile = ctypes.cast(buffer, ctypes.c_wchar_p)
    ofn.nMaxFile = len(buffer)
    ofn.lpstrTitle = title
    ofn.Flags = OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_HIDEREADONLY | OFN_EXPLORER
    if ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(ofn)):
        return buffer.value
    return None


def show_message(message, title="提示", kind="info"):
    icon = {"info": MB_ICONINFORMATION, "error": MB_ICONERROR, "warning": MB_ICONWARNING}.get(kind, MB_ICONINFORMATION)
    return ctypes.windll.user32.MessageBoxW(None, str(message), str(title), icon | MB_TOPMOST)


def show_confirm(message, title="确认"):
    result = ctypes.windll.user32.MessageBoxW(None, str(message), str(title), MB_OKCANCEL | MB_ICONINFORMATION | MB_TOPMOST)
    return result == IDOK


def convert_dwg_to_dxf(dwg_path, output_dir=None):
    if output_dir is None:
        output_dir = os.path.dirname(dwg_path) or os.getcwd()
    base_name = os.path.splitext(os.path.basename(dwg_path))[0]
    dxf_path = os.path.join(output_dir, base_name + ".dxf")
    if not ODA_EXE or not os.path.exists(ODA_EXE):
        return False, {"error": "ODA转换器未就绪"}

    input_dir = os.path.dirname(dwg_path) or os.getcwd()
    input_file = os.path.basename(dwg_path)
    cmd = [ODA_EXE, input_dir, output_dir, "ACAD2013", "DXF", "0", "0", input_file]
    env = os.environ.copy()
    env["PATH"] = os.path.dirname(ODA_EXE) + os.pathsep + env.get("PATH", "")
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    try:
        result = subprocess.run(
            cmd,
            cwd=os.path.dirname(ODA_EXE),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            startupinfo=startupinfo,
        )
        if result.returncode == 0 and os.path.exists(dxf_path) and os.path.getsize(dxf_path) > 0:
            return True, {"dxf_path": dxf_path, "msg": "DWG转换成功 (ACAD2013→DXF)"}
        error = (result.stderr or "未知错误").strip()
        return False, {"error": "DWG转换失败 (rc={0}): {1}".format(result.returncode, error)}
    except Exception as exc:
        return False, {"error": "DWG转换出错: {0}".format(exc)}


def _is_closed_polyline(entity):
    """Return whether a polyline is explicitly closed or repeats its first point."""
    kind = entity.dxftype()
    if kind not in ("POLYLINE", "LWPOLYLINE"):
        return False
    if kind == "LWPOLYLINE":
        points = list(entity.get_points())
        closed = bool(getattr(entity.dxf, "flags", 0) & 1)
    else:
        points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
        closed = bool(getattr(entity.dxf, "flags", 0) & 1)
    if len(points) < 3:
        return False
    return closed or points[0][:2] == points[-1][:2]


def _polyline_coordinates(entity):
    if entity.dxftype() == "LWPOLYLINE":
        coords = [(float(point[1]), float(point[0])) for point in entity.get_points()]
    else:
        coords = [
            (float(vertex.dxf.location.y), float(vertex.dxf.location.x))
            for vertex in entity.vertices
        ]
    if coords and coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords


def _is_red_entity(entity):
    # ACI 1 is the standard DXF red index. True-color is supported when present.
    if getattr(entity.dxf, "color", 0) == 1:
        return True
    return getattr(entity.dxf, "true_color", None) == 0xFF0000


def _collect_closed_candidates(path):
    import ezdxf

    doc = ezdxf.readfile(path)
    candidates = []
    for entity in doc.modelspace():
        if not _is_closed_polyline(entity):
            continue
        coords = _polyline_coordinates(entity)
        if len(coords) >= 4:
            candidates.append((str(entity.dxf.layer).upper(), _is_red_entity(entity), coords))
    return candidates


def _choose_candidate(candidates, mode="priority"):
    if not candidates:
        return []
    jzd = [item for item in candidates if item[0] == "JZD"]
    red = [item for item in candidates if item[1]]
    if mode == "jzd":
        pool = jzd
    elif mode == "red":
        pool = red
    elif mode == "all":
        pool = candidates
    else:
        pool = jzd or red or candidates
    if not pool:
        return []
    return max(pool, key=lambda item: len(item[2]))[2]


def parse_dxf_points_mode(path, mode="priority"):
    try:
        return _choose_candidate(_collect_closed_candidates(path), mode)
    except Exception:
        return parse_dxf_points_native(path)


def parse_dxf_points(path):
    """Choose the largest closed polyline using the integrated priority rule."""
    return parse_dxf_points_mode(path, "priority")


def _has_closed_jzd_polyline(path):
    try:
        import ezdxf

        doc = ezdxf.readfile(path)
        return any(
            str(entity.dxf.layer).upper() == "JZD" and _is_closed_polyline(entity)
            for entity in doc.modelspace()
        )
    except Exception:
        return False


def parse_dxf_points_native(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            lines = [line.strip() for line in handle.readlines()]
    except Exception:
        return []

    points = []
    in_entities = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if line == "0" and i + 3 < len(lines) and lines[i + 1] == "SECTION" and lines[i + 3] == "ENTITIES":
            in_entities = True
        elif line == "0" and i + 1 < len(lines) and lines[i + 1] == "ENDSEC" and in_entities:
            in_entities = False
        if in_entities and line == "10" and i + 1 < len(lines):
            try:
                x = float(lines[i + 1])
            except ValueError:
                i += 1
                continue
            for j in range(i + 2, min(i + 12, len(lines) - 1)):
                if lines[j] != "20":
                    continue
                try:
                    y = float(lines[j + 1])
                except ValueError:
                    break
                if abs(x) > 0.001 or abs(y) > 0.001:
                    points.append((x, y))
                break
        i += 1
    return points


def calculate_area(coords):
    if len(coords) < 3:
        return 0.0
    area = 0.0
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0 / 10000.0


def extract_jzd_layer(dxf_path, output_dir=None):
    try:
        import ezdxf
    except ImportError as exc:
        return False, {"error": "需要ezdxf库: {0}".format(exc)}

    output_dir = output_dir or os.path.dirname(dxf_path) or os.getcwd()
    try:
        doc = ezdxf.readfile(dxf_path)
        modelspace = doc.modelspace()
        selected = []
        for entity in modelspace:
            if str(entity.dxf.layer).upper() == "JZD":
                selected.append(entity)
        if not selected:
            return False, {"error": "未找到JZD图层"}
        for entity in list(modelspace):
            if entity not in selected:
                modelspace.delete_entity(entity)
        base_name = os.path.splitext(os.path.basename(dxf_path))[0]
        out_path = os.path.join(output_dir, base_name + "_jzd.dxf")
        doc.saveas(out_path)
        return True, {"jzd_count": len(selected), "jzd_dxf": out_path}
    except Exception as exc:
        return False, {"error": str(exc)}


def convert_dxf_to_txt(dxf_path, output_dir=None, mode="priority"):
    output_dir = output_dir or os.path.dirname(dxf_path) or os.getcwd()
    try:
        coords = parse_dxf_points_mode(dxf_path, mode)
        if not coords:
            return False, {"error": "未找到坐标点"}
        area = calculate_area(coords)
        unique_coords = []
        for coord in coords:
            if not unique_coords or coord != unique_coords[-1]:
                unique_coords.append(coord)
        filtered_coords = []
        for coord in unique_coords:
            if not filtered_coords or math.hypot(coord[0] - filtered_coords[-1][0], coord[1] - filtered_coords[-1][1]) > 0.012:
                filtered_coords.append(coord)
        if filtered_coords and filtered_coords[0] != filtered_coords[-1]:
            filtered_coords.append(filtered_coords[0])

        base_name = os.path.splitext(os.path.basename(dxf_path))[0]
        if base_name.endswith("_jzd") or base_name.endswith("_JZD"):
            base_name = base_name[:-4]
        txt_path = os.path.join(output_dir, base_name + ".txt")
        n = len(filtered_coords)
        with open(txt_path, "w", encoding="utf-8-sig") as handle:
            handle.write("[属性描述]\n")
            handle.write("坐标系=2000国家大地坐标系\n")
            handle.write("几度分带=3\n")
            handle.write("投影类型=高斯克吕格\n")
            handle.write("计量单位=米\n")
            handle.write("带号=38\n")
            handle.write("精度=0.001\n")
            handle.write("转换参数=,,,,,,\n")
            handle.write("[地块坐标]\n")
            handle.write("{0},{1:.3f},1,1,面,,,,@\n".format(n, area))
            for i, (x, y) in enumerate(filtered_coords):
                handle.write("J{0},1,{1:.3f},{2:.3f}\n".format(i + 1, x, y))
        return True, {
            "txt_path": txt_path,
            "point_count": n,
            "area_ha": area,
            "txt_msg": "界址点{0}个，面积{1:.6f}公顷".format(n, area),
        }
    except Exception as exc:
        return False, {"error": str(exc)}


def process_dxf_file(dxf_path, mode="priority", output_dir=None):
    output_dir = output_dir or os.path.dirname(dxf_path) or os.getcwd()
    if mode in ("priority", "jzd") and _has_closed_jzd_polyline(dxf_path):
        ok1, result1 = extract_jzd_layer(dxf_path, output_dir)
        if not ok1:
            return False, result1
        ok2, result2 = convert_dxf_to_txt(result1["jzd_dxf"], output_dir, "jzd")
        if not ok2:
            return False, result2
        result2["jzd_count"] = result1["jzd_count"]
        result2["jzd_dxf"] = result1["jzd_dxf"]
        return True, result2

    if mode == "jzd":
        return False, {"error": "未找到JZD图层中的闭合多段线"}
    if not parse_dxf_points_mode(dxf_path, mode):
        return False, {"error": "未找到符合当前模式的闭合多段线"}
    ok, result = convert_dxf_to_txt(dxf_path, output_dir, mode)
    if not ok:
        return False, result
    result["jzd_count"] = 0
    result["jzd_dxf"] = None
    return True, result


def process_dwg_file(dwg_path, mode="priority", output_dir=None):
    output_dir = output_dir or os.path.dirname(dwg_path) or os.getcwd()
    ok1, result1 = convert_dwg_to_dxf(dwg_path, output_dir)
    if not ok1:
        return False, result1
    ok2, result2 = process_dxf_file(result1["dxf_path"], mode, output_dir)
    if not ok2:
        return False, result2
    result2["dwg_msg"] = result1["msg"]
    result2["dxf_path"] = result1["dxf_path"]
    return True, result2


def process_file(path, mode="priority", output_dir=None):
    suffix = os.path.splitext(path)[1].lower()
    if suffix == ".dwg":
        return process_dwg_file(path, mode, output_dir)
    if suffix == ".dxf":
        return process_dxf_file(path, mode, output_dir)
    return False, {"error": "不支持的文件类型: {0}".format(suffix or "未知")}


def _result_message(path, ok, result):
    if ok:
        return "✓ {0}\n  {1}\n  JZD实体: {2}\n  {3}".format(
            os.path.basename(path),
            result.get("dwg_msg", ""),
            result.get("jzd_count", 0),
            result.get("txt_msg", "处理完成"),
        )
    return "✗ {0}\n  错误: {1}".format(os.path.basename(path), result.get("error", "未知"))


def run_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("DWG / DXF 转换器")
    root.geometry("760x560")
    root.minsize(640, 460)

    input_dir_var = tk.StringVar()
    output_dir_var = tk.StringVar()
    processing = [False]
    status_var = tk.StringVar(value="请选择输入文件夹")

    frame = ttk.Frame(root, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="DWG / DXF 转换器", font=("Microsoft YaHei UI", 12, "bold")).pack(anchor=tk.W)

    path_frame = ttk.LabelFrame(frame, text="文件夹")
    path_frame.pack(fill=tk.X, pady=(10, 8))
    path_frame.columnconfigure(1, weight=1)
    ttk.Label(path_frame, text="输入文件夹").grid(row=0, column=0, padx=8, pady=6, sticky=tk.W)
    ttk.Entry(path_frame, textvariable=input_dir_var, state="readonly").grid(row=0, column=1, padx=4, pady=6, sticky=tk.EW)
    input_button = ttk.Button(path_frame, text="选择...", command=lambda: choose_input())
    input_button.grid(row=0, column=2, padx=8, pady=6)
    ttk.Label(path_frame, text="导出位置").grid(row=1, column=0, padx=8, pady=6, sticky=tk.W)
    ttk.Entry(path_frame, textvariable=output_dir_var, state="readonly").grid(row=1, column=1, padx=4, pady=6, sticky=tk.EW)
    output_button = ttk.Button(path_frame, text="选择...", command=lambda: choose_output())
    output_button.grid(row=1, column=2, padx=8, pady=6)

    list_frame = ttk.LabelFrame(frame, text="待处理文件")
    list_frame.pack(fill=tk.BOTH, expand=True)
    file_list = tk.Listbox(list_frame, height=8)
    scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=file_list.yview)
    file_list.configure(yscrollcommand=scrollbar.set)
    file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0), pady=6)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 6), pady=6)

    log_frame = ttk.LabelFrame(frame, text="处理日志")
    log_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 8))
    log_text = tk.Text(log_frame, height=8, state=tk.DISABLED, wrap=tk.WORD)
    log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=log_text.yview)
    log_text.configure(yscrollcommand=log_scrollbar.set)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def append_log(message):
        log_text.configure(state=tk.NORMAL)
        log_text.insert(tk.END, message + "\n")
        log_text.see(tk.END)
        log_text.configure(state=tk.DISABLED)

    def input_files():
        folder = input_dir_var.get()
        if not folder:
            return []
        return [
            os.path.join(folder, name)
            for name in sorted(os.listdir(folder))
            if os.path.isfile(os.path.join(folder, name))
            and os.path.splitext(name)[1].lower() in (".dwg", ".dxf")
        ]

    def refresh_files(paths):
        file_list.delete(0, tk.END)
        for path in paths:
            file_list.insert(tk.END, os.path.basename(path))
        status_var.set("已发现 {0} 个 DWG/DXF 文件".format(len(paths)))

    def choose_input():
        if processing[0]:
            return
        folder = filedialog.askdirectory(title="选择输入文件夹")
        if folder:
            input_dir_var.set(folder)
            if not output_dir_var.get():
                output_dir_var.set(os.path.join(folder, "output"))
            refresh_files(input_files())

    def choose_output():
        if processing[0]:
            return
        folder = filedialog.askdirectory(title="选择导出位置")
        if folder:
            output_dir_var.set(folder)

    def set_buttons(enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        process_button.configure(state=state)
        input_button.configure(state=state)
        output_button.configure(state=state)

    def finish_run(success_count, total):
        processing[0] = False
        set_buttons(True)
        status_var.set("处理完成：{0}/{1} 成功".format(success_count, total))
        messagebox.showinfo("处理完成", "处理完成：{0}/{1} 成功".format(success_count, total))

    def worker(paths, output_dir):
        success_count = 0
        try:
            oda_ready = setup_portable_oda()
            root.after(0, append_log, "ODA 状态：{0}".format("可用" if oda_ready else "未找到"))
            for index, path in enumerate(paths, 1):
                root.after(0, append_log, "[{0}/{1}] 处理：{2}".format(index, len(paths), os.path.basename(path)))
                ok, result = process_file(path, "priority", output_dir)
                if ok:
                    success_count += 1
                root.after(0, append_log, _result_message(path, ok, result))
        except Exception as exc:
            root.after(0, append_log, "处理线程异常：{0}".format(exc))
        finally:
            cleanup_oda()
            root.after(0, finish_run, success_count, len(paths))

    def start_process():
        if processing[0]:
            return
        paths = input_files()
        output_dir = output_dir_var.get()
        if not paths:
            messagebox.showwarning("提示", "输入文件夹中没有 DWG 或 DXF 文件")
            return
        if not output_dir:
            messagebox.showwarning("提示", "请选择导出位置")
            return
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("错误", "无法创建导出目录：{0}".format(exc))
            return
        processing[0] = True
        set_buttons(False)
        status_var.set("正在处理...")
        refresh_files(paths)
        threading.Thread(target=worker, args=(paths, output_dir), daemon=True).start()

    def close_window():
        if processing[0]:
            messagebox.showwarning("提示", "当前正在处理文件，请等待处理完成")
            return
        cleanup_oda()
        root.destroy()

    button_frame = ttk.Frame(frame)
    button_frame.pack(fill=tk.X, pady=(8, 0))
    process_button = ttk.Button(button_frame, text="开始转换", command=start_process)
    process_button.pack(side=tk.RIGHT, padx=(6, 0))
    ttk.Button(button_frame, text="退出", command=close_window).pack(side=tk.RIGHT)
    ttk.Label(frame, textvariable=status_var).pack(anchor=tk.W, pady=(8, 0))

    root.protocol("WM_DELETE_WINDOW", close_window)
    root.mainloop()


def run(paths):
    if not paths:
        run_gui()
        return
    setup_portable_oda()
    if not paths:
        cleanup_oda()
        return

    results = []
    success_count = 0
    for path in paths:
        ok, result = process_file(path)
        results.append((path, ok, result))
        if ok:
            success_count += 1
    messages = []
    for path, ok, result in results:
        if ok:
            message = _result_message(path, True, result)
        else:
            message = _result_message(path, False, result)
        messages.append(message)
    show_message("\n\n".join(messages), "处理完成 ({0}/{1} 成功)".format(success_count, len(results)), "info" if success_count == len(results) else "warning")
    cleanup_oda()


if __name__ == "__main__":
    run([path for path in sys.argv[1:] if os.path.isfile(path)])
