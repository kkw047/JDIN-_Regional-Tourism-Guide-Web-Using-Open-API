#  JDIN - 지역관광 안내 웹  
**Regional Tourism Guide Web Using Open API**

---

## 프로젝트 개요

Open API를 활용하여 **출발지 기준 거리 계산**, **여행 시간 설정**, 그리고 **복잡한 로그인 없이** 누구나 쉽게 이용 가능한  
**20대를 위한 여행 플랫폼**을 개발했습니다.  
여행 계획을 디테일하게 세우고 싶은 P세대의 니즈를 적극 반영한 서비스입니다.

---

## 팀원 및 역할

| 이름     | 역할               |
|----------|--------------------|
| 김건우   | 팀장, 데이터베이스(DB) |
| 박정환   | 백엔드 개발         |
| 이정환   | 백엔드 개발         |
| 최정륜   | UI/UX 디자인        |
| 하희찬   | 프론트엔드 개발     |

---

## 프로젝트 의의

- **20대 여행자(P들)**의 니즈에 맞춘 맞춤형 여행 경로 안내
- **로그인 없이도** 누구나 쉽게 접근 가능
- 출발지 기준 **거리 및 소요 시간 자동 계산**
- 각 관광지 마다 **추천 기능**을 통한 선택의 다향성 증가


##  사용 기술 스택
---
###  백엔드 (Backend)
- **Python 3.x**  
  사용자 요청 처리 및 데이터 가공을 위한 주요 언어
- **Flask**  
  경량 웹 프레임워크로 라우팅 및 템플릿 렌더링 담당
- **pymysql**  
  MySQL 데이터베이스 연동용 라이브러리 (DictCursor 사용으로 딕셔너리 형태 반환)
- **Open API 활용 예정**  
  관광 정보 연동을 위한 공공데이터 API 활용 가능

---

###  데이터베이스 (Database)
- **MySQL**
  - 사용자 선택 정보(`user_selection`)
  - 음식점 정보(`food_location`)
  - 관광지 정보(`tourist_attraction`)
- **데이터 자동 초기화 로직**
  - 최초 요청 시 `@app.before_request`에서 테이블에 데이터가 없으면 자동 삽입
    
---

### 프론트엔드 (Frontend)
- **HTML / CSS / Jinja2 (Flask 템플릿)**
  - 사용자 입력 화면 및 결과 페이지 구성
  - `index.html`, `result.html` 템플릿 사용

---
---
### 실행 및 배포
- **Flask 개발 서버 실행**
  - `python app.py` 또는 `flask run`
- **서비스 URL**
  - [http://61.81.96.151:5000](http://61.81.96.151:5000)
  - [http://justdoit.myddns.me/](http://justdoit.myddns.me/)

---

## 실행 화면

![image](https://github.com/user-attachments/assets/17dda793-051a-4208-ad8a-bb8feb2ce1eb)

  

---

