# dissertation-ko

영문 논문 초안(`../`)의 한국어 LaTeX 번역본입니다.

## 빌드

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```

XeLaTeX 2-pass로 `main.pdf`를 생성합니다.

## 원본

- 소스: `D:\Github\phd_works\2-Dissertation-Draft\`
- 결과 표(`../results/tables/`)는 부모 폴더의 생성 산출물을 `\input`합니다 (수치 재생성 없음).
- 참고문헌(`03-End/bibliography.tex`)은 영문 APA 형식 그대로 유지합니다.
