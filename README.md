# reconstructed_legacy

这是一个从旧版 Windows 程序恢复出的地块界址数据提取工具。工具面向 Windows 7 及以上系统，用于从 DWG/DXF 图纸中识别闭合地块边界，计算面积，并导出地块坐标 TXT。

项目不是原厂源码，而是根据已恢复的 Python 字节码和运行行为整理出的可维护版本。

## 功能

- 批量读取一个输入目录中的 `.dwg` 和 `.dxf` 文件。
- DWG 通过 ODA File Converter 转换为 DXF，目标格式为 `ACAD2013 DXF`。
- 优先识别 `JZD` 图层中的闭合多段线。
- 没有可用的 JZD 图层时，按优先规则选择闭合多段线：JZD 图层、红色实体、最后选择最大候选轮廓。
- 提取界址点坐标，去除相邻距离小于 `0.012` 的重复点，并闭合首尾点。
- 计算面积，单位为公顷。
- 输出包含以下内容的 UTF-8 BOM TXT：坐标系、分带、投影类型、计量单位、精度、带号、面积和界址点坐标。
- 加密分支在 TXT 生成后额外输出同名的 `_加密.jmtxt`，不修改原 TXT。
- 在 `ezdxf` 不可用或解析失败时，使用内置的基础 DXF 文本解析器作为回退路径。

## 使用方式

### 图形界面

在 Windows 上运行：

```bat
python main.py
```

程序会依次选择输入文件夹和导出文件夹，然后点击“开始转换”。输出目录会生成：

- DWG 转换得到的 DXF
- 提取后的 `_jzd.dxf`（适用时）
- 与输入文件同名的 `.txt`

### 命令行

也可以直接传入一个或多个 DWG/DXF 文件：

```bat
python main.py D:\data\sample.dwg D:\data\boundary.dxf
```

命令行模式使用输入文件所在目录作为输出目录，并通过 Windows 消息框报告处理结果。

## 开发环境

推荐使用 CPython 3.8，原因是该版本与原始 Windows 7 运行环境和当前 PyInstaller 配置一致。安装依赖：

```bat
py -3.8 -m venv ..\.venv-win7
..\.venv-win7\Scripts\python.exe -m pip install -r requirements-win7-legacy.txt
```

依赖包括：

- `ezdxf 1.1.4`：读取和写入 DXF
- `gmssl 3.2.2`：加密分支生成兼容 `GisqTxtEncrypt` 的 SM2 密文
- `numpy 1.21.6`、`fonttools 4.47.0`、`pyparsing 3.0.9`、`typing-extensions 4.7.1`
- `pyinstaller 5.13.2`：生成 Windows 可执行文件

开发运行前，需要准备 ODA File Converter。程序会按以下顺序查找：

1. 打包程序中的 `oda\ODAFileConverter.exe`
2. `C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe`
3. `C:\Program Files\ODA\ODAFileConverter 21.5.0\ODAFileConverter.exe`
4. `C:\Program Files (x86)\ODA\ODAFileConverter 21.5.0\ODAFileConverter.exe`

如果使用便携目录，`oda` 目录必须包含 ODA 转换器及其 DLL。没有 ODA 时仍可直接处理 DXF，但不能处理 DWG。

## 打包

打包配置在 `jzd_extract_win7_legacy.spec`，构建脚本是 `build_legacy.bat`。准备好以下目录后，在项目目录运行：

- `oda\`：便携版 ODA File Converter 及依赖
- `win7_runtime\`：Windows 7 所需运行库 DLL
- `..\.venv-win7\`：包含项目依赖和 PyInstaller 的虚拟环境

```bat
build_legacy.bat
```

成功后，可执行文件位于：

```text
dist\jzd_extract_win7_legacy.exe
```

也可以手动执行：

```bat
..\.venv-win7\Scripts\python.exe -m PyInstaller --noconfirm --clean jzd_extract_win7_legacy.spec
```

spec 文件会把 `oda` 和 `win7_runtime` 放入 PyInstaller 数据文件，并收集 `ezdxf` 的必要子模块。

## 目录说明

| 路径 | 作用 |
| --- | --- |
| `main.py` | 主程序、DWG/DXF 处理流程和 Tkinter 界面 |
| `requirements-win7-legacy.txt` | 固定版本依赖 |
| `jzd_extract_win7_legacy.spec` | PyInstaller 打包配置 |
| `build_legacy.bat` | Windows 打包脚本 |
| `choco_oda_19.12/` | ODA 安装包元数据和 Chocolatey 安装脚本 |
| `oda/` | 本地便携 ODA 运行时，不纳入 Git |
| `win7_runtime/` | Windows 运行库，不纳入 Git |
| `build/`、`dist/` | 构建输出，不纳入 Git |

## 输出格式示例

生成的 TXT 使用 UTF-8 BOM，结构类似：

```text
[属性描述]
坐标系=2000国家大地坐标系
几度分带=3
投影类型=高斯克吕格
计量单位=米
带号=38
精度=0.001
转换参数=,,,,,,
[地块坐标]
...
```

## 已知限制

- DWG 转换依赖 ODA File Converter，项目没有把 ODA 二进制文件提交到 Git。
- 运行和打包需要 Windows 环境；Windows 7 兼容性取决于本机运行库和 ODA 版本。
- 自动识别依赖图纸中的闭合多段线。图纸使用非标准实体或边界未闭合时，可能无法提取。
- 该项目是恢复版本，输出行为以已验证的旧程序样本和当前代码为准，不代表原厂实现的全部功能。

## 脱敏与版本控制

`.gitignore` 会忽略测试数据、DWG/DXF/JMTXT、构建产物、运行时 DLL、安装包、日志和密钥文件。提交新测试前，应使用虚构坐标和文件名，不要提交真实项目图纸、真实地块信息或私钥材料。
