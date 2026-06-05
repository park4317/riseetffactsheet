# GitHub Pages 셋업 가이드

## 최초 1회 설정 (5분)

### 1. GitHub 레포 생성
1. https://github.com/new 접속
2. Repository name: `rise-etf-factsheets`
3. **Private** 선택 (사내 자료)
4. Create repository 클릭

### 2. 이 폴더를 GitHub에 연결
프로젝트 폴더에서 터미널(cmd) 열고:

```
git init
git remote add origin https://github.com/[내아이디]/rise-etf-factsheets.git
git branch -M main
```

### 3. docs 폴더 + .gitignore 초기 설정
```
mkdir docs
echo # RISE ETF Factsheet Portal > docs\README.md
echo output/__pycache__/ > .gitignore
echo pipeline/__pycache__/ >> .gitignore
git add .
git commit -m "Initial setup"
git push -u origin main
```

### 4. GitHub Pages 활성화
1. GitHub 레포 → Settings → Pages
2. Source: **GitHub Actions** 선택
3. 저장

---

## 이후 사용법

### 팩트시트 업데이트 & 배포
```
deploy.bat 더블클릭
```
→ 자동으로: 생성 → 인덱스 빌드 → GitHub 푸시 → 1분 내 사이트 반영

### 접속 주소
```
https://[내아이디].github.io/rise-etf-factsheets/
```

---

## Private 레포인데 외부 접속?
GitHub Pages는 Private 레포에서도 **URL을 아는 사람은 누구나** 접속 가능합니다.
(GitHub Pro/Team이면 완전 비공개 설정도 가능)
