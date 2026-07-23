"""生成带嵌入中文字体、可被 pypdf 提取的 PDF 上传验收文件。"""

import sys
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


def main(target: Path) -> None:
    font_path = Path("/System/Library/Fonts/STHeiti Light.ttc")
    if not font_path.exists():
        raise RuntimeError("缺少用于生成中文验收 PDF 的系统字体")
    pdfmetrics.registerFont(TTFont("UploadFixtureCJK", font_path, subfontIndex=0))
    target.parent.mkdir(parents=True, exist_ok=True)
    document = canvas.Canvas(str(target))
    document.setTitle("PDF 文件上传验收")
    document.setFont("UploadFixtureCJK", 20)
    document.drawString(72, 760, "PDF 文件上传验收")
    document.setFont("UploadFixtureCJK", 12)
    document.drawString(72, 720, "唯一验收标记：UPLOAD-PDF-20260723")
    document.drawString(
        72, 690, "用于验证文件签名、中文文本解析、后台任务处理和切片预览。"
    )
    document.drawString(
        72, 660, "本文件不包含任何真实产品参数，不应导入正式产品知识库。"
    )
    document.save()


if __name__ == "__main__":
    main(Path(sys.argv[1]))
