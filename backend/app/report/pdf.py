"""PDF 生成工具（WeasyPrint 封装）。"""
import os
from pathlib import Path


def generate_pdf(html_content: str, output_path: str) -> str:
    """将 HTML 内容转为 PDF 文件。"""
    try:
        from weasyprint import HTML
        HTML(string=html_content).write_pdf(output_path)
        return output_path
    except ImportError:
        # WeasyPrint 未安装时回退为保存 HTML
        html_path = output_path.replace(".pdf", ".html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return html_path
