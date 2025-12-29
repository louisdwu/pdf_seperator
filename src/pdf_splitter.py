"""
PDF 分割器核心模块
负责 PDF 加载、目录解析和页面拆分操作
"""

import os
import re
from dataclasses import dataclass
from typing import List, Optional, Callable, Tuple

import fitz  # PyMuPDF


@dataclass
class SplitPlan:
    """分割计划数据类"""
    name: str           # 输出文件名（不含扩展名）
    start_page: int     # 起始页（从0开始）
    end_page: int       # 结束页（包含）
    title: str          # 原始标题
    level: int          # 目录层级（1为一级标题）


class PDFSplitter:
    """PDF 分割器类"""
    
    def __init__(self, filepath: str):
        """
        初始化 PDF 分割器
        
        Args:
            filepath: PDF 文件路径
        """
        self.filepath = filepath
        self.doc: Optional[fitz.Document] = None
        self.toc: List[Tuple] = []
        self.split_plans: List[SplitPlan] = []
        self._load_pdf()
    
    def _load_pdf(self) -> None:
        """加载 PDF 文件"""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"文件不存在: {self.filepath}")
        
        self.doc = fitz.open(self.filepath)
        self.toc = self.doc.get_toc()  # 获取目录结构
    
    def get_toc(self) -> List[Tuple]:
        """
        获取原始目录结构
        
        Returns:
            目录列表，每项为 (level, title, page_number)
        """
        return self.toc
    
    def get_page_count(self) -> int:
        """获取 PDF 总页数"""
        return len(self.doc) if self.doc else 0
    
    def _sanitize_filename(self, name: str) -> str:
        """
        清理文件名，移除非法字符
        
        Args:
            name: 原始文件名
            
        Returns:
            清理后的文件名
        """
        # 移除或替换 Windows 文件名非法字符
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, '_', name)
        # 移除首尾空格和点
        sanitized = sanitized.strip(' .')
        # 限制长度（保守起见，限制为100字符）
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        return sanitized or "未命名"
    
    def analyze_structure(self) -> List[SplitPlan]:
        """
        分析 PDF 结构，生成分割计划
        
        分割策略：
        1. 前导部分：从第0页到第一个一级目录之前
        2. 正文章节：按一级目录拆分
        3. 尾部（如有）：最后一章之后的剩余页面
        
        Returns:
            分割计划列表
        """
        if not self.doc:
            raise RuntimeError("PDF 文件未加载")
        
        total_pages = len(self.doc)
        self.split_plans = []
        
        # 筛选出一级目录（用于主要章节分割）
        top_level_toc = [(title, page) for level, title, page in self.toc if level == 1]
        
        if not top_level_toc:
            # 没有目录，将整个文档作为一个部分
            self.split_plans.append(SplitPlan(
                name="00_完整文档",
                start_page=0,
                end_page=total_pages - 1,
                title="完整文档",
                level=0
            ))
            return self.split_plans
        
        # 1. 前导部分（封面、前言、目录等）
        first_chapter_page = top_level_toc[0][1] - 1  # 转换为从0开始的索引
        if first_chapter_page > 0:
            self.split_plans.append(SplitPlan(
                name="00_前导部分",
                start_page=0,
                end_page=first_chapter_page - 1,
                title="前导部分（封面/目录等）",
                level=0
            ))
        
        # 2. 正文各章节
        for i, (title, page_num) in enumerate(top_level_toc):
            start_page = page_num - 1  # 转换为从0开始的索引
            
            # 确定结束页
            if i + 1 < len(top_level_toc):
                # 下一章的前一页
                end_page = top_level_toc[i + 1][1] - 2
            else:
                # 最后一章，到文档末尾
                end_page = total_pages - 1
            
            # 生成带序号的文件名
            chapter_num = str(i + 1).zfill(2)
            safe_title = self._sanitize_filename(title)
            filename = f"{chapter_num}_{safe_title}"
            
            self.split_plans.append(SplitPlan(
                name=filename,
                start_page=start_page,
                end_page=end_page,
                title=title,
                level=1
            ))
        
        # 3. 检查是否有尾部内容（附录等未被目录覆盖的部分）
        # 注意：通常最后一章会覆盖到末尾，此处逻辑已在上面处理
        
        return self.split_plans
    
    def split(
        self,
        output_dir: str,
        callback: Optional[Callable[[float, str], None]] = None
    ) -> List[str]:
        """
        执行分割操作
        
        Args:
            output_dir: 输出目录路径
            callback: 进度回调函数，接收 (progress: 0.0-1.0, message: str)
            
        Returns:
            生成的文件路径列表
        """
        if not self.split_plans:
            self.analyze_structure()
        
        if not self.split_plans:
            raise RuntimeError("无法生成分割计划")
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        output_files = []
        total_tasks = len(self.split_plans)
        
        for i, plan in enumerate(self.split_plans):
            # 报告进度
            if callback:
                progress = i / total_tasks
                callback(progress, f"正在处理: {plan.title}")
            
            # 创建新的 PDF 文档
            new_doc = fitz.open()
            
            # 插入页面范围
            new_doc.insert_pdf(
                self.doc,
                from_page=plan.start_page,
                to_page=plan.end_page
            )
            
            # 保存文件
            output_path = os.path.join(output_dir, f"{plan.name}.pdf")
            new_doc.save(output_path)
            new_doc.close()
            
            output_files.append(output_path)
        
        # 完成
        if callback:
            callback(1.0, f"完成！共生成 {len(output_files)} 个文件")
        
        return output_files
    
    def close(self) -> None:
        """关闭 PDF 文档"""
        if self.doc:
            self.doc.close()
            self.doc = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 简单测试代码（仅在直接运行此模块时执行）
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python pdf_splitter.py <pdf文件路径>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    with PDFSplitter(pdf_path) as splitter:
        print(f"PDF 总页数: {splitter.get_page_count()}")
        print(f"\n目录结构:")
        for level, title, page in splitter.get_toc():
            indent = "  " * (level - 1)
            print(f"{indent}[{level}] {title} (第 {page} 页)")
        
        print(f"\n分割计划:")
        plans = splitter.analyze_structure()
        for plan in plans:
            print(f"  {plan.name}: 第 {plan.start_page + 1} - {plan.end_page + 1} 页")