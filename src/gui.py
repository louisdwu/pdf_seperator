"""
PDF 分割器图形用户界面模块
基于 tkinter 实现
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional

from .pdf_splitter import PDFSplitter, SplitPlan


class SplitterApp:
    """PDF 分割器应用程序主窗口"""
    
    def __init__(self, root: tk.Tk):
        """
        初始化应用程序
        
        Args:
            root: Tkinter 根窗口
        """
        self.root = root
        self.root.title("PDF 书籍分割工具")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # 状态变量
        self.splitter: Optional[PDFSplitter] = None
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.is_processing = False
        
        # 构建界面
        self._create_widgets()
        self._setup_layout()
    
    def _create_widgets(self) -> None:
        """创建界面组件"""
        # === 顶部：文件选择区 ===
        self.file_frame = ttk.LabelFrame(self.root, text="文件设置", padding=10)
        
        # 输入文件行
        self.input_label = ttk.Label(self.file_frame, text="输入 PDF:")
        self.input_entry = ttk.Entry(self.file_frame, textvariable=self.input_path, width=60)
        self.input_button = ttk.Button(
            self.file_frame, 
            text="浏览...", 
            command=self._browse_input
        )
        
        # 输出目录行
        self.output_label = ttk.Label(self.file_frame, text="输出目录:")
        self.output_entry = ttk.Entry(self.file_frame, textvariable=self.output_path, width=60)
        self.output_button = ttk.Button(
            self.file_frame, 
            text="浏览...", 
            command=self._browse_output
        )
        
        # === 中部：预览区 ===
        self.preview_frame = ttk.LabelFrame(self.root, text="分割预览", padding=10)
        
        # 创建 Treeview 和滚动条
        self.tree_scroll = ttk.Scrollbar(self.preview_frame)
        self.tree = ttk.Treeview(
            self.preview_frame,
            columns=("filename", "start", "end", "pages"),
            show="headings",
            yscrollcommand=self.tree_scroll.set
        )
        self.tree_scroll.config(command=self.tree.yview)
        
        # 设置列
        self.tree.heading("filename", text="输出文件名")
        self.tree.heading("start", text="起始页")
        self.tree.heading("end", text="结束页")
        self.tree.heading("pages", text="页数")
        
        self.tree.column("filename", width=350)
        self.tree.column("start", width=80, anchor="center")
        self.tree.column("end", width=80, anchor="center")
        self.tree.column("pages", width=80, anchor="center")
        
        # === 底部：控制区 ===
        self.control_frame = ttk.Frame(self.root, padding=10)
        
        # 进度条
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(
            self.control_frame,
            variable=self.progress_var,
            maximum=100,
            length=400
        )
        
        # 状态标签
        self.status_var = tk.StringVar(value="请选择 PDF 文件")
        self.status_label = ttk.Label(
            self.control_frame, 
            textvariable=self.status_var,
            foreground="gray"
        )
        
        # 按钮
        self.analyze_button = ttk.Button(
            self.control_frame,
            text="分析目录",
            command=self._analyze_pdf,
            state="disabled"
        )
        self.split_button = ttk.Button(
            self.control_frame,
            text="开始分割",
            command=self._start_split,
            state="disabled"
        )
    
    def _setup_layout(self) -> None:
        """设置布局"""
        # 文件选择区
        self.file_frame.pack(fill="x", padx=10, pady=5)
        
        self.input_label.grid(row=0, column=0, sticky="w", pady=2)
        self.input_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.input_button.grid(row=0, column=2, pady=2)
        
        self.output_label.grid(row=1, column=0, sticky="w", pady=2)
        self.output_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        self.output_button.grid(row=1, column=2, pady=2)
        
        self.file_frame.columnconfigure(1, weight=1)
        
        # 预览区
        self.preview_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree_scroll.pack(side="right", fill="y")
        
        # 控制区
        self.control_frame.pack(fill="x", padx=10, pady=5)
        
        self.progress_bar.pack(fill="x", pady=5)
        self.status_label.pack(pady=2)
        
        button_frame = ttk.Frame(self.control_frame)
        button_frame.pack(pady=5)
        self.analyze_button.pack(side="left", padx=5)
        self.split_button.pack(side="left", padx=5)
    
    def _browse_input(self) -> None:
        """浏览并选择输入 PDF 文件"""
        filepath = filedialog.askopenfilename(
            title="选择 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if filepath:
            self.input_path.set(filepath)
            # 自动设置输出目录为 PDF 所在目录下的同名文件夹
            pdf_dir = os.path.dirname(filepath)
            pdf_name = os.path.splitext(os.path.basename(filepath))[0]
            default_output = os.path.join(pdf_dir, f"{pdf_name}_分割")
            self.output_path.set(default_output)
            
            # 启用分析按钮
            self.analyze_button.config(state="normal")
            self.status_var.set('已选择文件，点击"分析目录"查看分割预览')
            
            # 清空之前的预览
            self._clear_preview()
    
    def _browse_output(self) -> None:
        """浏览并选择输出目录"""
        dirpath = filedialog.askdirectory(title="选择输出目录")
        if dirpath:
            self.output_path.set(dirpath)
    
    def _clear_preview(self) -> None:
        """清空预览列表"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.split_button.config(state="disabled")
    
    def _analyze_pdf(self) -> None:
        """分析 PDF 目录结构"""
        input_file = self.input_path.get()
        
        if not input_file or not os.path.exists(input_file):
            messagebox.showerror("错误", "请选择有效的 PDF 文件")
            return
        
        try:
            # 关闭之前的文档
            if self.splitter:
                self.splitter.close()
            
            self.status_var.set("正在分析 PDF 结构...")
            self.root.update()
            
            # 加载并分析
            self.splitter = PDFSplitter(input_file)
            plans = self.splitter.analyze_structure()
            
            # 清空并填充预览列表
            self._clear_preview()
            
            if not plans:
                self.status_var.set("未能识别目录结构")
                messagebox.showwarning("警告", "未能从 PDF 中识别目录结构，请确认文件包含书签。")
                return
            
            for plan in plans:
                page_count = plan.end_page - plan.start_page + 1
                self.tree.insert("", "end", values=(
                    f"{plan.name}.pdf",
                    plan.start_page + 1,  # 显示从1开始的页码
                    plan.end_page + 1,
                    page_count
                ))
            
            total_pages = self.splitter.get_page_count()
            self.status_var.set(
                f"共 {total_pages} 页，将分割为 {len(plans)} 个文件。"
                f'确认后点击"开始分割"'
            )
            self.split_button.config(state="normal")
            
        except Exception as e:
            messagebox.showerror("错误", f"分析 PDF 时出错:\n{str(e)}")
            self.status_var.set("分析失败")
    
    def _start_split(self) -> None:
        """开始分割操作"""
        if self.is_processing:
            return
        
        output_dir = self.output_path.get()
        if not output_dir:
            messagebox.showerror("错误", "请指定输出目录")
            return
        
        if not self.splitter:
            messagebox.showerror("错误", "请先分析 PDF 文件")
            return
        
        # 确认覆盖
        if os.path.exists(output_dir) and os.listdir(output_dir):
            if not messagebox.askyesno(
                "确认",
                f"输出目录已存在且不为空：\n{output_dir}\n\n是否继续？（可能覆盖文件）"
            ):
                return
        
        # 禁用按钮，开始处理
        self.is_processing = True
        self.analyze_button.config(state="disabled")
        self.split_button.config(state="disabled")
        self.progress_var.set(0)
        
        # 在后台线程执行分割
        thread = threading.Thread(target=self._do_split, args=(output_dir,))
        thread.daemon = True
        thread.start()
    
    def _do_split(self, output_dir: str) -> None:
        """后台执行分割操作"""
        try:
            def progress_callback(progress: float, message: str):
                # 在主线程更新 UI
                self.root.after(0, self._update_progress, progress, message)
            
            output_files = self.splitter.split(output_dir, progress_callback)
            
            # 完成
            self.root.after(0, self._on_split_complete, output_files)
            
        except Exception as e:
            self.root.after(0, self._on_split_error, str(e))
    
    def _update_progress(self, progress: float, message: str) -> None:
        """更新进度条和状态"""
        self.progress_var.set(progress * 100)
        self.status_var.set(message)
    
    def _on_split_complete(self, output_files: list) -> None:
        """分割完成回调"""
        self.is_processing = False
        self.analyze_button.config(state="normal")
        self.progress_var.set(100)
        
        output_dir = self.output_path.get()
        messagebox.showinfo(
            "完成",
            f"分割完成！\n共生成 {len(output_files)} 个文件\n\n输出目录：\n{output_dir}"
        )
        
        # 询问是否打开输出目录
        if messagebox.askyesno("提示", "是否打开输出目录？"):
            os.startfile(output_dir)  # Windows
    
    def _on_split_error(self, error_msg: str) -> None:
        """分割出错回调"""
        self.is_processing = False
        self.analyze_button.config(state="normal")
        self.split_button.config(state="normal")
        self.status_var.set("分割失败")
        messagebox.showerror("错误", f"分割过程中出错:\n{error_msg}")
    
    def on_closing(self) -> None:
        """窗口关闭处理"""
        if self.is_processing:
            if not messagebox.askyesno("确认", "正在处理中，确定要退出吗？"):
                return
        
        if self.splitter:
            self.splitter.close()
        
        self.root.destroy()


def main():
    """启动应用程序"""
    root = tk.Tk()
    app = SplitterApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()