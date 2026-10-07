# Direct LaTeX Conversion

This folder contains a direct OOXML-to-LaTeX conversion of:

`D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx`

The conversion script reads the `.docx` package XML directly:

- `word/document.xml`
- `word/styles.xml`
- `word/numbering.xml`
- `word/_rels/document.xml.rels`

It does not use pandoc for conversion.

## Files

- `Proposal-Final_Taehong Kwon.direct.tex`: generated LaTeX source
- `Proposal-Final_Taehong Kwon.direct.pdf`: compiled PDF, if build succeeds
- `convert_docx_xml_to_latex.py`: direct conversion script
- `build.ps1`: XeLaTeX build script
- `conversion_report.txt`: conversion summary

## Build

Run from this folder:

```powershell
.\build.ps1
```

The document is configured for XeLaTeX because the source contains Unicode punctuation, arrows, and math symbols.
