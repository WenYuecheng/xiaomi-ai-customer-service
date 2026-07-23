const fs = require('node:fs')
const path = require('node:path')
const { Document, HeadingLevel, Packer, Paragraph, TextRun } = require('docx')

async function writeDocument(target, marker, formatLabel) {
  const document = new Document({
    sections: [{
      children: [
        new Paragraph({ text: `${formatLabel} 文件上传验收`, heading: HeadingLevel.TITLE }),
        new Paragraph({ children: [new TextRun({ text: `唯一验收标记：${marker}`, bold: true })] }),
        new Paragraph('用于验证文件签名、中文文本解析、后台任务处理和切片预览。'),
        new Paragraph('本文件不包含任何真实产品参数，不应导入正式产品知识库。'),
      ],
    }],
  })
  fs.mkdirSync(path.dirname(target), { recursive: true })
  fs.writeFileSync(target, await Packer.toBuffer(document))
}

const [docxTarget, pdfSourceTarget] = process.argv.slice(2)
if (!docxTarget || !pdfSourceTarget) throw new Error('missing output paths')
Promise.all([
  writeDocument(docxTarget, 'UPLOAD-DOCX-20260723', 'DOCX'),
  writeDocument(pdfSourceTarget, 'UPLOAD-PDF-20260723', 'PDF'),
]).catch((error) => { console.error(error); process.exitCode = 1 })
