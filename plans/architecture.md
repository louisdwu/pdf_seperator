# PDF 书籍自动分割工具 - 技术架构设计

## 1. 项目概述
本工具旨在根据 PDF 内部的电子目录（书签），自动将一本完整的 PDF 书籍拆分为多个独立文件。
**拆分逻辑**：
1. **前导部分**：封面、前言、目录页等（从第0页到正文第一章之前）。
2. **正文章节**：按照一级目录（Top-level TOC）进行拆分，每一章一个文件。
3. **尾部/其他**：如果最后一章结束后还有页面，则归为“其他”。

## 2. 技术选型
*   **编程语言**: Python 3.10+
*   **PDF 处理引擎**: `PyMuPDF` (模块名 `fitz`)
    *   *优势*: 性能极高，对 TOC (目录) 的提取和页面操作支持完善，比 `PyPDF2` 更可靠。
*   **图形用户界面 (GUI)**: `tkinter`
    *   *优势*: Python 标准库内置，无需额外依赖，开发快速，足够满足简单的文件选择和进度展示需求。
    *   *风格*: 使用 `tkinter.ttk` 组件以获得原生系统外观。

## 3. 模块设计

### 3.1 核心逻辑 (`src/pdf_splitter.py`)
该模块负责所有与 PDF 相关的操作，不包含 GUI 代码，便于分离测试。

*   **类 `PDFSplitter`**:
    *   `__init__(filepath)`: 加载 PDF。
    *   `get_toc()`: 获取原始目录结构。
    *   `analyze_structure()`: **核心算法**。分析目录，生成“切分方案”。
        *   识别第一章的起始页码，确定“前导部分”。
        *   遍历一级目录，计算每一章的 `start_page` 和 `end_page`。
        *   检测是否有尾部剩余页面。
    *   `split(output_dir, callback)`: 执行拆分。
        *   `callback(progress, message)`: 用于向 GUI 汇报进度。

### 3.2 用户界面 (`src/gui.py`)
*   **类 `SplitterApp`**:
    *   **UI 布局**:
        *   顶部：文件选择区 (输入路径, 输出文件夹选择)。
        *   中部：Treeview 列表，展示预览的拆分方案 (例如：文件名 | 起始页 | 结束页 | 状态)。
        *   底部：进度条 (Progressbar) 和控制按钮 ("开始分割")。
    *   **交互逻辑**:
        *   选择文件后，自动调用 `PDFSplitter.analyze_structure()` 并填充预览列表。
        *   点击开始后，在后台线程运行 `split()` 以免阻塞界面。

### 3.3 入口脚本 (`main.py`)
*   启动应用程序。

## 4. 数据流
1.  **Input**: 用户拖入 PDF 或点击“浏览”。
2.  **Analyze**:
    *   读取 PDF TOC。
    *   生成 `SplitPlan` 列表: `[{name: "00_前导部分", start: 0, end: 15}, {name: "01_第一章...", start: 16, end: 50}, ...]`
3.  **Review**: 用户在界面上看到即将生成的列表。
4.  **Execute**: 循环处理 `SplitPlan`，提取页面 -> 保存为新 PDF。

## 5. 项目结构
```
pdf_seperator/
├── src/
│   ├── __init__.py
│   ├── pdf_splitter.py  # 核心逻辑
│   └── gui.py           # 界面代码
├── main.py              # 启动入口
├── requirements.txt     # 依赖: PyMuPDF
└── README.md
```

## 6. 开发计划
1.  创建项目结构和虚拟环境。
2.  实现 `pdf_splitter.py` 并编写简单的测试脚本验证目录提取逻辑。
3.  实现 `gui.py` 基本框架。
4.  联调 GUI 与核心逻辑。
5.  优化体验（如非法字符处理、文件名格式化）。